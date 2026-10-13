#!/usr/bin/env python3
"""Validate system/registry/* against schemas and cross-file rules.

Exit codes: 0 valid, 1 findings, 2 usage error.
"""

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from bayan import registry
from bayan.common import repo_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", help="repository root (auto-detected)")
    args = parser.parse_args()
    root = repo_root(Path(args.root)) if args.root else repo_root()
    report = registry.run(root)
    report.print()
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
