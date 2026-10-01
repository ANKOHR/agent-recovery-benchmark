# Agent Recovery Benchmark

Data provenance: 200 synthetic fixture records (illustrative); 0 real records declared as Henry's own manually entered data. Source declarations are not independently verified.

Computed from supplied observations only. Synthetic timings are illustrative, not measured execution. No agent was executed. Time or money saved is unmeasured and is not reported.

Validation as of: 2026-09-30

## Exact input totals

| Metric | Value |
| --- | ---: |
| records | 200 |
| recovered | 120 |
| unrecovered | 80 |
| attempts | 300 |
| elapsed_ms | 30000 |
| labelled_records | 200 |
| true_positives | 120 |
| false_positives | 0 |
| true_negatives | 80 |
| false_negatives | 0 |

## Failure groups

| Failure | Records | Recovered |
| --- | ---: | ---: |
| invalid_output | 50 | 30 |
| permission_denied | 50 | 0 |
| timeout | 50 | 50 |
| tool_error | 50 | 40 |

## Baseline comparison

Paired records: 0
Recorded duration difference (ms): unmeasured: no paired baseline
Recorded baseline minus recovery duration for paired trials only; synthetic durations are illustrative. No causal savings claim.

Every aggregate is traceable to the trials in the JSON report.
