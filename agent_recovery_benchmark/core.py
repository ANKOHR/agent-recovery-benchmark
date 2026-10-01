"""Pure validation and analysis. Durations are supplied observations, not estimates."""

from datetime import date


class BenchmarkError(ValueError):
    """A named, actionable input or output failure."""


FIELDS = {"id", "synthetic", "source", "trial_date", "failure", "attempts",
          "recovered", "elapsed_ms", "baseline_ms", "expected_recovered"}
REQUIRED = FIELDS - {"baseline_ms", "expected_recovered"}
FAILURES = {"timeout", "tool_error", "invalid_output", "permission_denied"}
SOURCES = {"synthetic_fixture", "henry_entered"}
REFERENCE_DATE = date(2026, 9, 30)


def validate_records(records, as_of=REFERENCE_DATE):
    """Reject schema drift, duplicate IDs and future dates against explicit as_of."""
    if not isinstance(records, list):
        raise BenchmarkError("SchemaError: records must be a list")
    seen = set()
    for index, record in enumerate(records, 1):
        prefix = f"record {index}"
        if not isinstance(record, dict):
            raise BenchmarkError(f"SchemaError: {prefix}: record must be an object")
        missing, unknown = REQUIRED - record.keys(), record.keys() - FIELDS
        if missing or unknown:
            raise BenchmarkError(f"SchemaError: {prefix}: missing fields {sorted(missing)}; unknown fields {sorted(unknown)}")
        for field in ("id", "source", "trial_date", "failure"):
            value = record[field]
            if not isinstance(value, str) or not value or len(value) > 10000:
                raise BenchmarkError(f"SchemaError: {prefix}: {field} must be a nonempty string of at most 10000 characters")
            if "\u2014" in value or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
                raise BenchmarkError(f"SchemaError: {prefix}: {field} contains prohibited punctuation or control characters")
        if record["id"] in seen:
            raise BenchmarkError(f"SchemaError: {prefix}: duplicate id")
        seen.add(record["id"])
        for field in ("synthetic", "recovered", "expected_recovered"):
            if field in record and type(record[field]) is not bool:
                raise BenchmarkError(f"SchemaError: {prefix}: {field} must be boolean")
        if record["source"] not in SOURCES or record["synthetic"] != (record["source"] == "synthetic_fixture"):
            raise BenchmarkError(f"SchemaError: {prefix}: source and synthetic must agree")
        if record["failure"] not in FAILURES:
            raise BenchmarkError(f"SchemaError: {prefix}: failure must be one of {sorted(FAILURES)}")
        try:
            trial_date = date.fromisoformat(record["trial_date"])
        except ValueError:
            raise BenchmarkError(f"SchemaError: {prefix}: trial_date must be YYYY-MM-DD") from None
        if trial_date.isoformat() != record["trial_date"] or trial_date > as_of:
            raise BenchmarkError(f"SchemaError: {prefix}: trial_date must be canonical and no later than as_of {as_of}")
        for field in ("attempts", "elapsed_ms", "baseline_ms"):
            if field not in record:
                continue
            value = record[field]
            if type(value) is not int or not 0 <= value <= 10**12:
                raise BenchmarkError(f"SchemaError: {prefix}: {field} must be an integer between 0 and 1000000000000")
        if record["recovered"] and record["attempts"] == 0:
            raise BenchmarkError(f"SchemaError: {prefix}: recovered requires attempts greater than zero")
    return records


def analyze(records, as_of=REFERENCE_DATE):
    """Compute exact counts from recorded outcomes and optional independent labels."""
    validate_records(records, as_of)
    ordered = sorted(records, key=lambda r: r["id"])
    labelled = [r for r in ordered if "expected_recovered" in r]
    paired = [r for r in ordered if "baseline_ms" in r]
    recovered = sum(r["recovered"] for r in ordered)
    confusion = {
        "true_positives": sum(r["recovered"] and r["expected_recovered"] for r in labelled),
        "false_positives": sum(r["recovered"] and not r["expected_recovered"] for r in labelled),
        "true_negatives": sum(not r["recovered"] and not r["expected_recovered"] for r in labelled),
        "false_negatives": sum(not r["recovered"] and r["expected_recovered"] for r in labelled),
    }
    return {
        "schema_version": 1, "as_of": as_of.isoformat(),
        "provenance": {"synthetic_records": sum(r["synthetic"] for r in ordered),
                       "henry_entered_records": sum(not r["synthetic"] for r in ordered)},
        "metrics": {"records": len(ordered), "recovered": recovered,
                    "unrecovered": len(ordered) - recovered,
                    "attempts": sum(r["attempts"] for r in ordered),
                    "elapsed_ms": sum(r["elapsed_ms"] for r in ordered),
                    "labelled_records": len(labelled), **confusion},
        "baseline_comparison": {
            "paired_records": len(paired),
            "recorded_duration_difference_ms": sum(r["baseline_ms"] - r["elapsed_ms"] for r in paired) if paired else None,
            "interpretation": "Recorded baseline minus recovery duration for paired trials only; synthetic durations are illustrative. No causal savings claim.",
        },
        "by_failure": {failure: {"records": sum(r["failure"] == failure for r in ordered),
                                  "recovered": sum(r["failure"] == failure and r["recovered"] for r in ordered)}
                       for failure in sorted(FAILURES)},
        "trials": ordered,
        "honesty": "Computed from supplied observations only. Synthetic timings are illustrative, not measured execution. No agent was executed. Time or money saved is unmeasured and is not reported.",
    }
