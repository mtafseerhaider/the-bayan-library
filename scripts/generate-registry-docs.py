#!/usr/bin/env python3
"""Generate system/generated/ catalogs from the registries.

With --check, write nothing and fail if a committed catalog is stale.

Exit codes: 0 up to date or written, 1 drift or invalid registry,
2 usage error.
"""

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from bayan import catalog, registry
from bayan.common import EXIT_FINDINGS, EXIT_OK, repo_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, help="repository root")
    parser.add_argument("--check", action="store_true",
                        help="fail if committed catalogs are out of date")
    args = parser.parse_args()
    root = repo_root(args.root) if args.root else repo_root()
    report = registry.run(root)
    if report.failed("critical"):
        report.print()
        return EXIT_FINDINGS
    files = catalog.build(registry.load(root))
    stale = []
    for name, content in files.items():
        path = root / name
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current == content:
            continue
        if args.check:
            stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"wrote {name}")
    for name in stale:
        print(f"[major] catalog-drift: {name} is out of date")
    if stale:
        print("Run scripts/generate-registry-docs.py and commit the result.")
        return EXIT_FINDINGS
    print("Catalogs: OK")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
