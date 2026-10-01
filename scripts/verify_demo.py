"""Local acceptance measurement. Timing is measured, fixture trial durations are illustrative."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent_recovery_benchmark.fixtures import expectations


def main():
    env = os.environ.copy()
    env["PATH"] = sysconfig.get_path("scripts", scheme="nt_user" if os.name == "nt" else "posix_user") + os.pathsep + env.get("PATH", "")
    executable = shutil.which("arb2", path=env["PATH"])
    if not executable:
        raise SystemExit("Install arb2 locally before verifying the demo. See README.")
    commands = [[executable, "fixtures", "--out", "demo"],
                [executable, "run", "--input", "demo"],
                [executable, "report", "--format", "md"]]
    start = time.perf_counter()
    outputs = [subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True,
                              encoding="utf-8").stdout for command in commands]
    duration = time.perf_counter() - start
    saved = json.loads((ROOT / ".arb2-results.json").read_text(encoding="utf-8"))
    assert saved["metrics"] == expectations()["metrics"]
    assert duration < 5, f"Demo exceeded acceptance limit: {duration} seconds"
    assert "Data provenance: 200 synthetic" in outputs[-1]
    assert all("\u2014" not in output for output in outputs)
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "fixture-report.md").write_text(outputs[-1], encoding="utf-8", newline="\n")
    measurement = {
        "synthetic": True,
        "comment": "SYNTHETIC input data. CLI wall-clock duration measured locally; fixture trial durations illustrative.",
        "commands": ["arb2 fixtures --out demo", "arb2 run --input demo", "arb2 report --format md"],
        "measured_wall_clock_seconds": round(duration, 6),
        "acceptance_limit_seconds": 5,
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "metrics": saved["metrics"],
        "all_metrics_match_independent_expectations": True,
        "scope": "One local run including three process startups. No live recovery execution or real-use measurement.",
    }
    (evidence / "demo-measurement.json").write_text(json.dumps(measurement, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"Measured full demo: {duration:.6f} seconds; exact ground truth verified.")


if __name__ == "__main__":
    main()
