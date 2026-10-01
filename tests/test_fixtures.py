import json
from agent_recovery_benchmark.fixtures import write_fixtures, expectations, fixture_records
from agent_recovery_benchmark.core import analyze
from agent_recovery_benchmark.cli import read_records


def test_fixtures_labelled_synthetic(tmp_path):
    write_fixtures(tmp_path)
    assert (tmp_path / "trials.jsonl").read_text().startswith("# SYNTHETIC")
    assert all(r["synthetic"] for r in read_records(tmp_path))
    assert json.loads((tmp_path / "expectations.json").read_text())["synthetic"] is True


def test_fixture_ground_truth_matches_hand_computed():
    assert analyze(fixture_records())["metrics"] == expectations()["metrics"]
    assert expectations()["metrics"]["records"] == 200


def test_fixture_generation_deterministic(tmp_path):
    write_fixtures(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    write_fixtures(tmp_path)
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}
