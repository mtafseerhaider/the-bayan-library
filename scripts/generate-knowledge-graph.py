#!/usr/bin/env python3
"""Generate the knowledge graph, its maps and Mermaid previews.

Writes build/graph/ (git-ignored): graph.json, adjacency.json, one JSON and
one .mmd file per map, and stats.json. Inverse edges are materialised.

Exit codes: 0 written, 1 validation findings (critical), 2 usage error.
"""

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from bayan import graph, metadata, registry
from bayan.common import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, Report, \
    rel, repo_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, help="repository root")
    parser.add_argument("--out", type=Path, help="output directory "
                        "(default: build/graph)")
    args = parser.parse_args()
    root = repo_root(args.root) if args.root else repo_root()
    reg_report = Report("Registry")
    reg = registry.load(root, reg_report)
    if reg_report.failed("critical"):
        reg_report.print()
        return EXIT_USAGE
    lib = metadata.load(root, reg)
    report = Report("Knowledge graph validation")
    graph.validate(lib, reg, report)
    if report.failed("critical"):
        report.print()
        return EXIT_FINDINGS
    built = graph.build(lib, reg)
    out = args.out or root / "build" / "graph"
    for path in graph.write(built, reg, out):
        print(f"wrote {rel(path, root)}")
    print(f"Graph: {len(built['nodes'])} nodes, {len(built['edges'])} edges")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
