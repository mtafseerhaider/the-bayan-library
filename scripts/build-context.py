#!/usr/bin/env python3
"""Assemble a context pack with the retrieval ladder under a token budget.

Example:

    scripts/build-context.py book-muqaddimah author-ibn-khaldun \\
        --budget 8000 --max-layer executive

Each target may carry a relevance weight: book-muqaddimah=1.0.
Prints the context pack as JSON (layers used, tokens, dropped items).

Exit codes: 0 built, 1 a target is missing or was dropped, 2 usage error.
"""

import argparse
import json
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from bayan import retrieval
from bayan.common import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, repo_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(__doc__.splitlines()[2:]))
    parser.add_argument("targets", nargs="+", help="record IDs[=relevance]")
    parser.add_argument("--budget", type=int, required=True)
    parser.add_argument("--max-layer", choices=retrieval.LAYERS,
                        default="full")
    parser.add_argument("--root", type=Path, help="repository root")
    args = parser.parse_args()
    root = repo_root(args.root) if args.root else repo_root()
    targets = {}
    for item in args.targets:
        name, _, weight = item.partition("=")
        try:
            targets[name] = float(weight) if weight else 1.0
        except ValueError:
            print(f"error: bad relevance in {item!r}", file=sys.stderr)
            return EXIT_USAGE
    pack = retrieval.build(root, targets, args.budget, args.max_layer)
    print(json.dumps(pack, indent=2, ensure_ascii=False))
    return EXIT_FINDINGS if pack["missing"] or pack["dropped"] else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
