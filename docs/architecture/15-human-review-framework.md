# Human Review Framework

## Purpose

This document defines how humans review what agents produce: the five
review gates, who reviews at each, what they check, how the Chief
Librarian Agent prepares decisions for the owner, and how review is kept
light enough for one person to sustain for decades.

Source of truth: `system/registry/review-gates.yaml` (gates G0-G4) and the
`mandatory_review` section of `system/registry/permissions.yaml`. Review
volume is derived from `system/registry/workflows.yaml`. Gate assignment
per agent is in the [Agent Registry](02-agent-registry.md); enforcement is
in the [Permission Model](04-permission-model.md).

## Principles

- **Nothing merges without a human.** Even G0 changes are merged by a
  person; only content review is skipped.
- **Review where judgment matters.** Deterministic checks belong to CI
  ([Quality Assurance Framework](12-quality-assurance-framework.md)); human
  attention is spent on meaning, fairness and truth.
- **Strictest gate wins.** An item starts at its producing agent's gate
  and is raised, never lowered, by its change classes or a degraded
  fallback; a PR's gate is the strictest of its items, with the workflow's
  `review_gate` as the minimum. CODEOWNERS adds owner approval on protected
  paths.
- **The PR is the record.** Every decision, with its reasons, lives on the
  pull request.
- **Sustainable load.** Agent throughput is limited by review capacity,
  not the other way round.

## Gates

| Gate | Name | Human review | Sample rate | Min QA score | Citations | Rationale | Cooling-off | Reviewer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G0 | Automated checks | none | 0.0 | none | no | no | none | Merger only (owner or delegated editor) |
| G1 | Sampled review | sampled | 0.2 | 0.85 | no | no | none | Owner or delegated editor |
| G2 | Editorial review | every item | 1.0 | 0.80 | no | no | none | Owner or delegated editor |
| G3 | Scholarly review | every item with sources open | 1.0 | 0.85 | required | no | none | Owner or delegated scholarly reviewer |
| G4 | Chief Librarian approval | owner approval via CODEOWNERS | 1.0 | 0.90 | required | required | 72 hours | Owner only |

G1 requires a higher QA score than G2 because at G1 the QA score is the
only check on the 80 percent of items no human reads; at G2 a human reads
everything.

### G0 Automated Checks

Applies to reports, regenerated indexes and formatting-only changes. All
`validate.yml` jobs must pass. The merger confirms the diff is what the
label claims (for example, that a "formatting only" PR changes no words).

### G1 Sampled Review

Applies to metadata updates, tags, daily entries and index rebuilds.
`quality-assurance` scores every item. The reviewer reads:

- a random 20 percent of items, drawn with the run ID as seed so the
  sample is reproducible;
- every item scoring below 0.85;
- every item labelled `qa-flagged`.

If any sampled item fails review, the reviewer reads the whole PR.

### G2 Editorial Review

Applies to summaries, notes, author and poet profiles and primers. Every
item is read before merge. The reviewer may edit in place; edits are
recorded as review commits so the agent's original is preserved in history.

### G3 Scholarly Review

Applies to religious interpretation, historical claims and comparative
theology. Every item is read with its cited sources open. Claims without a
citation are removed or rewritten as questions. Interpretation must be
labelled as interpretation, and where scholars disagree the competing views
must appear.

### G4 Chief Librarian Approval

Applies to canon, ranking, governance, Quran methodology and architecture
changes. The owner approves via CODEOWNERS after reading the approval
packet. The PR may not merge until 72 hours after the packet is posted,
even if approved earlier; the `cooling-off` label is removed by the owner.

## Mandatory Review

Four change classes always require G4 and two always require G3, whoever
proposes them and whatever files they touch.

| Change class | Gate | Why it is mandatory | Extra requirements |
| --- | --- | --- | --- |
| `canon_change` | G4 | Canons shape everything the reader meets first | Bias audit, representation check, changelog entry |
| `ranking_change` | G4 | Rank movement signals value judgments | Per-criterion scores; memo for any move above 10 places |
| `governance_change` | G4 | Changes who decides what | Risk register consulted, options compared |
| `quran_methodology_change` | G4 | Affects how scripture is approached for life | Traditional grounding preserved; scholarly sources cited |
| `architecture_change` | G4 | Changes how the system behaves | Migration and rollback plan |
| `religious_interpretation` | G3 | Interpretation must not pass as fact | Labelled, cited, competing views shown |
| `historical_claim` | G3 | Errors compound through the graph | Primary or credible secondary source |

Ranking changes and canon changes usually travel together in the
`canon-revision` workflow; the PR then carries both classes. Quran
methodology changes come from `quran-learning` or the `methodology-change`
workflow and are always G4, while ordinary Quran track notes are G3.

## Reviewer Checklists

### Checklist by Gate

```text
Every gate
[ ] All required CI checks green
[ ] AI Provenance complete: agent_id, workflow_id, run_id, model,
    permission_tier, tokens, estimated cost, escalations
[ ] Gate label is the strictest the change demands
[ ] Changed paths fit the agent's tier (`agent permissions` check green)

G1 adds
[ ] Sample drawn and every flagged item read
[ ] Sampled items match templates and controlled vocabularies

G2 adds
[ ] Every item read in full
[ ] Faithful to the source; no invented claims
[ ] Terms glossed; links resolve to the right records

G3 adds
[ ] Every claim checked against its cited source
[ ] Facts, interpretations and debates labelled as such
[ ] Competing schools or views represented where they exist

G4 adds
[ ] Approval packet read in full, including options and dissent
[ ] Rationale, bias audit and risk notes present
[ ] QA score >= 0.90; packet not marked degraded (or waived)
[ ] 72-hour cooling-off elapsed before merge
```

### Checklist by Content Type

| Content type | Typical gate | Reviewer checks |
| --- | --- | --- |
| Summaries (one-line, executive, chapter) | G2 | Matches the book's actual argument; no claims beyond the source; page or section citations; compression levels agree with each other; tags from `metadata/tags.yaml`; difficulty plausible |
| Religious interpretation | G3 | Commentators named and dated; at least three commentaries where the passage is debated and more than one school when they differ; no forced or scientific over-reading; no normative ruling presented; interpretation labelled; tone respectful and non-sectarian |
| Historical claims | G3 | Dates and attributions sourced; uncertainty stated; no anachronism; transmissions between civilizations evidenced rather than assumed |
| Canon and ranking | G4 | Weights sum to 100; every item scored on every criterion; bias audit attached and no unresolved high-severity finding; representation balance index at least 0.7; ranking volatility within 5 percent per annual review; each move explained |
| Graph edges | G2 (G3 if contradicting a high-evidence edge) | Relationship type fits the signature in `knowledge-graph.yaml`; evidence level honest; citation present for high and moderate; no duplicate or self loop; tentative links labelled for readers |

## Approval Packet

For every G4 change, `chief-librarian` prepares an approval packet using
the `governance-review` skill and posts it as the first PR comment. A
packet missing any section is returned to the proposing agent with the gaps
listed, and does not reach the owner.

```text
APPROVAL PACKET  <PR number>  <date>
Change classes:  canon_change, ranking_change
Proposed by:     canon-editor (tier 4)    Run: <run_id>
Model:           opus / claude-opus-5-5   Degraded: no
QA score:        0.93 (min 0.90)          Cost: USD <n.nn>

1. Decision requested     one sentence
2. Summary of change      what moves, what is added or removed
3. Rationale              why, with sources
4. Options considered     at least two, including "no change"
5. Recommendation         and the reason it beats the alternatives
6. Evidence               dossiers, citations, representation report
7. Bias audit             findings by severity and how each is handled
8. Risks                  register entries consulted, new risks
9. Dissent                agent disagreements and how they were weighed
10. Rollback              how to revert, and what else would change
11. Cooling-off           posted <timestamp>; earliest merge <timestamp>
```

If the packet was produced on the fallback model, it is labelled
`degraded` and blocks merge until it is rerun on opus or the owner waives
the block in writing.

## Review Service Levels

| Gate | First response | Decision | When missed |
| --- | --- | --- | --- |
| G0 | none | within 7 days | PR stays open; drift checks keep it honest |
| G1 | none | within 2 days | Next bundle still opens; stale bundles merged together |
| G2 | within 7 days | within 14 days | Workflow backpressure (below) |
| G3 | within 7 days | within 30 days | Item stays in `drafts/`; not visible to readers |
| G4 | packet read within 7 days | after 72 h, within 30 days | Closed with reason; may be reopened with new evidence |

A PR left without decision past its window is closed by the owner with a
one-line reason, never merged by default.

## Sustainable Review Load

The owner is one person. Review capacity is therefore the system's real
throughput limit, and the planning target is about four hours a week.

### Weekly Estimate

Planning estimates derived from `workflows.yaml`. Volumes for manual
workflows are assumptions to revisit at each quarterly review.

| Workflow | Gate | Assumed volume | Minutes per item | Minutes per week |
| --- | --- | --- | --- | --- |
| `daily-cycle` | G1 | 7 bundles of 8 entries; 20 percent sampled plus flags | 4 per bundle | 28 |
| `weekly-cycle` | G1 (notes G2) | 1 run; health report and inbox notes | 15 | 15 |
| `monthly-cycle` | G2 | 1 per month: gap, graph, cost and risk reports | 60 | 15 |
| `annual-cycle` | G4 | 1 per year: canon audit, paths, system review | 360 | 7 |
| `book-ingestion` | G2 | 3 books (summaries and concept notes) | 25 | 75 |
| `graph-enrichment` | G2 | about 20 edges, reviewed in one batch | 1 | 20 |
| `quran-study-session` | G3 | 2 sessions | 15 | 30 |
| `reading-path-build` | G4 | 1 per month | 45 | 10 |
| `canon-revision` | G4 | 2 per year | 240 | 10 |
| `methodology-change` | G4 | 2 per year | 120 | 5 |
| Total | | | | about 215 |

The largest and most elastic line is `book-ingestion`. The cost budget in
`budgets.yaml` is sized for roughly 100 summaries a month, but at G2 that
would need about eight hours of review a week. The review budget, not the
cost budget, therefore sets ingestion pace: about three books a week, more
only when the owner chooses to read more.

### Batching

| Session | Cadence | Length | Content |
| --- | --- | --- | --- |
| Daily glance | daily | 5-10 min | Today's `daily-cycle` bundle (G1) |
| Editorial session | weekly | 90-120 min | All open G2 items grouped by book, then graph edges, then the weekly cycle |
| Scholarly session | weekly or with Quran study | 30-45 min | G3 items with sources open; doubles as the owner's own study |
| Decision session | monthly | 60 min | G4 packets past cooling-off, monthly reports |

Grouping by book means the owner reads a book's summary, notes and graph
edges together, once.

### Backpressure

To keep the queue bounded, the orchestrator does not start a new run of a
G2, G3 or G4 workflow while that workflow already has more open PRs than
the owner's configured limit (recommended: 10 for G2, 5 for G3, 3 for G4).
The skipped run is logged, not lost.

## Feedback into Evaluation

Each review outcome is recorded on the PR and in the usage ledger
(`accepted` field), and feeds the
[Evaluation Framework](13-evaluation-framework.md).

| Outcome | Recorded as | Feeds |
| --- | --- | --- |
| Approved as is | `accepted: true` | `owner_acceptance_rate`, `cost_per_accepted_artifact` |
| Approved with reviewer edits | `accepted: true`, edit size noted | Fidelity and rubric drift for the agent |
| Changes requested | `accepted: false` until rerun | `rework_rate`; repeated failures trigger escalation |
| Rejected | `accepted: false` | Becomes an evaluation case for the agent |
| Sampled item fails at G1 | QA miss | `escaped_defect_rate`; QA recalibration |
| QA score disagrees with human | Disagreement logged | `agreement_with_human_reviewers` (target 0.85) |

Rejected and corrected items join the golden set that `quality-assurance`
is calibrated against each month in `monthly-cycle`. An agent whose
acceptance rate falls for two consecutive months is reviewed by
`chief-librarian`, which may propose a prompt, skill, class or gate change
through a G4 registry PR.

## Disagreement and Appeal

| Disagreement | Resolution |
| --- | --- |
| Agent versus agent (for example research versus canon-editor) | `chief-librarian` arbitrates and records both positions in the packet's Dissent section |
| QA agent versus producing agent | Escalates to the human reviewer; the QA score stands until a human overrides it on the PR |
| Reviewer versus agent output | The reviewer decides; the agent may add one evidence-backed reply on the PR |
| Delegated reviewer versus owner | The owner decides |
| Owner wishes to revisit a decision | New PR referencing the old one with new evidence; G4 cooling-off restarts |

Disputes follow the steps of the [Governance Model](../02-governance-model.md):
clarify, review evidence, compare sources, document alternatives, decide.
The aim is better understanding, and alternative views remain recorded
even when they lose.

## Audit Trail

The pull request is the record. Run logs in `.bayan/runs/` are deleted
after 30 days, so everything needed to understand a decision must be on
the PR.

| Question | Where the answer lives |
| --- | --- |
| Who produced it, on which model, at what cost | AI provenance block; commit trailers `Bayan-Run`, `Bayan-Agent`, `Bayan-Model` |
| Which gate applied and why | `gate:Gn` label and change classes in the PR body |
| How it scored | QA report comment from `quality-assurance` |
| Who reviewed and what they said | GitHub review and comments |
| Why a G4 change was approved | Approval packet comment and owner approval |
| What was spent | Usage ledger and `system/reports/cost/YYYY-MM.md` |
| What the project decided over time | `system/memory/projects/<id>.md` decision section |

Merge commits are squashed with the PR number in the subject, so
`git log` leads straight back to the full record.

## Human Review Framework Summary

Five gates match human attention to risk: none for automated changes, a
sample for routine ones, every item for editorial content, sources open
for scholarship, and owner approval with a 72-hour cooling-off for canon,
ranking, governance, Quran methodology and architecture. The Chief
Librarian Agent prepares complete packets so the owner decides rather than
investigates, batching and backpressure keep the load near four hours a
week, and every decision is preserved on its pull request.
