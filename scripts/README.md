# Scripts

## Purpose

Deterministic tooling for validation, indexing, graph generation, model
routing, context assembly and cost reporting. No script calls a model or
the network. Shared code lives in [`bayan/`](bayan/).

## Commands

| Script | Purpose |
| --- | --- |
| `validate-registry.py` | Registries against schemas and cross-file rules |
| `validate-metadata.py` | Records: schemas, permanent IDs, references |
| `validate-knowledge-graph.py` | Relationship signatures, evidence, duplicates |
| `validate-reading-paths.py` | Path members, level sizes, prerequisite order |
| `validate-links.py` | Internal Markdown links and anchors |
| `check-permissions.py` | Agent-authored changes stay inside the agent's tier |
| `build-index.py` | Sharded retrieval index in `metadata/index/` |
| `generate-knowledge-graph.py` | Graph, maps and Mermaid previews in `build/graph/` |
| `generate-registry-docs.py` | Catalogs in `system/generated/` |
| `route-task.py` | Reference model router |
| `build-context.py` | Reference retrieval-ladder context builder |
| `cost-report.py` | Monthly cost report from the usage ledger |

Exit codes: `0` success, `1` findings or drift, `2` usage error.

## Setup

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -t tests
```
