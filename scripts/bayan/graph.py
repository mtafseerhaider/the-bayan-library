"""Knowledge graph validation and generation.

Edges come from two places:

1. explicit relationship files (metadata/relationships*), which carry
   evidence levels and citations, and
2. reference fields on records (author_id, canon_memberships, ...), which
   are converted into edges with `derived: true`.

Only forward relationship types are stored; inverses are materialised at
build time so every edge is navigable in both directions.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .common import Report, rel
from .metadata import Library, looks_like_id
from .registry import Registries

# record field -> (relationship type, direction). direction "out" means
# record -> value; "in" means value -> record.
DERIVED_FIELDS = {
    "author_id": ("wrote", "in"),
    "major_works": ("wrote", "out"),
    "canon_memberships": ("member_of", "out"),
    "influenced_by": ("influenced", "in"),
    "influenced": ("influenced", "out"),
    "themes": ("has_theme", "out"),
    "included_books": ("member_of", "in"),
    "related_books": ("references", "out"),
}


def _signatures(reg: Registries) -> dict[str, dict]:
    return {r["type"]: r for r in reg.graph["relationship_types"]}


def _inverses(reg: Registries) -> dict[str, str]:
    return {r["inverse"]: r["type"] for r in reg.graph["relationship_types"]
            if r["inverse"] != r["type"]}


def node_type(lib: Library, node_id: str) -> str | None:
    if node_id in lib.records:
        return lib.records[node_id].type
    return lib.prefix_to_type.get(node_id.split("-", 1)[0])


def derived_edges(lib: Library) -> list[dict]:
    prefixes = set(lib.prefix_to_type)
    edges = []
    for record in sorted(lib.records.values(), key=lambda r: r.id):
        for name, (kind, direction) in DERIVED_FIELDS.items():
            value = record.data.get(name)
            for target in value if isinstance(value, list) else [value]:
                if not looks_like_id(target, prefixes) or \
                        target not in lib.records:
                    continue
                source, dest = (record.id, target) if direction == "out" \
                    else (target, record.id)
                edges.append({"source": source, "relationship": kind,
                              "target": dest, "derived": True})
    return edges


def validate(lib: Library, reg: Registries, report: Report) -> None:
    signatures = _signatures(reg)
    inverses = _inverses(reg)
    evidence = {e["id"]: e for e in reg.graph["evidence_levels"]}
    seen: dict[tuple, str] = {}
    for edge in lib.relationships:
        where = edge.get("_location", "metadata/relationships")
        source, kind, target = (edge.get("source"), edge.get("relationship"),
                                edge.get("target"))
        if kind in inverses:
            report.add("major", "inverse-stored",
                       f"store the forward form '{inverses[kind]}' "
                       f"(swap source and target) instead of '{kind}'",
                       where)
            continue
        if kind not in signatures:
            report.add("critical", "unknown-relationship",
                       f"relationship {kind!r} is not in the ontology "
                       "(system/registry/knowledge-graph.yaml)", where)
            continue
        if source == target:
            report.add("major", "self-loop", f"{source} -> itself", where)
        for end, role in ((source, "source"), (target, "target")):
            if end not in lib.records:
                report.add("critical", "dangling-node",
                           f"{role} {end} has no metadata record", where)
        signature = signatures[kind]
        source_type, target_type = node_type(lib, source), \
            node_type(lib, target)
        if source_type and source_type not in signature["source"]:
            report.add("critical", "signature",
                       f"{kind} cannot start at a {source_type}", where)
        if target_type and target_type not in signature["target"]:
            report.add("critical", "signature",
                       f"{kind} cannot end at a {target_type}", where)
        level = edge.get("confidence")
        if level is None:
            report.add("minor", "evidence",
                       "no confidence level; defaulting to tentative", where)
        elif evidence[level]["requires_citation"] and \
                not edge.get("citations"):
            report.add("major", "citation",
                       f"{level}-confidence edges must cite a source", where)
        key = (source, kind, target)
        if signature.get("symmetric"):
            key = (min(source, target), kind, max(source, target))
        if key in seen:
            report.add("major", "duplicate-edge",
                       f"duplicates the edge at {seen[key]}", where)
        else:
            seen[key] = where


def build(lib: Library, reg: Registries) -> dict:
    """Return the full graph with inverse edges materialised."""
    signatures = _signatures(reg)
    edges: list[dict] = []
    keys = set()

    def add(edge: dict) -> None:
        key = (edge["source"], edge["relationship"], edge["target"])
        if key not in keys:
            keys.add(key)
            edges.append(edge)

    explicit = [
        {k: v for k, v in e.items() if not k.startswith("_")}
        for e in lib.relationships
        if e.get("relationship") in signatures
        and e.get("source") in lib.records and e.get("target") in lib.records
    ]
    for edge in explicit + derived_edges(lib):
        edge = {"confidence": "tentative", **edge}
        add(edge)
        signature = signatures[edge["relationship"]]
        add({**edge, "source": edge["target"], "target": edge["source"],
             "relationship": signature["inverse"], "inverse_of":
             edge["relationship"]})

    nodes = []
    for record in sorted(lib.records.values(), key=lambda r: r.id):
        nodes.append({
            "id": record.id,
            "type": record.type,
            "label": record.data.get("title") or record.data.get("name")
            or record.id,
            "status": record.data.get("status", "draft"),
        })
    edges.sort(key=lambda e: (e["source"], e["relationship"], e["target"]))
    return {"version": 1, "nodes": nodes, "edges": edges}


def adjacency(graph: dict) -> dict[str, list[list[str]]]:
    """Node -> [[relationship, neighbour], ...] for O(1) neighbourhood."""
    table: dict[str, list[list[str]]] = defaultdict(list)
    for edge in graph["edges"]:
        table[edge["source"]].append([edge["relationship"], edge["target"]])
    return {node: sorted(pairs) for node, pairs in sorted(table.items())}


def subgraph(graph: dict, graph_map: dict) -> dict:
    node_types = set(graph_map["node_types"])
    forward = set(graph_map["relationship_types"])
    nodes = [n for n in graph["nodes"] if n["type"] in node_types]
    keep = {n["id"] for n in nodes}
    edges = [e for e in graph["edges"]
             if (e["relationship"] in forward
                 or e.get("inverse_of") in forward)
             and e["source"] in keep and e["target"] in keep]
    return {"version": 1, "map": graph_map["id"], "nodes": nodes,
            "edges": edges}


def neighbourhood(graph: dict, seeds: list[str], depth: int = 1,
                  relationships: set[str] | None = None,
                  max_degree: int = 50) -> dict:
    """Bounded breadth-first neighbourhood (the graph-query skill)."""
    if depth > 2:
        raise ValueError("depth is capped at 2 to keep context small")
    table = adjacency(graph)
    frontier, seen = list(seeds), set(seeds)
    edges = []
    for _ in range(depth):
        nxt = []
        for node in frontier:
            pairs = [p for p in table.get(node, [])
                     if relationships is None or p[0] in relationships]
            for kind, other in pairs[:max_degree]:
                edges.append({"source": node, "relationship": kind,
                              "target": other})
                if other not in seen:
                    seen.add(other)
                    nxt.append(other)
        frontier = nxt
    nodes = [n for n in graph["nodes"] if n["id"] in seen]
    return {"seeds": seeds, "depth": depth, "nodes": nodes, "edges": edges}


def mermaid(graph: dict, limit: int = 150) -> str:
    """A Mermaid preview of forward edges, capped for readability."""
    lines = ["flowchart LR"]
    labels = {n["id"]: n["label"].replace('"', "'") for n in graph["nodes"]}
    forward = [e for e in graph["edges"] if "inverse_of" not in e][:limit]
    used = sorted({e["source"] for e in forward} |
                  {e["target"] for e in forward})
    alias = {node: f"n{i}" for i, node in enumerate(used)}
    for node in used:
        lines.append(f'    {alias[node]}["{labels.get(node, node)}"]')
    for edge in forward:
        lines.append(f"    {alias[edge['source']]} -- "
                     f"{edge['relationship']} --> {alias[edge['target']]}")
    return "\n".join(lines) + "\n"


def write(graph: dict, reg: Registries, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    def dump(name: str, data) -> None:
        path = out_dir / name
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        written.append(path)

    dump("graph.json", graph)
    dump("adjacency.json", adjacency(graph))
    for graph_map in reg.graph["maps"]:
        part = subgraph(graph, graph_map)
        dump(f"{graph_map['id']}.json", part)
        path = out_dir / f"{graph_map['id']}.mmd"
        path.write_text(mermaid(part), encoding="utf-8")
        written.append(path)
    stats = {
        "nodes": len(graph["nodes"]),
        "edges": len(graph["edges"]),
        "maps": {m["id"]: len(subgraph(graph, m)["edges"])
                 for m in reg.graph["maps"]},
    }
    dump("stats.json", stats)
    return written


def orphan_report(lib: Library, graph: dict, report: Report) -> None:
    connected = {e["source"] for e in graph["edges"]}
    for record in lib.records.values():
        if record.id not in connected and record.type != "note":
            report.add("minor", "orphan",
                       "node has no relationships",
                       f"{rel(record.path, lib.root)}#{record.id}")
