#!/usr/bin/env python3
"""Build the sharded retrieval index under metadata/index/.

With --check, write nothing and fail if the committed index is stale.

Exit codes: 0 up to date or written, 1 drift (with --check), 2 usage error.
"""

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from bayan import index, metadata, registry
from bayan.common import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, Report, \
    repo_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, help="repository root")
    parser.add_argument("--check", action="store_true",
                        help="fail if the committed index is out of date")
    args = parser.parse_args()
    root = repo_root(args.root) if args.root else repo_root()
    reg_report = Report("Registry")
    reg = registry.load(root, reg_report)
    if reg_report.failed("critical"):
        reg_report.print()
        return EXIT_USAGE
    lib = metadata.load(root, reg)
    files = index.build(lib)
    if args.check:
        problems = index.drift(lib, files)
        for problem in problems:
            print(f"[major] index-drift: {problem}")
        if problems:
            print("Run scripts/build-index.py and commit the result.")
            return EXIT_FINDINGS
        print(f"Index: OK ({len(lib.records)} records)")
        return EXIT_OK
    changed = index.write(lib, files)
    for name in changed:
        print(f"wrote {name}")
    print(f"Index: {len(lib.records)} records, {len(changed)} files changed")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
