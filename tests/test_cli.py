import json
import time
import pytest
from agent_recovery_benchmark.cli import main, read_records
from agent_recovery_benchmark.core import BenchmarkError
from agent_recovery_benchmark.fixtures import write_fixtures, fixture_records


def test_run_completes_on_fixture(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    start = time.perf_counter()
    assert main(["fixtures", "--out", "demo"]) == 0
    assert main(["run", "--input", "demo"]) == 0
    assert main(["report", "--format", "md"]) == 0
    assert time.perf_counter() - start < 5
    assert "Data provenance" in capsys.readouterr().out


def test_cli_smoke_all_subcommands(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_fixtures(tmp_path / "demo")
    for command in ("fixtures", "run", "report", "validate", "failures"):
        with pytest.raises(SystemExit) as exc:
            main([command, "--help"])
        assert exc.value.code == 0
    for command in ("validate", "failures", "run"):
        assert main([command, "--input", "demo"]) == 0
    assert main(["report", "--format", "json"]) == 0


def test_determinism_byte_identical(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_fixtures(tmp_path / "demo")
    outputs = []
    for _ in range(2):
        assert main(["run", "--input", "demo"]) == 0
        assert main(["report", "--out", "report.md"]) == 0
        outputs.append(((tmp_path / ".arb2-results.json").read_bytes(), (tmp_path / "report.md").read_bytes()))
    assert outputs[0] == outputs[1]


def test_malformed_input_named_error(tmp_path, capsys):
    (tmp_path / "bad.jsonl").write_text('# header\n{"id":\n', encoding="utf-8")
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "ParseError" in error and "bad.jsonl" in error and "line 2" in error
    assert "Traceback" not in error


@pytest.mark.parametrize("text", ['{"synthetic": true,', '{"x": NaN}', '{"x":1,"x":2}'])
def test_malformed_json(tmp_path, text):
    (tmp_path / "bad.json").write_text(text)
    with pytest.raises(BenchmarkError, match="ParseError.*line"):
        read_records(tmp_path)


def test_missing_input_named_error(tmp_path, capsys):
    assert main(["run", "--input", str(tmp_path / "missing")]) == 2
    assert "MissingInput" in capsys.readouterr().err


def test_report_write_failure_no_partial_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write_fixtures(tmp_path / "demo")
    main(["run", "--input", "demo"])
    before = sorted(p.name for p in tmp_path.iterdir())
    assert main(["report", "--out", "absent/report.md"]) == 2
    assert "WriteError" in capsys.readouterr().err
    assert before == sorted(p.name for p in tmp_path.iterdir())


def test_five_hand_written_records():
    # Hand-written minimum workflow, intentionally independent of generator.
    from agent_recovery_benchmark.core import analyze
    rows = [dict(id=str(i), synthetic=False, source="henry_entered", trial_date="2026-09-01",
                 failure="timeout", attempts=1, recovered=i < 3, elapsed_ms=10) for i in range(5)]
    assert analyze(rows)["metrics"]["recovered"] == 3


def test_json_envelope(tmp_path):
    rows = fixture_records()[:5]
    (tmp_path / "trials.json").write_text(json.dumps({"synthetic": True, "comment": "SYNTHETIC", "records": rows}))
    assert read_records(tmp_path) == rows


def test_empty_directory_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "empty").mkdir()
    assert main(["run", "--input", "empty"]) == 0
    assert main(["report"]) == 0
    assert "0 synthetic" in capsys.readouterr().out


def test_cached_totals_are_recomputed(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write_fixtures(tmp_path / "demo")
    main(["run", "--input", "demo"])
    path = tmp_path / ".arb2-results.json"
    saved = json.loads(path.read_text())
    saved["metrics"]["recovered"] = 999
    path.write_text(json.dumps(saved))
    capsys.readouterr()
    assert main(["report", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["metrics"]["recovered"] == 120


def test_five_record_file_workflow(tmp_path, monkeypatch, capsys):
    from pathlib import Path
    input_dir = Path(__file__).resolve().parents[1] / "examples" / "five"
    monkeypatch.chdir(tmp_path)
    assert main(["run", "--input", str(input_dir)]) == 0
    capsys.readouterr()
    assert main(["report", "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["metrics"]["records"] == 5
    assert report["metrics"]["recovered"] == 3


@pytest.mark.parametrize("suffix", ["csv", "yaml"])
def test_unsupported_format_named_error(tmp_path, suffix, capsys):
    (tmp_path / f"bad.{suffix}").write_text("broken: [")
    assert main(["run", "--input", str(tmp_path)]) == 2
    assert "SchemaError" in capsys.readouterr().err


def test_atomic_failure_preserves_existing_file(tmp_path, monkeypatch):
    import os
    from agent_recovery_benchmark.cli import atomic_write
    target = tmp_path / "report.md"
    target.write_text("previous")
    def fail_replace(*args):
        raise PermissionError("planted write failure")
    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(BenchmarkError, match="WriteError"):
        atomic_write(target, "new")
    assert target.read_text() == "previous"
    assert list(tmp_path.iterdir()) == [target]


def test_unicode_cli_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / "输入"
    directory.mkdir()
    record = fixture_records()[0]
    record["id"] = "C:\\Users\\亨利\\" + "é" * 9000
    (directory / "trials.jsonl").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    assert main(["run", "--input", str(directory)]) == 0
    capsys.readouterr()
    assert main(["report", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["trials"][0]["id"] == record["id"]


def test_corrupted_fixture_label_changes_report(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / "demo"
    write_fixtures(directory)
    path = directory / "trials.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[1])
    record["expected_recovered"] = False
    lines[1] = json.dumps(record)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert main(["run", "--input", "demo"]) == 0
    capsys.readouterr()
    assert main(["report", "--format", "json"]) == 0
    metrics = json.loads(capsys.readouterr().out)["metrics"]
    assert metrics["false_positives"] == 1
    assert metrics["true_positives"] == 119


def test_schema_error_names_file_line_field(tmp_path, capsys):
    record = fixture_records()[0]
    record["elapsed_ms"] = -1
    (tmp_path / "trials.jsonl").write_text("# SYNTHETIC\n" + json.dumps(record))
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert all(word in error for word in ("SchemaError", "trials.jsonl", "line 2", "elapsed_ms"))
