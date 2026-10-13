#!/usr/bin/env python3
"""Validate knowledge graph relationships against the ontology.

Checks relationship signatures, evidence and citations, dangling nodes,
duplicate edges, self loops and inverse forms. Orphans are reported as
minor findings.

Exit codes: 0 valid, 1 findings at or above --fail-on, 2 usage error.
"""

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from bayan import graph, metadata, registry
from bayan.common import EXIT_USAGE, Report, repo_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, help="repository root")
    parser.add_argument("--fail-on", choices=["critical", "major", "minor"],
                        default="major")
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
    graph.orphan_report(lib, graph.build(lib, reg), report)
    report.print()
    return report.exit_code(args.fail_on)


if __name__ == "__main__":
    sys.exit(main())
