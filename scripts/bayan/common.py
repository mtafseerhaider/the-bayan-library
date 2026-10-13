"""Common helpers: repository paths, YAML loading, findings and exit codes."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

import yaml

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

SEVERITIES = ("critical", "major", "minor")


def repo_root(start: Path | None = None) -> Path:
    """Return the repository root (the directory holding system/registry)."""
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "system" / "registry").is_dir():
            return candidate
    raise SystemExit("Could not locate repository root (system/registry).")


class _StringDateLoader(yaml.SafeLoader):
    """SafeLoader that keeps dates and timestamps as plain strings.

    JSON Schema has no date type, and identifiers such as `2026-10-13`
    must round-trip unchanged.
    """


_StringDateLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers
          if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.load(handle, Loader=_StringDateLoader)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True,
                          width=78)


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


@dataclass(order=True)
class Finding:
    """One validation result. Sorted by severity, then location."""

    sort_key: tuple = field(init=False, repr=False)
    severity: str
    code: str
    message: str
    location: str = ""

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"unknown severity {self.severity!r}")
        self.sort_key = (SEVERITIES.index(self.severity), self.location,
                         self.code, self.message)

    def render(self) -> str:
        where = f"{self.location}: " if self.location else ""
        return f"[{self.severity}] {where}{self.code}: {self.message}"


class Report:
    """Collects findings and turns them into an exit code."""

    def __init__(self, title: str) -> None:
        self.title = title
        self.findings: list[Finding] = []

    def add(self, severity: str, code: str, message: str,
            location: str = "") -> None:
        self.findings.append(Finding(severity, code, message, location))

    def extend(self, findings: Iterable[Finding]) -> None:
        self.findings.extend(findings)

    def counts(self) -> dict[str, int]:
        return {s: sum(1 for f in self.findings if f.severity == s)
                for s in SEVERITIES}

    def failed(self, fail_on: str = "minor") -> bool:
        limit = SEVERITIES.index(fail_on)
        return any(SEVERITIES.index(f.severity) <= limit
                   for f in self.findings)

    def print(self, stream=sys.stdout) -> None:
        for finding in sorted(self.findings):
            print(finding.render(), file=stream)
        counts = self.counts()
        summary = ", ".join(f"{counts[s]} {s}" for s in SEVERITIES)
        status = "FAIL" if self.failed("major") else \
            "WARN" if self.findings else "OK"
        print(f"{self.title}: {status} ({summary})", file=stream)

    def exit_code(self, fail_on: str = "minor") -> int:
        return EXIT_FINDINGS if self.failed(fail_on) else EXIT_OK


def iter_files(base: Path, patterns: Iterable[str]) -> Iterator[Path]:
    seen: set[Path] = set()
    for pattern in patterns:
        for path in sorted(base.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def estimate_tokens(text: str) -> int:
    """Cheap, deterministic token estimate (about 4 characters per token).

    Used only for budgeting and index cards. Exact counts come from the
    API's token-counting endpoint when a model call is actually planned.
    """
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)
