"""Fixed, hand-designed cases. No random generator or seed is used."""

import json
from pathlib import Path


def fixture_records():
    records = []
    # Four equal groups of 50: 50, 40, 30, 0 recoveries respectively.
    for group, (failure, successes, attempts, duration) in enumerate([
        ("timeout", 50, 1, 100), ("tool_error", 40, 2, 200),
        ("invalid_output", 30, 3, 300), ("permission_denied", 0, 0, 0),
    ]):
        for i in range(50):
            recovered = i < successes
            records.append({"id": f"trial-{group * 50 + i + 1:03}",
                            "synthetic": True, "source": "synthetic_fixture",
                            "trial_date": "2026-09-30", "failure": failure,
                            "attempts": attempts, "elapsed_ms": duration,
                            "recovered": recovered, "expected_recovered": recovered})
    return records


def expectations():
    # Independent arithmetic: 4*50 trials; 50+40+30 recoveries;
    # attempts = 50*(1+2+3+0); duration = 50*(100+200+300+0).
    return {"synthetic": True, "comment": "SYNTHETIC: hand-computed planted ground truth; durations illustrative",
            "metrics": {"records": 200, "recovered": 120, "unrecovered": 80,
                        "attempts": 300, "elapsed_ms": 30000, "labelled_records": 200,
                        "true_positives": 120, "false_positives": 0,
                        "true_negatives": 80, "false_negatives": 0}}


def write_fixtures(directory):
    from .cli import atomic_write
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    atomic_write(path / "trials.jsonl", "# SYNTHETIC fixtures: durations are illustrative, not measured\n" +
                 "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in fixture_records()))
    atomic_write(path / "expectations.json", json.dumps(expectations(), indent=2, sort_keys=True) + "\n")
