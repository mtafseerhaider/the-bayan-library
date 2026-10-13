#!/usr/bin/env python3
"""Check that an agent-authored change stays inside its permission tier.

The agent is named by --agent, or read from an `agent_id:` line in the
pull request body (the AI provenance block of the PR template). Changed
files come from arguments or from `git diff --name-only BASE...HEAD`.

Exit codes: 0 allowed, 1 out-of-tier writes, 2 usage error.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from bayan import registry
from bayan.common import EXIT_USAGE, Report, repo_root

# Paths whose changes need owner approval (G4) whoever authored them.
G4_PATHS = ("canon/", "reading-paths/", "docs/", "system/", ".github/")


def changed_files(root: Path, base: str) -> list[str]:
    result = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"],
                            cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"git diff failed: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line]


def agent_from_body(body: str) -> str | None:
    match = re.search(r"(?im)^\s*[-*]?\s*agent_id:\s*`?([a-z0-9-]+)`?",
                      body or "")
    return match.group(1) if match else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", help="changed paths")
    parser.add_argument("--agent", help="agent_id of the author")
    parser.add_argument("--pr-body-env", metavar="VAR",
                        help="environment variable holding the PR body")
    parser.add_argument("--base", help="git ref to diff against")
    parser.add_argument("--root", type=Path, help="repository root")
    args = parser.parse_args()
    root = repo_root(args.root) if args.root else repo_root()
    reg = registry.load(root)

    agent_id = args.agent
    if not agent_id and args.pr_body_env:
        agent_id = agent_from_body(os.environ.get(args.pr_body_env, ""))
    if not agent_id:
        print("No agent_id given or found in the PR body; nothing to check.")
        return 0
    agent = reg.agents.get(agent_id)
    if agent is None:
        print(f"error: unknown agent {agent_id!r}", file=sys.stderr)
        return EXIT_USAGE
    files = args.files or (changed_files(root, args.base) if args.base
                           else [])

    tier = agent["permission_level"]
    report = Report(f"Permission check for {agent_id} (tier {tier})")
    for path in files:
        allowed = registry.tiers_allowed_to_write(reg, path)
        if tier not in allowed:
            need = f"tier {min(allowed)}" if allowed else "the owner only"
            report.add("critical", "out-of-tier",
                       f"{path} needs {need}", path)
        elif path.startswith(G4_PATHS):
            report.add("minor", "owner-approval",
                       "path requires G4 owner approval (CODEOWNERS)", path)
    report.print()
    return report.exit_code("critical")


if __name__ == "__main__":
    sys.exit(main())
