"""CLI: byop validate <layers_dir> | byop registry [measures.json] | byop pin <owner/repo> <tag> <asset>..."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import registry as reg
from .validate import ValidationError, validate_layers_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="byop", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="check a layers dir (aggregation_spec.json + files)")
    v.add_argument("layers_dir")
    v.add_argument("--lenient", action="store_true", help="don't require label/description/methodology/direction")
    r = sub.add_parser("registry", help="check measures.json")
    r.add_argument("path", nargs="?", default=str(reg.REGISTRY_PATH))
    p = sub.add_parser("pin", help="print sha256 pins for a release's assets")
    p.add_argument("repo"); p.add_argument("tag"); p.add_argument("assets", nargs="+")
    args = parser.parse_args(argv)

    if args.cmd == "validate":
        try:
            report = validate_layers_dir(args.layers_dir, strict_catalog=not args.lenient)
        except ValidationError as error:
            print("INVALID:", file=sys.stderr)
            for problem in error.problems:
                print(f"  - {problem}", file=sys.stderr)
            return 1
        print(json.dumps(report, indent=2))
        print(f"ok: {report['source']} — {len(report['metrics'])} metrics over {len(report['layers'])} layers")
        return 0
    if args.cmd == "registry":
        problems = reg.validate_registry(reg.load_registry(Path(args.path)))
        if problems:
            print("\n".join(f"- {p}" for p in problems), file=sys.stderr); return 1
        print("registry ok"); return 0
    if args.cmd == "pin":
        print(json.dumps(reg.pin(args.repo, args.tag, args.assets), indent=2)); return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
