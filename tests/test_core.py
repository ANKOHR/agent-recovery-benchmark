from copy import deepcopy
import pytest

from agent_recovery_benchmark.core import BenchmarkError, analyze
from agent_recovery_benchmark.fixtures import fixture_records


@pytest.mark.parametrize("field,value", [
    ("elapsed_ms", -1), ("baseline_ms", -1), ("attempts", True),
    ("elapsed_ms", float("inf")), ("elapsed_ms", 10**13),
    ("trial_date", "2099-01-01"), ("id", "x" * 10001),
    ("source", "unknown"), ("synthetic", False), ("failure", "new"),
    ("recovered", "true"), ("id", "bad\u2014punctuation"),
    ("id", "\ud800"),
])
def test_rejects_adversarial_values(field, value):
    record = fixture_records()[0]
    record[field] = value
    with pytest.raises(BenchmarkError, match="SchemaError"):
        analyze([record])


def test_duplicate_ids_rejected():
    record = fixture_records()[0]
    with pytest.raises(BenchmarkError, match="duplicate id"):
        analyze([record, deepcopy(record)])


def test_schema_drift_named():
    record = fixture_records()[0]
    record["amount"] = -10
    with pytest.raises(BenchmarkError, match="amount"):
        analyze([record])


def test_corrupted_ground_truth_changes_figures():
    records = fixture_records()
    records[0]["expected_recovered"] = False
    metrics = analyze(records)["metrics"]
    assert metrics["false_positives"] == 1
    assert metrics["true_positives"] == 119


def test_corrupted_outcome_changes_figures():
    records = fixture_records()
    records[0]["recovered"] = False
    assert analyze(records)["metrics"]["recovered"] == 119


def test_baseline_only_paired_observations():
    records = fixture_records()[:2]
    records[0]["baseline_ms"] = 80
    assert analyze(records)["baseline_comparison"]["recorded_duration_difference_ms"] == -20
    assert analyze(records)["baseline_comparison"]["paired_records"] == 1


def test_handles_unicode_and_long_inputs():
    record = fixture_records()[0]
    record["id"] = "C:\\Users\\亨利\\" + "é" * 9000
    assert analyze([record])["trials"][0]["id"] == record["id"]
