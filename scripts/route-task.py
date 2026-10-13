#!/usr/bin/env python3
"""Route a task to a model class with the reference router.

Reads a task spec (YAML or JSON) from a file or stdin and prints the
routing decision as JSON. Example:

    echo 'task: canon_ranking
    agent: canon-editor
    signals: {canon_decision: true}
    input_tokens: 60000
    change_classes: [ranking_change]' | scripts/route-task.py -

Exit codes: 0 routed, 1 needs justification or blocked, 2 usage error.
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

import _bootstrap  # noqa: F401
from bayan import registry, router
from bayan.common import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, repo_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(__doc__.splitlines()[2:]))
    parser.add_argument("spec", help="task spec file, or - for stdin")
    parser.add_argument("--root", type=Path, help="repository root")
    args = parser.parse_args()
    root = repo_root(args.root) if args.root else repo_root()
    text = sys.stdin.read() if args.spec == "-" else \
        Path(args.spec).read_text(encoding="utf-8")
    spec = yaml.safe_load(text) or {}
    try:
        decision = router.route(registry.load(root), spec)
    except router.RoutingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    print(json.dumps(decision.to_dict(), indent=2))
    return EXIT_OK if decision.status == "ok" else EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
