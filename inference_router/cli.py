"""Local JSONL inputs and atomic local output. Never calls a model or network."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from .core import POLICY, RouterError, route, validate, workflow
from .fixtures import encode, expectations, records
from .report import render


def atomic_write(path, text):
    path = Path(path)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=".ir-", delete=False) as stream:
            tmp = Path(stream.name)
            stream.write(text)
        os.replace(tmp, path)
    except OSError as exc:
        raise RouterError(f"WriteError: {path}: {exc.strerror}") from exc
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()


def read_input(directory):
    directory = Path(directory)
    if not directory.is_dir():
        raise RouterError(f"MissingInput: {directory}: use ir fixtures --out demo or supply an input directory")
    rows, provenance, seen = [], [], set()
    for path in sorted(directory.iterdir()):
        if path.name == "expectations.json":
            continue  # Ground truth is in each record; this independent oracle is for verification only.
        if not path.is_file() or path.suffix != ".jsonl":
            raise RouterError(f"SchemaError: {path}: line 1: unsupported input; use .jsonl files")
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise RouterError(f"ParseError: {path}: line 1: cannot read UTF-8 input") from exc
        if "\u2014" in path.name:
            raise RouterError("SchemaError: input filename contains prohibited U+2014")
        provenance.append({"name": path.name, "sha256": hashlib.sha256(raw).hexdigest()})
        for line_no, line in enumerate(text.splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                row = json.loads(line, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
            except (ValueError, RecursionError) as exc:
                raise RouterError(f"ParseError: {path}: line {line_no}: invalid JSON") from exc
            try:
                validate(row)
                if row["id"] in seen:
                    raise RouterError(f"SchemaError: duplicate id {row['id']}")
            except RouterError as exc:
                raise RouterError(f"{exc}: {path}: line {line_no}") from exc
            seen.add(row["id"])
            rows.append(row)
    return rows, provenance


def parser():
    p = argparse.ArgumentParser(description="Offline deterministic router. Illustrative tiers; no model execution.")
    sub = p.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fixtures", help="Generate labelled synthetic fixtures", epilog="Example: ir fixtures --out demo")
    f.add_argument("--out", required=True)
    f.add_argument("--count", choices=(5, 200), type=int, default=200)
    r = sub.add_parser("run", help="Compute routes from a JSONL directory", epilog="Example: ir run --input demo")
    r.add_argument("--input", required=True)
    r.add_argument("--results", default=".ir-results.json")
    rep = sub.add_parser("report", help="Render computed evidence", epilog="Example: ir report --format md")
    rep.add_argument("--format", choices=("md", "json"), default="md")
    rep.add_argument("--results", default=".ir-results.json")
    rep.add_argument("--out")
    one = sub.add_parser("route", help="Explain one declared task's route", epilog='Example: ir route --prompt "Write code" --steps 2 --code')
    one.add_argument("--prompt", required=True)
    one.add_argument("--steps", type=int, default=1)
    one.add_argument("--reasoning", action="store_true")
    one.add_argument("--code", action="store_true")
    sub.add_parser("policy", help="Show illustrative tier rules", epilog="Example: ir policy")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            if any(out.iterdir()):
                raise RouterError(f"WriteError: {out}: fixture destination must be empty")
            atomic_write(out / "prompts.jsonl", "# SYNTHETIC fixture data; no real prompts\n" + "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records(args.count)))
            atomic_write(out / "expectations.json", encode(expectations(args.count)))
            print(f"Generated {args.count} SYNTHETIC records. Illustrative model tiers; no measured savings.")
        elif args.command == "run":
            rows, provenance = read_input(args.input)
            data = workflow(rows)
            data["input_files"] = provenance
            atomic_write(args.results, encode(data))
            print(f"Computed {len(rows)} routes ({sum(r['synthetic'] for r in rows)} synthetic; {sum(not r['synthetic'] for r in rows)} declared real). Illustrative policy; no model calls or measured savings. Results: {args.results}")
        elif args.command == "report":
            path = Path(args.results)
            if not path.is_file():
                raise RouterError(f"MissingInput: {path}: run ir run --input <dir> first")
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                output = render(data, args.format)
            except (ValueError, KeyError, TypeError) as exc:
                raise RouterError(f"SchemaError: {path}: invalid results; rerun ir run") from exc
            if args.out:
                atomic_write(args.out, output)
            else:
                print(output, end="")
        elif args.command == "route":
            print(encode({"provenance_banner": "Single prompt entered by caller; ownership is user-declared.", "honesty": POLICY["label"] + " Cost, latency and savings are unmeasured.", "record": route({"id": "single", "prompt": args.prompt,
                  "steps": args.steps, "requires_reasoning": args.reasoning, "requires_code": args.code,
                  "synthetic": False, "source": "henry_entered"})}), end="")
        else:
            print(encode(POLICY), end="")
        return 0
    except (RouterError, OSError) as exc:
        message = str(exc).replace("\u2014", "-")
        print(message if isinstance(exc, RouterError) else f"WriteError: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
