# Risk Analysis

## Purpose

This document analyses the risks that the multi-agent architecture adds to
The Bayan Library: context, scale, coordination, quality, automation,
governance and long-term vendor and model risks. Each risk has an owner
agent, a mitigation built into the architecture, and an early-warning
signal that an existing metric or script can detect.

Source of truth: [Risk Register](../16-risk-register.md), which ends at
R-025; this document continues at R-026. Signals come from
`system/registry/budgets.yaml` metrics and the agents' `evaluation_metrics`
in `system/registry/agents/*.yaml`. The `risk-management` agent keeps both
documents in step during `monthly-cycle` and `annual-cycle`.

Related documents: [Cost Governance Framework](14-cost-governance-framework.md),
[Quality Assurance Framework](12-quality-assurance-framework.md),
[Automation Architecture](11-automation-architecture.md),
[Human Review Framework](15-human-review-framework.md) and
[Future Roadmap](17-future-roadmap.md).

## Scales and Scoring

Likelihood and impact use the Low, Medium and High scales of the risk
register. Priority is derived from both.

| Likelihood \ Impact | Low | Medium | High |
|---|---|---|---|
| High | Moderate | High | Critical |
| Medium | Low | Moderate | High |
| Low | Low | Low | Moderate |

Critical and High risks escalate to `chief-librarian` immediately, per the
`risk-management` escalation rule, and target mitigation within 30 days
(`mean_time_to_mitigation_days`).

## Context Risks

| ID | Risk | Description | L | I | Mitigation | Owner agent | Early-warning signal |
|---|---|---|---|---|---|---|---|
| R-026 | Context explosion | Retrieved context grows with the library until calls exceed budgets, cost rises and models lose focus | Medium | High | Per-model input caps (haiku 10K, sonnet 30K, opus 100K); retrieval ladder card -> summary -> executive summary -> full text; graph depth <= 2; `budget_policy` compresses before it escalates; hand-off cards <= 300 tokens | `quality-assurance` | `budget_overrun_count` above 0; `tokens_per_artifact` rising 3 months in a row; `cache_hit_rate` below 0.5 |

## Repository Scale Risks

| ID | Risk | Description | L | I | Mitigation | Owner agent | Early-warning signal |
|---|---|---|---|---|---|---|---|
| R-027 | Metadata file growth | Single YAML lists per type become huge, slow to parse and conflict-prone | High | Medium | One record per file, 2-char shards for large types (see [GitHub Architecture](10-github-architecture.md)) | `metadata` | Any `metadata/<type>.yaml` over 500 records or 1 MB |
| R-028 | CI time growth | Full validation on every PR becomes slow, so contributors skip checks | High | Medium | Changed-file validation on PRs, full runs nightly and on release; concurrency cancels stale runs | `automation` | `validate.yml` median duration over 10 minutes |
| R-029 | Index size | Retrieval index grows past what tools load comfortably | Medium | Medium | JSONL per type, split per shard when large; cards only, never bodies | `metadata` | Any `metadata/index/<type>.jsonl` over 50 MB |
| R-030 | Graph size | Edge count and inverse materialisation make builds slow and maps unreadable | Medium | Medium | Per-map files; graph is an artifact, not committed; depth-limited queries | `knowledge-graph` | `generate-knowledge-graph.py` runtime over 5 minutes; map previews over 500 nodes |
| R-031 | Git history growth | Decades of commits and generated files slow clones | Medium | Medium | Squash merges; generated artifacts outside git; no binaries; ebooks pointer policy | `automation` | Repository size over 1 GB or clone time over 5 minutes |

## Agent Coordination Risks

| ID | Risk | Description | L | I | Mitigation | Owner agent | Early-warning signal |
|---|---|---|---|---|---|---|---|
| R-032 | Conflicting edits | Two runs change the same record or path at once | Medium | Medium | One record per file; one run per branch; orchestrator refuses a run whose target IDs are in an open agent PR | `chief-librarian` | Merge conflicts on agent PRs; more than one open PR per record ID |
| R-033 | Duplicated work | Two agents produce the same note, summary or edge | Medium | Low | `duplicate-detection` before creation; index lookup at step 1; project memory lists claimed work | `metadata` | `duplicate_id_count` above 0; near-duplicate findings in QA |
| R-034 | Cascading errors | An early wrong output (record, summary) is consumed by later steps and spreads | Medium | High | QA between producing and consuming steps; daily entries draw only on reviewed records; reverts invalidate dependants via `inputs_hash` | `quality-assurance` | Same root cause in findings across more than one artifact |
| R-035 | Hand-off loss | A decision or open question is lost between steps or sessions | Medium | Medium | Structured hand-off cards (goal, decisions, open questions, files touched); project memory for multi-week work; 30-day run retention | `chief-librarian` | Open questions in cards not answered by the end of the run |

## Quality Risks

| ID | Risk | Description | L | I | Mitigation | Owner agent | Early-warning signal |
|---|---|---|---|---|---|---|---|
| R-036 | Hallucinated citations | A model cites a page, edition, commentary or quotation that does not exist | High | High | `citation-verification` (hybrid) on every G2-G4 output; G3 review with sources open; fabricated citation is a critical finding | `quality-assurance` | `claim_citation_rate` below 0.95; any citation marked unsupported by humans |
| R-037 | Summary drift | Layered summaries drift from the source as each layer is made from the previous one | Medium | High | Each layer graded for fidelity against the source excerpt, not only the layer above; golden-set fidelity checks | `study-notes` | `fidelity_score` below 0.9; human corrections concentrated in executive summaries |
| R-038 | Compression loss | `knowledge-compression` drops qualifications, so short forms overstate claims | Medium | Medium | Must-keep facts list in `context-compression`; dropped items recorded; daily entries traced to reviewed summaries | `study-notes` | QA flags of "overstated" or "missing qualification" |
| R-039 | Sectarian or civilizational bias | Agent outputs favour one school, tradition or civilization, or present an interpretation as consensus (see R-018, R-020, R-021) | Medium | High | `representation-check` and `bias-audit` skills; G3 for interpretation; `school_balance`, `tradition_balance`, `representation_balance_index` metrics | `islamic-civilization` | `representation_balance_index` below 0.7; any tradition above 40% of daily entries in a month |
| R-040 | Translation distortion | Agents rely on one translation or paraphrase originals silently (see R-022) | Medium | Medium | `translation-comparison` for poetry; original text and translator cited; uncertainty marked | `poetry` | `original_language_presence` below 0.9 |
| R-041 | Copyright exposure | Agents reproduce long copyrighted passages in summaries or quotations | Medium | High | Summaries and commentary over reproduction; quotation length limits in templates; ebooks policy | `quality-assurance` | QA flags of long verbatim passages |

## Automation Risks

| ID | Risk | Description | L | I | Mitigation | Owner agent | Early-warning signal |
|---|---|---|---|---|---|---|---|
| R-042 | Runaway cost | Loops, retries or escalations overspend the USD 60 month | Medium | High | Per-run caps; hard stop at 100% (110% for `daily-cycle`); retry once and escalate one rung only; escalation reserve; no model calls in CI | `risk-management` | Alerts at 50% and 80% of cap; `escalation_rate` above 0.15; `opus_share` above 0.35 |
| R-043 | Workflow compromise | A malicious or careless change to `.github/**` or an action leaks secrets or writes to protected branches | Low | High | Pinned action SHAs; least privilege; no secrets in validation; CODEOWNERS on `.github/`; future model key only in a protected environment | `automation` | Any workflow diff not labelled `gate:G4`; unpinned action found in review |
| R-044 | Silent failure | A scheduled run, validator or report stops without anyone noticing | Medium | Medium | Every cycle ends in a PR or an explicit `stopped_*` report; `on_time_publication` and `digest_on_time` metrics; weekly graph workflow | `risk-management` | Missing daily PR for 2 days; no cost report by the 3rd of the month |
| R-045 | Model deprecation | A model ID is retired or repriced | High | Medium | Classes, not IDs, in registries; one-file change in `models.yaml`; offline evaluation before switching | `chief-librarian` | Deprecation notice; price change on `last_reviewed` check |
| R-046 | Personal data leak | Private reflection content reaches a public path or a PR | Low | High | `notes/reflections/**` protected; only granted agents read the digest; private digests never enter PRs | `reflection-journal` | `privacy_incidents` above 0 |

## Governance Risks

| ID | Risk | Description | L | I | Mitigation | Owner agent | Early-warning signal |
|---|---|---|---|---|---|---|---|
| R-047 | Rubber-stamp review | The owner approves agent PRs without reading them | High | High | Small PRs; QA flags surfaced first; deterministic G1 sample; G4 cooling-off; occasional seeded-defect audits | `quality-assurance` | Median review time under 1 minute on G2+ PRs; seeded defects merged |
| R-048 | Owner overload | Review queue grows beyond what one person can read (see R-002, R-015) | High | High | Batch daily entries into one PR; G1 sampling; monthly throughput limits per workflow; delegated editors for G2 | `chief-librarian` | Open G2-G4 PRs older than 14 days; queue above 20 PRs |
| R-049 | Agent self-approval | An agent approves, merges or waives its own output | Low | High | Agents never approve or merge; separate machine identity; CODEOWNERS; QA tier 1 cannot write | `chief-librarian` | Any approval or merge event from the machine identity |
| R-050 | Methodology drift | Small agent changes slowly alter canon, Quran or note methodology without a G4 decision | Medium | High | `mandatory_review` change classes; methodology files are tier-4 paths; annual audit | `chief-librarian` | Diffs in methodology docs not linked to a `methodology-change` run |

## Strategic Risks

| ID | Risk | Description | L | I | Mitigation | Owner agent | Early-warning signal |
|---|---|---|---|---|---|---|---|
| R-051 | Vendor lock-in | Prompts, tooling or formats tie the library to one model provider | Medium | Medium | Plain-text outputs; provider-neutral registries; skills as documented procedures; deterministic scripts need no model | `chief-librarian` | Provider-specific features in skills without a fallback |
| R-052 | Long-term model change | Over decades models change behaviour, style and calibration, so old and new outputs diverge | High | Medium | Golden sets and rubrics outlive models; re-evaluation on every model change; human-reviewed canonical memory is the reference | `quality-assurance` | Score shift above 0.05 on unchanged golden sets |

## Heat Map

| Likelihood \ Impact | Low | Medium | High |
|---|---|---|---|
| High | | R-027, R-028, R-045, R-052 | R-036, R-047, R-048 |
| Medium | R-033 | R-029, R-030, R-031, R-032, R-035, R-038, R-040, R-044, R-051 | R-026, R-034, R-037, R-039, R-041, R-042, R-050 |
| Low | | | R-043, R-046, R-049 |

The three critical risks (R-036, R-047, R-048) share a cause: the volume
of model output can exceed what human review can verify. The architecture
answers with smaller PRs, citations checked by machine before people,
sampling at G1 and throughput limits.

## Response Playbooks

Playbooks for the critical and the most likely high-impact risks. Each is
a fixed sequence so that the response does not depend on memory.

### Fabricated Citation Found

1. Classify as critical; label the PR `qa-flagged` or revert if merged.
2. Remove the claim or replace the citation with a verified one.
3. Search the same run and the same agent's last 30 days of merged
   outputs for citations to the same source.
4. Add the case to `tests/golden/citation-verification/`.
5. If two incidents occur in one month for one skill, raise that skill's
   G2 outputs to G3 review until the next golden-set pass.

### Review Queue Overload

1. Pause non-essential manual workflows (`book-ingestion`,
   `reading-path-build`, `graph-enrichment`) until the queue is below 10.
2. Keep `daily-cycle` running; it is one PR per day at G1.
3. Close or convert to draft any agent PR older than 30 days.
4. Record the throughput limit that held in project memory and revisit it
   at the monthly review.

### Budget Breach

1. At 80% of the monthly cap, `risk-management` alerts the owner.
2. At 100%, new non-essential runs refuse to start; `daily-cycle` may run
   to 110%.
3. The cost report names the top three spenders by agent and workflow.
4. Corrective action is chosen among: batch more, cache more, downgrade by
   experiment, cut throughput; never by skipping QA.

### Model Deprecation or Price Change

1. Update `last_reviewed` and prices in `models.yaml` on a `docs/*` branch.
2. Run offline evaluation on every skill of the affected class.
3. If regression gates pass, switch the `model_id`; otherwise keep the old
   model until its retirement date and escalate to the owner.
4. Recompute envelope fit with `scripts/cost-report.py` on last month's
   ledger at the new prices.

## Register Entry Format

When a risk here is promoted into [Risk Register](../16-risk-register.md),
it keeps its ID and gains the register's headings. The machine form used
by `risk-management` is:

```yaml
id: R-042
title: Runaway cost
category: Automation
likelihood: Medium
impact: High
priority: High
owner_agent: risk-management
owner_human: Repository Maintainer
signals: [budget alerts at 0.5 and 0.8, escalation_rate > 0.15]
mitigations: [per-run caps, hard stop, escalation reserve]
status: open
last_reviewed: 2026-10-13
```

## Monitoring Cadence

| Cadence | Activity | Workflow step |
|---|---|---|
| Daily | Missing daily PR, budget alerts | `daily-cycle` final step |
| Weekly | Repository health: metadata, links | `weekly-cycle` step 4 |
| Monthly | Cost and risk report; signals above checked | `monthly-cycle` step 5 |
| Quarterly | Review of ratings and mitigations | per [Risk Register](../16-risk-register.md) |
| Annually | Risk register review, merged into docs/16 by G4 PR | `annual-cycle` step 5 |

## Risk Analysis Summary

The architecture adds 27 risks (R-026 to R-052) to the register. Most are
controlled by mechanisms already in the registries: token caps, per-run
and monthly budgets, one record per file, hand-off cards, citation
verification, mandatory review classes and CODEOWNERS. The critical risks
concern human review capacity and fabricated citations, so they are
watched by the most direct signals: PR age, review time, seeded defects
and the claim citation rate.
