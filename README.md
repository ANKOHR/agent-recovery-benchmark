# Agent Recovery Benchmark

`arb2` benchmarks recovery after execution failures using local, recorded trials.
It computes counts, recovery outcomes, label agreement, and recorded durations.
It does not run an agent, discover failures, predict recovery, call a model, or
estimate savings. Python 3.10+ and CPU only; no runtime dependencies or network calls.

The hypothesis is that deterministic validation and exact aggregation of recorded
failure trials can provide trustworthy, inspectable recovery evidence. Acceptance
requires all planted cases to reconcile with independent expectations, zero false
positives on the supplied labels, a passing adversarial suite, and a fixture demo
under five seconds. This establishes aggregation correctness, not agent quality.

## Quickstart

From this directory, using an environment with setuptools and pytest installed:

```powershell
python -m pip install --no-build-isolation --no-deps --no-index -e .
arb2 fixtures --out demo
arb2 run --input demo
arb2 report --format md
python -m pytest -q
```

The equivalent module entry point is `python -m agent_recovery_benchmark.cli`.
On Windows, if pip reports its user Scripts directory is not on PATH, add the
printed directory to your session's PATH or use that module entry point.
Each invocation is a separate CLI process. `run` writes `.arb2-results.json` in the
current working directory. `report` reads that file and recomputes its aggregates
from saved trials, so edited cached totals cannot become reported facts. Use
`--results <path>` on both commands to manage multiple runs. Reports and results
use atomic replacement; parent output directories must already exist.

## Input reference

An input directory contains UTF-8 `.jsonl` and/or `.json` files, read in sorted
filename order. JSONL supports blank lines and `#` header comments. Each other line
is one trial. JSON uses an envelope with exactly `synthetic`, `comment`, and
`records` fields. The envelope label must match every enclosed record.
`expectations.json` is reserved fixture metadata and is never used in calculations.
`.arb2-results.json` is also reserved and ignored as input. Other files are rejected
with a named schema error. CSV and YAML are not supported: convert them to JSONL.
For JSONL the error line is exact; JSON syntax errors name the parser line, while
JSON envelope and record schema errors name line 1.

```json
{
  "synthetic": true,
  "comment": "SYNTHETIC example: durations illustrative, not measured",
  "records": [
    {
      "id": "example-001",
      "synthetic": true,
      "source": "synthetic_fixture",
      "trial_date": "2026-09-30",
      "failure": "timeout",
      "attempts": 1,
      "recovered": true,
      "elapsed_ms": 100,
      "expected_recovered": true
    }
  ]
}
```

| Field | Rules and interpretation |
| --- | --- |
| id | Unique, nonempty string, maximum 10000 characters |
| synthetic | Required boolean; true for fixtures |
| source | `synthetic_fixture` when synthetic; otherwise `henry_entered` |
| trial_date | Canonical YYYY-MM-DD, no later than explicit `--as-of` |
| failure | `timeout`, `tool_error`, `invalid_output`, or `permission_denied` |
| attempts | Integer from 0 to 1000000000000, includes unsuccessful recovery attempts |
| recovered | Observed boolean outcome; true requires at least one attempt |
| elapsed_ms | Recorded total recovery duration, integer in the same range |
| baseline_ms | Optional paired baseline duration, integer in the same range |
| expected_recovered | Optional independent hand-checked boolean label |

Booleans are rejected in integer fields. Negative values, unknown fields, unknown
failure types, duplicate IDs across files, duplicate JSON keys, non-finite numbers,
invalid dates, control characters and strings over the limit are errors. Unicode
and Windows paths are supported. The prohibited em dash character is rejected in
record strings so reports cannot contain it. Unsupported monetary fields are
rejected, never silently interpreted. No records are silently dropped.
Unpaired UTF-16 surrogate characters are rejected rather than producing invalid UTF-8.

The default validation reference date is fixed at 2026-09-30, rather than the
system clock, to keep repeated runs deterministic. For later observations use
`--as-of 2026-10-15` consistently. No randomness is used; there is no seed.

For real use Henry manually records his own trials with `synthetic: false` and
`source: "henry_entered"`. Keep real trial files and results private. These source
declarations are self-reported and are not independently verified. Define a
successful recovery before collecting trials, record all failed trials as well,
and obtain expected labels independently when assessing correctness. Unlabelled
trials contribute to totals but not to the confusion matrix. Without labels the
false-positive count of zero provides no evidence of accuracy.

## Subcommand catalogue

| Command | Example | Output |
| --- | --- | --- |
| fixtures | `arb2 fixtures --out demo` | 200 synthetic trials and independent expectations |
| run | `arb2 run --input demo --results trial-results.json` | Saved analysis with every trial |
| report | `arb2 report --results trial-results.json --format json --out report.json` | JSON with provenance and trial-level traceability |
| validate | `arb2 validate --input demo` | Schema, date and duplicate checks without saving |
| failures | `arb2 failures --input demo` | JSON analysis including exact counts grouped by failure |

Every subcommand has `--help` and an example. `report --format md` is the readable
report. `failures` helps inspect which failure classes remain unrecovered;
`validate` checks recorded experiments before reporting. Missing input,
ParseError, SchemaError and WriteError return exit code 2 without tracebacks.
Successful commands return 0. A write failure preserves an existing output and
removes temporary files; fixture generation is atomic per file, not per directory.

## Architecture

```text
fixtures.py -> labelled local trials + expectations.json
local JSON/JSONL -> cli.py parse + source locations
                -> core.py validate + pure analyze
                -> saved trials + computed results
                -> report.py recompute via core + Markdown/JSON provenance
```

The CLI owns file I/O. Core functions have no I/O or clock access. Records are
sorted by ID; reports have fixed ordering and UTF-8 encoding. The same input,
reference date and format produce byte-identical saved results and reports.
`expectations.json` is independent of core computation and deliberately ignored
by the loader. Corrupting an outcome or its expected label changes the computed
figures, as covered by tests.

## Fixture labelling and planted ground truth

Every generated JSONL file begins with a `# SYNTHETIC` header and every record
has `synthetic: true`. The JSON expectations file carries a `synthetic: true`
field and a `comment` header stating its synthetic status. All examples and the
five-record starter input are synthetic. Reports always state synthetic and real
record counts, including mixed and empty data.

| Failure | Trials | Recovered | Attempts | Illustrative elapsed ms |
| --- | ---: | ---: | ---: | ---: |
| timeout | 50 | 50 | 50 | 5000 |
| tool_error | 50 | 40 | 100 | 10000 |
| invalid_output | 50 | 30 | 150 | 15000 |
| permission_denied | 50 | 0 | 0 | 0 |
| Total | 200 | 120 | 300 | 30000 |

The remaining 80 trials are unrecovered. Independent labels yield 120 true
positives, 80 true negatives, zero false positives and zero false negatives. These
are planted synthetic outcomes, not results of running a recovery policy. All
200 labels reconcile. See `evidence/` for local measured CLI performance and the
exact report. A small hand-written workflow is available with
`arb2 run --input examples/five && arb2 report --format md`.

## Honesty boundary and failure modes

All counts are computed from explicit records. Fixture durations are illustrative,
not measured execution timings. Real durations are supplied observations that
the tool cannot verify. A paired baseline permits a recorded duration difference
only for those paired rows; a negative difference is retained. This is not a causal
time-savings claim. Without paired baselines the comparison is labelled unmeasured.
Money saved and time saved are never estimated or reported as measured savings.
No hypothetical economic figures are provided.

Wrong hand-entered outcomes remain wrong observations: schema validation cannot
detect them. Expected labels copied from observations can give misleading perfect
agreement. Coverage is limited to the recorded trials, four failure classes and a
single supplied recovery outcome per trial. It cannot compare recovery policies,
measure live executions, or establish reliability under production load. Counts
are exact, but synthetic fixture accuracy does not demonstrate real-world accuracy.
Empty data renders zero totals and explicitly unmeasured baseline comparisons.

## Evidence-based improvement hook and verdict

The two-week real-use window begins when Henry records the first actual use.
No real-use window has been completed or claimed by this build. Track use dates
privately. After 14 days, independently hand-check at least one trial sample and
its report. Record sample size, mismatched output count and error rate as
`mismatches / checked items`; if the denominator is zero mark accuracy unmeasured.
Also record number of actual uses. If measured error exceeds 10 percent, fix the
largest evidenced cause and repeat the check, or kill the project with a reason.
If there are no actual uses, record that finding and kill it.

`VERDICT.md` is the evidence log template. The final verdict is pending this
window: expand for daily use or revenue, integrate for substantial sibling overlap,
commercialise for demonstrated willingness to pay as-is, maintain for useful
portfolio evidence otherwise, or kill for non-use or failed acceptance. No buyer,
revenue, saved time or adoption is invented. See `LESSONS.md` for build findings.

## Development

`python -m pytest -q` runs the exact ground-truth, provenance, determinism, corrupted
data and adversarial tests. Test fixtures that declare real provenance are test
inputs only, not real Henry trial evidence. `BUILD-DONE.txt` records the test count,
build commit and verified demo measurement. Publishing is a separate authorised
verification step; this build performs no publishing or network calls.
`python scripts/verify_demo.py` reruns the installed CLI in three separate processes,
checks exact expectations and the five-second limit, and refreshes the local
measurement evidence. Timing evidence naturally varies between measurements;
computed trial results and reports remain deterministic.
