#!/usr/bin/env python3
"""Validate internal Markdown links and heading anchors (offline).

Exit codes: 0 valid, 1 broken links, 2 usage error.
"""

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from bayan import links
from bayan.common import repo_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", type=Path,
                        help="Markdown files (default: whole repository)")
    parser.add_argument("--root", type=Path, help="repository root")
    args = parser.parse_args()
    root = repo_root(args.root) if args.root else repo_root()
    files = [f.resolve() for f in args.files] or None
    report = links.run(root, files)
    report.print()
    return report.exit_code("major")


if __name__ == "__main__":
    sys.exit(main())
