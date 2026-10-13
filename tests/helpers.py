"""Test helpers: build throwaway repository roots from the real registries
plus fixture metadata, so tests never touch the working tree."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "library"
sys.path.insert(0, str(REPO / "scripts"))

from bayan import registry  # noqa: E402


class TempRepo:
    """A temporary repository root with system/ copied from the repo."""

    def __init__(self, with_fixture: bool = True) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        shutil.copytree(REPO / "system", self.root / "system")
        if with_fixture:
            shutil.copytree(FIXTURE, self.root, dirs_exist_ok=True)

    def write(self, relative: str, data) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        text = data if isinstance(data, str) else \
            yaml.safe_dump(data, sort_keys=False)
        path.write_text(text, encoding="utf-8")
        return path

    def read_yaml(self, relative: str):
        return yaml.safe_load((self.root / relative).read_text())

    def registries(self):
        return registry.load(self.root)

    def cleanup(self) -> None:
        self._dir.cleanup()
