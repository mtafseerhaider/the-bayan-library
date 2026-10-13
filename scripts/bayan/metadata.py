"""Metadata records: loading, schema validation and referential integrity.

Records live under metadata/ in either layout, which may be mixed:

* a list file per type, e.g. metadata/books.yaml (as in docs/07), or
* one record per file, e.g. metadata/books/w/book-war-and-peace.yaml,
  which is the recommended layout once a type passes a few hundred
  records (small diffs, no merge conflicts, cheap partial loads).

Relationships use the same two layouts under the name `relationships`.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from . import schemas
from .common import Report, load_yaml, rel
from .registry import Registries

# metadata directory name -> schema file stem
SCHEMAS = {
    "books": "book",
    "authors": "author",
    "poets": "poet",
    "civilizations": "civilization",
    "themes": "theme",
    "concepts": "concept",
    "reading-paths": "reading-path",
    "canons": "canon",
    "quotations": "quotation",
}

# Fields whose values are record IDs, checked for referential integrity.
REFERENCE_FIELDS = (
    "author_id", "related_books", "canon_memberships", "major_works",
    "influenced_by", "influenced", "related_thinkers", "related_poets",
    "related_concepts", "themes", "included_books", "prerequisites",
    "replaced_by",
)


@dataclass
class Record:
    id: str
    type: str
    data: dict
    path: Path


@dataclass
class Library:
    root: Path
    records: dict[str, Record] = field(default_factory=dict)
    relationships: list[dict] = field(default_factory=list)
    relationship_paths: list[str] = field(default_factory=list)
    prefix_to_type: dict[str, str] = field(default_factory=dict)
    type_to_dir: dict[str, str] = field(default_factory=dict)

    def by_type(self, node_type: str) -> list[Record]:
        return sorted((r for r in self.records.values()
                       if r.type == node_type), key=lambda r: r.id)


def metadata_dir(root: Path) -> Path:
    return root / "metadata"


def _as_records(content: Any) -> list[dict]:
    if content is None:
        return []
    if isinstance(content, list):
        return content
    if isinstance(content, dict) and isinstance(content.get("records"),
                                                list):
        return content["records"]
    if isinstance(content, dict):
        return [content]
    raise ValueError("expected a mapping or a list of mappings")


def load(root: Path, reg: Registries, report: Report | None = None
         ) -> Library:
    lib = Library(root=root)
    for node in reg.graph["node_types"]:
        lib.prefix_to_type[node["prefix"]] = node["type"]
        lib.type_to_dir[node["type"]] = node["metadata_dir"]
    base = metadata_dir(root)
    if not base.is_dir():
        return lib

    schema_root = root / "system" / "schemas" / "metadata"
    for node in reg.graph["node_types"]:
        dir_name = node["metadata_dir"]
        schema = schema_root / f"{SCHEMAS.get(dir_name, 'generic')}" \
            ".schema.json"
        files: list[Path] = []
        list_file = base / f"{dir_name}.yaml"
        if list_file.is_file():
            files.append(list_file)
        shard_dir = base / dir_name
        if shard_dir.is_dir():
            files.extend(sorted(p for p in shard_dir.rglob("*.yaml")
                                if p.is_file()))
        for path in files:
            location = rel(path, root)
            try:
                items = _as_records(load_yaml(path))
            except Exception as exc:  # malformed YAML is critical
                if report:
                    report.add("critical", "yaml", str(exc), location)
                continue
            sharded = path != list_file
            if sharded and len(items) == 1 and report:
                expected = f"{items[0].get('id')}.yaml"
                if path.name != expected:
                    report.add("major", "file-name",
                               f"one-record files must be named {expected}",
                               location)
            for item in items:
                _add_record(lib, report, item, node, schema, path, location)

    rel_files = []
    if (base / "relationships.yaml").is_file():
        rel_files.append(base / "relationships.yaml")
    if (base / "relationships").is_dir():
        rel_files.extend(sorted((base / "relationships").rglob("*.yaml")))
    rel_schema = schema_root / "relationship.schema.json"
    for path in rel_files:
        location = rel(path, root)
        lib.relationship_paths.append(location)
        try:
            items = _as_records(load_yaml(path))
        except Exception as exc:
            if report:
                report.add("critical", "yaml", str(exc), location)
            continue
        for index, item in enumerate(items):
            if report:
                for message in schemas.errors(rel_schema, item):
                    report.add("critical", "schema", message,
                               f"{location}[{index}]")
            if isinstance(item, dict):
                lib.relationships.append({**item, "_location":
                                          f"{location}[{index}]"})
    return lib


def _add_record(lib: Library, report: Report | None, item: Any, node: dict,
                schema: Path, path: Path, location: str) -> None:
    if not isinstance(item, dict) or "id" not in item:
        if report:
            report.add("critical", "record", "record without an id",
                       location)
        return
    record_id = str(item["id"])
    where = f"{location}#{record_id}"
    if report:
        for message in schemas.errors(schema, item):
            report.add("critical", "schema", message, where)
        if not record_id.startswith(node["prefix"] + "-"):
            report.add("critical", "prefix",
                       f"{node['type']} IDs must start with "
                       f"'{node['prefix']}-'", where)
    if record_id in lib.records:
        if report:
            other = rel(lib.records[record_id].path, lib.root)
            report.add("critical", "duplicate-id",
                       f"ID already defined in {other}", where)
        return
    lib.records[record_id] = Record(record_id, node["type"], item, path)


def looks_like_id(value: Any, prefixes: Iterable[str]) -> bool:
    if not isinstance(value, str) or "-" not in value:
        return False
    return value.split("-", 1)[0] in prefixes and value == value.lower() \
        and " " not in value


def check_references(lib: Library, report: Report) -> None:
    prefixes = set(lib.prefix_to_type)
    for record in lib.records.values():
        where = f"{rel(record.path, lib.root)}#{record.id}"
        for name in REFERENCE_FIELDS:
            value = record.data.get(name)
            values = value if isinstance(value, list) else [value]
            for target in values:
                if not looks_like_id(target, prefixes):
                    continue
                if target not in lib.records:
                    report.add("critical", "dangling-reference",
                               f"{name} -> {target} does not exist", where)
        for entry in record.data.get("entries", []) or []:
            work = entry.get("work_id") if isinstance(entry, dict) else None
            if work and work not in lib.records:
                report.add("critical", "dangling-reference",
                           f"canon entry -> {work} does not exist", where)
        if record.data.get("status") == "deprecated" and \
                not record.data.get("replaced_by"):
            report.add("major", "deprecation",
                       "deprecated records need replaced_by", where)


def check_tags(lib: Library, report: Report) -> None:
    vocab_path = metadata_dir(lib.root) / "tags.yaml"
    if not vocab_path.is_file():
        return
    vocab = load_yaml(vocab_path) or {}
    allowed = set(vocab.get("tags", vocab) if isinstance(vocab, dict)
                  else vocab)
    for record in lib.records.values():
        for tag in record.data.get("tags", []) or []:
            if tag not in allowed:
                report.add("minor", "tag",
                           f"tag {tag!r} is not in metadata/tags.yaml",
                           f"{rel(record.path, lib.root)}#{record.id}")


class RefError(ValueError):
    """A git ref needed for a check cannot be read."""


def ids_at_ref(root: Path, ref: str) -> set[str]:
    """IDs recorded in the committed retrieval index at a git ref.

    An unreadable ref raises RefError: a check that silently compared
    against nothing would pass a deleted ID.
    """
    try:
        listing = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", ref, "metadata/index/"],
            cwd=root, capture_output=True, text=True, check=True).stdout
    except FileNotFoundError as exc:
        raise RefError("git is not installed") from exc
    except subprocess.CalledProcessError as exc:
        raise RefError(f"cannot read {ref!r}: "
                       f"{exc.stderr.strip() or 'git ls-tree failed'}"
                       ) from exc
    ids: set[str] = set()
    for name in listing.split():
        if not name.endswith(".jsonl"):
            continue
        blob = subprocess.run(["git", "show", f"{ref}:{name}"], cwd=root,
                              capture_output=True, text=True).stdout
        for line in blob.splitlines():
            if line.strip():
                ids.add(json.loads(line)["id"])
    return ids


def check_immutability(lib: Library, report: Report, base_ref: str) -> None:
    for missing in sorted(ids_at_ref(lib.root, base_ref) -
                          set(lib.records)):
        report.add("critical", "id-removed",
                   f"{missing} existed at {base_ref}; IDs are permanent. "
                   "Mark the record deprecated with replaced_by instead.",
                   "metadata/")


def run(root: Path, reg: Registries, base_ref: str | None = None
        ) -> tuple[Report, Library]:
    report = Report("Metadata validation")
    lib = load(root, reg, report)
    check_references(lib, report)
    check_tags(lib, report)
    if base_ref:
        check_immutability(lib, report, base_ref)
    return report, lib
