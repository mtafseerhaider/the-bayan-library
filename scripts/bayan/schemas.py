"""JSON Schema loading and validation with local `$ref` resolution."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .common import load_json


@lru_cache(maxsize=None)
def _registry(schema_dir: str) -> Registry:
    resources = []
    for path in sorted(Path(schema_dir).rglob("*.schema.json")):
        schema = load_json(path)
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


@lru_cache(maxsize=None)
def validator(schema_path: str) -> Draft202012Validator:
    path = Path(schema_path)
    schema = load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(
        schema, registry=_registry(str(path.parent)),
        format_checker=Draft202012Validator.FORMAT_CHECKER)


def errors(schema_path: Path, instance: Any) -> Iterator[str]:
    """Yield readable messages for every schema violation."""
    for error in sorted(validator(str(schema_path)).iter_errors(instance),
                        key=lambda e: list(e.absolute_path)):
        where = "/".join(str(p) for p in error.absolute_path) or "(root)"
        yield f"{where}: {error.message}"
