"""Internal Markdown link and anchor validation (no network access).

External links are not fetched: CI must stay deterministic and offline.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote

from .common import Report, rel

EXCLUDED_DIRS = {".git", "node_modules", "build", ".bayan", ".venv"}
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def markdown_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md")
                  if not EXCLUDED_DIRS & set(p.relative_to(root).parts))


def github_slug(text: str) -> str:
    """Approximate GitHub's heading anchor algorithm."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[`*~]", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


@lru_cache(maxsize=None)
def anchors(path: Path) -> frozenset[str]:
    found: list[str] = []
    counts: dict[str, int] = {}
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING.match(line)
        if not match:
            continue
        slug = github_slug(match.group(2))
        n = counts.get(slug, 0)
        counts[slug] = n + 1
        found.append(slug if n == 0 else f"{slug}-{n}")
    return frozenset(found)


def iter_links(path: Path):
    in_fence = False
    for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = re.sub(r"`[^`]*`", "", line)
        for pattern in (LINK, IMAGE):
            for match in pattern.finditer(stripped):
                yield number, match.group(1)
        for match in re.finditer(r'<img[^>]*\ssrc="([^"]+)"', stripped):
            yield number, match.group(1)


def check_file(path: Path, root: Path, report: Report) -> None:
    for number, target in iter_links(path):
        where = f"{rel(path, root)}:{number}"
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
            continue  # external (http, https, mailto, ...)
        file_part, _, anchor = target.partition("#")
        file_part = unquote(file_part)
        if file_part:
            if file_part.startswith("/"):
                dest = root / file_part.lstrip("/")
            else:
                dest = (path.parent / file_part)
            if not dest.exists():
                report.add("critical", "broken-link",
                           f"{target} does not exist", where)
                continue
        else:
            dest = path
        if anchor and dest.is_file() and dest.suffix == ".md":
            if anchor.lower() not in anchors(dest.resolve()):
                report.add("major", "broken-anchor",
                           f"#{anchor} not found in {rel(dest, root)}",
                           where)


def run(root: Path, files: list[Path] | None = None) -> Report:
    report = Report("Link validation")
    for path in files or markdown_files(root):
        check_file(path, root, report)
    return report
