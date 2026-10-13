# AI-Native Architecture

## Purpose

This folder is the operating architecture of The Bayan Library: how a
network of AI agents, under human supervision, maintains a library meant
to grow for fifty years and hold 10,000+ books, 5,000+ authors, 100,000+
notes and 20,000+ concepts.

It turns the governing specifications in [`docs/`](../) into a system that
can run. It creates no library content.

## The Principle

Every agent, skill and workflow serves one transformation:

```text
Information -> Knowledge -> Understanding -> Wisdom -> Action -> Character
```

And one golden rule:

> Use the smallest model with the smallest context that can reliably
> solve the task.

## How to Read This Folder

The documents explain; the registries decide. Every number, ID, tier and
budget below lives in machine-readable form under
[`system/registry/`](../../system/registry/), is validated by
`scripts/validate-registry.py`, and is rendered into the
[generated catalogs](../../system/generated/).

| No. | Document | Source of truth |
| ---: | --- | --- |
| 1 | [System Architecture Overview](01-system-architecture-overview.md) | all registries |
| 2 | [Agent Registry](02-agent-registry.md) | `agents/*.yaml` |
| 3 | [Skill Registry](03-skill-registry.md) | `skills.yaml` |
| 4 | [Permission Model](04-permission-model.md) | `permissions.yaml` |
| 5 | [Model Routing Framework](05-model-routing-framework.md) | `routing.yaml`, `models.yaml` |
| 6 | [Token Optimization Framework](06-token-optimization-framework.md) | `models.yaml`, `routing.yaml` |
| 7 | [Memory Architecture](07-memory-architecture.md) | `memory.yaml` |
| 8 | [Knowledge Graph Architecture](08-knowledge-graph-architecture.md) | `knowledge-graph.yaml` |
| 9 | [Workflow Architecture](09-workflow-architecture.md) | `workflows.yaml` |
| 10 | [GitHub Architecture](10-github-architecture.md) | `.github/` |
| 11 | [Automation Architecture](11-automation-architecture.md) | `.github/workflows/`, `scripts/` |
| 12 | [Quality Assurance Framework](12-quality-assurance-framework.md) | `agents/*.yaml`, `review-gates.yaml` |
| 13 | [Evaluation Framework](13-evaluation-framework.md) | `agents/*.yaml` |
| 14 | [Cost Governance Framework](14-cost-governance-framework.md) | `budgets.yaml`, `models.yaml` |
| 15 | [Human Review Framework](15-human-review-framework.md) | `review-gates.yaml` |
| 16 | [Risk Analysis](16-risk-analysis.md) | extends [Risk Register](../16-risk-register.md) |
| 17 | [Future Roadmap](17-future-roadmap.md) | extends [Implementation Roadmap](../15-implementation-roadmap.md) |

## At a Glance

| Element | Count or rule |
| --- | --- |
| Agents | 46 in four families: core 16, Quran 9, daily 11, learning 10 |
| Skills | 43, in a validated dependency DAG |
| Permission tiers | 5; every agent in exactly one; the owner above all |
| Complexity classes | A Haiku, B and C Sonnet, D and E Opus |
| Models | `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5` |
| Token caps (in / out) | Haiku 10K / 2K, Sonnet 30K / 5K, Opus 100K / 10K |
| Retrieval ladder | metadata card, summary, executive summary, full text |
| Memory layers | working, session, project, repository, canonical, personal reflection |
| Review gates | G0 automated to G4 owner approval |
| Monthly budget | USD 60 in six envelopes, with an escalation reserve |
| CI | validate, metadata, knowledge-graph, index, release |

## Human Supervision

No agent merges, approves or pushes to `main`. Every change arrives as a
pull request; canon, ranking, governance, Quran methodology and
architecture changes require the owner's approval through CODEOWNERS.
No GitHub workflow calls a paid model API; running agents from CI is a
later, opt-in step described in the
[Automation Architecture](11-automation-architecture.md).

## Working With the Tooling

```bash
pip install -r requirements.txt
python scripts/validate-registry.py          # registries are consistent
python scripts/generate-registry-docs.py     # refresh system/generated/
python scripts/route-task.py spec.yaml       # route one task
python scripts/build-index.py                # refresh the retrieval index
python -m unittest discover -s tests -t tests
```

## Architecture Summary

The architecture is a small set of plain-text registries, a handful of
deterministic scripts and a review process. Models, agents and tools will
change many times in fifty years; the registries, IDs, schemas and the
rule that a human approves what becomes canonical are designed to outlast
them.
