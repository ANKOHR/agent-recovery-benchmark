from pathlib import Path


def test_no_em_dash_in_project_sources():
    root = Path(__file__).resolve().parents[1]
    paths = [root / name for name in ("README.md", "LESSONS.md", "VERDICT.md", "pyproject.toml")]
    paths += list((root / "agent_recovery_benchmark").glob("*.py"))
    paths += list((root / "tests").glob("*.py"))
    paths += list((root / "scripts").glob("*.py"))
    assert all("\u2014" not in p.read_text(encoding="utf-8") for p in paths)
