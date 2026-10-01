import json
from agent_recovery_benchmark.core import analyze
from agent_recovery_benchmark.fixtures import fixture_records, expectations
from agent_recovery_benchmark.report import render


def test_report_matches_ground_truth_exact():
    report = json.loads(render(analyze(fixture_records()), "json"))
    assert report["metrics"] == expectations()["metrics"]


def test_report_zero_false_positives():
    assert json.loads(render(analyze(fixture_records()), "json"))["metrics"]["false_positives"] == 0


def test_report_carries_provenance_banner():
    for format in ("md", "json"):
        output = render(analyze(fixture_records()), format)
        assert "Data provenance: 200 synthetic" in output
        assert "0 real records" in output


def test_hypothetical_figures_labelled():
    for format in ("md", "json"):
        output = render(analyze(fixture_records()), format)
        assert "illustrative" in output
        assert "unmeasured" in output
        assert "No agent was executed" in output


def test_empty_input_renders_without_traceback():
    result = analyze([])
    assert all(value == 0 for value in result["metrics"].values())
    assert "unmeasured" in render(result)


def test_no_em_dashes_in_outputs():
    for format in ("md", "json"):
        assert "\u2014" not in render(analyze(fixture_records()), format)


def test_mixed_provenance():
    records = fixture_records()[:2]
    records[0].update(synthetic=False, source="henry_entered")
    assert "1 synthetic" in render(analyze(records))
    assert "1 real records" in render(analyze(records))
