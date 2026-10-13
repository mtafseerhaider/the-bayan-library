#!/usr/bin/env python3
"""Check that an agent-authored change stays inside its permission tier.

The agent is named by --agent, or read from an `agent_id:` line in the
pull request body (the AI provenance block of the PR template). A missing
agent ID is a usage error: an agent-authored PR must keep that block.
Changed files come from arguments or from `git diff --name-only BASE...HEAD`.

Exit codes: 0 allowed, 1 out-of-tier writes, 2 usage error.
"""

import argparse
import os
import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

import _bootstrap  # noqa: F401
from bayan import registry
from bayan.common import EXIT_USAGE, Report, repo_root

AGENT_LINE = re.compile(
    r"(?im)^[ \t]*[-*]?[ \t]*agent_id:[ \t]*`?([a-z0-9][a-z0-9-]*)`?")


def changed_files(root: Path, base: str) -> list[str]:
    result = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"],
                            cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"git diff failed: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line]


def agent_from_body(body: str) -> str | None:
    match = AGENT_LINE.search(body or "")
    return match.group(1) if match else None


def owner_patterns(root: Path) -> list[str]:
    """Patterns from .github/CODEOWNERS: paths that need owner approval.

    The file uses anchored patterns (`/docs/`, `/README.md`); the leading
    slash is dropped so they compare against repository-relative paths.
    """
    path = root / ".github" / "CODEOWNERS"
    patterns = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                patterns.append(line.split()[0].lstrip("/"))
    return patterns


def needs_owner(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith("/"):
            if path.startswith(pattern):
                return True
        elif path == pattern or fnmatch(path, pattern):
            return True
    return False


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
        print("error: no agent_id given (--agent) or found in the PR body; "
              "agent-authored PRs must keep the AI provenance block",
              file=sys.stderr)
        return EXIT_USAGE
    agent = reg.agents.get(agent_id)
    if agent is None:
        print(f"error: unknown agent {agent_id!r}", file=sys.stderr)
        return EXIT_USAGE
    files = args.files or (changed_files(root, args.base) if args.base
                           else [])

    tier = agent["permission_level"]
    patterns = owner_patterns(root)
    report = Report(f"Permission check for {agent_id} (tier {tier})")
    for path in files:
        allowed = registry.tiers_allowed_to_write(reg, path)
        if tier not in allowed:
            need = f"tier {min(allowed)}" if allowed else "the owner only"
            report.add("critical", "out-of-tier",
                       f"{path} needs {need}", path)
        elif needs_owner(path, patterns):
            report.add("minor", "owner-approval",
                       "path requires G4 owner approval (CODEOWNERS)", path)
    report.print()
    return report.exit_code("critical")


if __name__ == "__main__":
    sys.exit(main())
