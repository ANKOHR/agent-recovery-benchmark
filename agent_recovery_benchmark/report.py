"""Deterministic rendering with provenance on both output surfaces."""

import json


def banner(result):
    p = result["provenance"]
    return (f"Data provenance: {p['synthetic_records']} synthetic fixture records (illustrative); "
            f"{p['henry_entered_records']} real records declared as Henry's own manually entered data. "
            "Source declarations are not independently verified.")


def render(result, format="md"):
    if format == "json":
        return json.dumps({"provenance_banner": banner(result), **result}, ensure_ascii=False,
                          sort_keys=True, indent=2) + "\n"
    if format != "md":
        raise ValueError("format must be md or json")
    lines = ["# Agent Recovery Benchmark", "", banner(result), "", result["honesty"], "",
             f"Validation as of: {result['as_of']}", "", "## Exact input totals", "",
             "| Metric | Value |", "| --- | ---: |"]
    lines += [f"| {key} | {value} |" for key, value in result["metrics"].items()]
    lines += ["", "## Failure groups", "", "| Failure | Records | Recovered |", "| --- | ---: | ---: |"]
    lines += [f"| {key} | {value['records']} | {value['recovered']} |" for key, value in result["by_failure"].items()]
    b = result["baseline_comparison"]
    lines += ["", "## Baseline comparison", "", f"Paired records: {b['paired_records']}",
              f"Recorded duration difference (ms): {b['recorded_duration_difference_ms'] if b['paired_records'] else 'unmeasured: no paired baseline'}",
              b["interpretation"], "", "Every aggregate is traceable to the trials in the JSON report."]
    return "\n".join(lines) + "\n"
