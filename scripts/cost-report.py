#!/usr/bin/env python3
"""Produce the monthly cost report from the usage ledger.

Example:

    scripts/cost-report.py .bayan/ledger/2026-10.jsonl --period 2026-10 \\
        --out system/reports/cost/2026-10.md

Exit codes: 0 within budget, 1 alerts raised, 2 usage error.
"""

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from bayan import cost, registry
from bayan.common import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, repo_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(__doc__.splitlines()[2:]))
    parser.add_argument("ledger", nargs="+", type=Path,
                        help="ledger JSONL files")
    parser.add_argument("--period", required=True, help="e.g. 2026-10")
    parser.add_argument("--out", type=Path, help="write Markdown here")
    parser.add_argument("--root", type=Path, help="repository root")
    args = parser.parse_args()
    root = repo_root(args.root) if args.root else repo_root()
    reg = registry.load(root)
    try:
        rows = cost.read_ledger(args.ledger)
        summary = cost.summarise(reg, rows)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    text = cost.render(reg, summary, args.period)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text, end="")
    return EXIT_FINDINGS if cost.alerts(reg, summary) else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
