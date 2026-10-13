#!/usr/bin/env python3
"""Validate metadata records: schemas, IDs and referential integrity.

Exit codes: 0 valid, 1 findings at or above --fail-on, 2 usage error.
"""

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from bayan import metadata, registry
from bayan.common import EXIT_USAGE, Report, repo_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, help="repository root")
    parser.add_argument("--base-ref", help="git ref whose IDs must survive "
                        "(e.g. origin/main); enables the immutability check")
    parser.add_argument("--fail-on", choices=["critical", "major", "minor"],
                        default="major")
    args = parser.parse_args()
    root = repo_root(args.root) if args.root else repo_root()
    reg_report = Report("Registry")
    reg = registry.load(root, reg_report)
    if reg_report.failed("critical"):
        reg_report.print()
        return EXIT_USAGE
    try:
        report, lib = metadata.run(root, reg, args.base_ref)
    except metadata.RefError as exc:
        print(f"error: {exc} (fetch the base branch first)", file=sys.stderr)
        return EXIT_USAGE
    report.print()
    print(f"{len(lib.records)} records, {len(lib.relationships)} "
          "relationships")
    return report.exit_code(args.fail_on)


if __name__ == "__main__":
    sys.exit(main())
