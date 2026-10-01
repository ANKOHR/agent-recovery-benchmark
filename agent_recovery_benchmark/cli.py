"""Local-file CLI. No network, model calls or agent execution."""

import argparse
from datetime import date
import json
import os
from pathlib import Path
import sys
import tempfile

from .core import BenchmarkError, REFERENCE_DATE, analyze, validate_records
from .fixtures import write_fixtures
from .report import render
from .report import banner


def atomic_write(path, content):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        os.replace(temporary, path)
    except OSError as exc:
        raise BenchmarkError(f"WriteError: {path}: {exc.strerror or 'unable to write output'}") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def strict_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate field {key}")
        obj[key] = value
    return obj


def parse_json(text, file, line=1):
    try:
        return json.loads(text, object_pairs_hook=strict_object,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-finite value")))
    except (ValueError, RecursionError) as exc:
        offset = exc.lineno - 1 if isinstance(exc, json.JSONDecodeError) else 0
        reason = exc.msg if isinstance(exc, json.JSONDecodeError) else str(exc)
        raise BenchmarkError(f"ParseError: {file}: line {line + offset}: {reason}") from None


def read_records(directory, as_of=REFERENCE_DATE):
    path = Path(directory)
    if not path.is_dir():
        raise BenchmarkError(f"MissingInput: {path}: supply an existing directory with --input; use arb2 fixtures --out demo")
    records, origins = [], []
    for file in sorted(path.iterdir()):
        if not file.is_file() or file.name in {"expectations.json", ".arb2-results.json"}:
            continue
        if file.suffix.lower() not in {".jsonl", ".json"}:
            raise BenchmarkError(f"SchemaError: {file}: line 1: unsupported input format; use JSONL or JSON")
        try:
            content = file.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            raise BenchmarkError(f"ParseError: {file}: line 1: cannot read UTF-8 input") from None
        if file.suffix.lower() == ".jsonl":
            for line_number, line in enumerate(content.splitlines(), 1):
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                records.append(parse_json(line, file, line_number))
                origins.append((file, line_number))
        else:
            data = parse_json(content, file)
            if not isinstance(data, dict) or set(data) != {"synthetic", "comment", "records"} or type(data["synthetic"]) is not bool or not isinstance(data["comment"], str) or not isinstance(data["records"], list):
                raise BenchmarkError(f"SchemaError: {file}: line 1: expected envelope fields synthetic, comment, records")
            if any(not isinstance(r, dict) or r.get("synthetic") != data["synthetic"] for r in data["records"]):
                raise BenchmarkError(f"SchemaError: {file}: line 1: envelope synthetic must match every record")
            records.extend(data["records"])
            origins.extend((file, 1) for _ in data["records"])
    # Validate each record to give exact source locations, then validate IDs globally.
    seen = set()
    for record, (file, line) in zip(records, origins):
        try:
            validate_records([record], as_of)
            if record["id"] in seen:
                raise BenchmarkError("SchemaError: duplicate id")
            seen.add(record["id"])
        except BenchmarkError as exc:
            raise BenchmarkError(f"{exc.args[0].split(':', 1)[0]}: {file}: line {line}: {str(exc).split(':', 1)[1].strip()}") from None
    return records


def parser():
    p = argparse.ArgumentParser(description="Benchmark recorded recovery after execution failures. Local observations only.")
    sub = p.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fixtures", help="Generate labelled synthetic trials", epilog="Example: arb2 fixtures --out demo")
    f.add_argument("--out", required=True)
    for command, help_text in [("run", "Analyze recorded trials and save results"),
                               ("validate", "Validate schema, dates and duplicate IDs"),
                               ("failures", "Show exact recovery counts by failure type")]:
        s = sub.add_parser(command, help=help_text, description=help_text,
                           epilog=f"Example: arb2 {command} --input demo")
        s.add_argument("--input", required=True)
        s.add_argument("--as-of", type=date.fromisoformat, default=REFERENCE_DATE,
                       help="Explicit latest allowed trial date, default 2026-09-30")
        if command == "run":
            s.add_argument("--results", default=".arb2-results.json", help="Atomic output path for recorded analysis")
    r = sub.add_parser("report", help="Render a report with provenance", epilog="Example: arb2 report --format md")
    r.add_argument("--format", choices=["md", "json"], default="md")
    r.add_argument("--results", default=".arb2-results.json")
    r.add_argument("--out", help="Optional atomic report file; otherwise stdout")
    return p


def main(argv=None):
    # Explicit UTF-8 avoids Windows redirected-output mojibake for supported Unicode.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            write_fixtures(args.out)
            print("Generated 200 SYNTHETIC trials; all fixture durations are illustrative.")
        elif args.command in {"run", "validate", "failures"}:
            records = read_records(args.input, args.as_of)
            result = analyze(records, args.as_of)
            if args.command == "run":
                atomic_write(args.results, json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
                print(f"Computed {len(records)} recorded trials. " + banner(result))
                print(f"Results: {args.results}".replace("\u2014", "-"))
            elif args.command == "validate":
                print(f"Valid: {len(records)} records. " + banner(result))
                print(result["honesty"])
            else:
                print(render(result, "json"), end="")
        else:
            path = Path(args.results)
            if not path.is_file():
                raise BenchmarkError(f"MissingInput: {path}: run arb2 run --input <dir> first")
            try:
                saved = parse_json(path.read_text(encoding="utf-8"), path)
            except (OSError, UnicodeError):
                raise BenchmarkError(f"ParseError: {path}: line 1: cannot read UTF-8 results") from None
            if not isinstance(saved, dict) or saved.get("schema_version") != 1:
                raise BenchmarkError(f"SchemaError: {path}: line 1: unsupported results schema_version")
            try:
                # Recompute rather than trusting potentially edited cached aggregates.
                result = analyze(saved["trials"], date.fromisoformat(saved["as_of"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise BenchmarkError(f"SchemaError: {path}: line 1: invalid trials or as_of: {exc}") from None
            output = render(result, args.format)
            if args.out:
                atomic_write(args.out, output)
            else:
                print(output, end="")
        return 0
    except (BenchmarkError, OSError) as exc:
        message = str(exc).replace("\u2014", "-")
        print(message if isinstance(exc, BenchmarkError) else f"WriteError: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
