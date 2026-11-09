"""boxkit command-line interface."""

from __future__ import annotations

import argparse
import sys

from boxkit import __version__
from boxkit.adapters import run_optional_adapters
from boxkit.render import render_spec
from boxkit.spec import load_spec
from boxkit.validate import validate_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="boxkit", description="Declarative ffmpeg edits for headless Linux")
    parser.add_argument("--version", action="version", version=f"boxkit {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Check spec files")
    p_val.add_argument("spec", nargs="+", help="YAML or JSON edit spec")

    p_plan = sub.add_parser("plan", help="Print ffmpeg command and filter graph (dry-run)")
    p_plan.add_argument("spec", help="Edit spec path")
    p_plan.add_argument("-o", "--output", help="Override output path")

    p_render = sub.add_parser("render", help="Render spec with ffmpeg")
    p_render.add_argument("spec", help="Edit spec path")
    p_render.add_argument("-o", "--output", help="Override output path")
    p_render.add_argument("-n", "--dry-run", action="store_true", help="Print plan only")

    args = parser.parse_args(argv)

    if args.cmd == "validate":
        failed = 0
        for path in args.spec:
            res = validate_path(path)
            print(f"## {path}")
            if res.warnings:
                for w in res.warnings:
                    print(f"  warn: {w}")
            if res.ok:
                print("  OK")
            else:
                failed += 1
                for e in res.errors:
                    print(f"  error: {e}")
        return 1 if failed else 0

    if args.cmd == "plan":
        from boxkit.plan import build_plan

        spec = load_spec(args.spec)
        run_optional_adapters(spec, dry_run=True)
        plan = build_plan(spec, output_override=args.output)
        print(plan.describe())
        return 0

    if args.cmd == "render":
        spec = load_spec(args.spec)
        run_optional_adapters(spec, dry_run=args.dry_run)
        plan = render_spec(args.spec, output=args.output, dry_run=args.dry_run)
        if args.dry_run:
            print(plan.describe())
        else:
            print(f"wrote {plan.output_path}")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
