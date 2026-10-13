# Model Routing Framework

## Purpose

This document explains how every task in The Bayan Library is assigned a
complexity class, a model, an effort level, a token budget, an execution mode
and a review gate. It is the human-readable companion to the reference router,
`scripts/route-task.py` (shared code in `scripts/bayan/router.py`).

The golden rule governs every decision below: use the smallest model with the
smallest context that can reliably solve the task. Deterministic work runs as
a script and calls no model at all.

Source of truth: `system/registry/routing.yaml` (classes, escalation,
downgrade, budget policy, task matrix) and `system/registry/models.yaml`
(model IDs, effort defaults, prices, token caps). Gates come from
`system/registry/review-gates.yaml`; the generated table lives in
`system/generated/routing-matrix.md`.

Related documents:
[Token Optimization Framework](06-token-optimization-framework.md),
[Cost Governance Framework](14-cost-governance-framework.md),
[Agent Registry](02-agent-registry.md),
[Skill Registry](03-skill-registry.md),
[Human Review Framework](15-human-review-framework.md) and the
[AI Maintainer Operating Manual](../20-ai-maintainer-operating-manual.md).

## Routing Principles

| Principle | Rule |
| --- | --- |
| Classes, not IDs | Agents, skills and tasks name a class (`haiku`, `sonnet`, `opus`); only `models.yaml` holds dated model IDs. |
| Skill model wins | A skill always runs on its own `recommended_model`, whatever the invoking agent's class; a class A agent using a class B skill pays one sonnet call for that step, recorded under the skill's class and not as an escalation. |
| Script first | `execution: script` never calls a model; `hybrid` calls a model only for what the script cannot decide. |
| One rung at a time | Escalation follows `escalation_ladder: [haiku, sonnet, opus]`, never skips a rung, never climbs past opus. |
| Justify every climb | An escalation without a justification record fails the route. |
| Downgrade automatically | Forbidden task types never run on opus; the router downgrades and records it. |
| Compress before climbing | A bigger context window is never a reason to escalate. |
| Batch when nobody waits | Batch-eligible work goes through the Message Batches API at 50% of list price. |
| Gate follows risk | An output starts at its agent's gate and is raised, never lowered, by change classes or a degraded fallback. |

## Complexity Classes

| Class | Name | Model class | Model ID | Effort | Description | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| A | Simple | haiku | `claude-haiku-5-5` | low | Well-specified, single-source, checkable output | metadata fixes, tag generation, link validation, formatting |
| B | Moderate | sonnet | `claude-sonnet-5-5` | medium | Single-work understanding and faithful prose | book summaries, author profiles, study notes |
| C | Complex | sonnet | `claude-sonnet-5-5` | high | Multi-source structure-building; escalate when required | reading paths, theme analysis, concept mapping |
| D | Expert | opus | `claude-opus-5-5` | high | Contested, high-stakes scholarship requiring judgment | canon ranking, Islamic philosophy, comparative theology |
| E | Strategic | opus | `claude-opus-5-5` | xhigh | Decisions that shape the system itself | governance, architecture, methodology |

Per-call token caps come from the model, not the class:

| Model class | Max input tokens | Max output tokens | Input / output USD per MTok |
| --- | --- | --- | --- |
| haiku | 10,000 | 2,000 | 0.10 / 0.50 |
| sonnet | 30,000 | 5,000 | 2.00 / 10.00 |
| opus | 100,000 | 10,000 | 4.00 / 20.00 |

An agent or skill may declare a smaller `token_budget` than its model cap
(for example `daily-word` at 5,000 / 800). The router checks the model cap;
the context assembler then fills only the smaller budget.
`scripts/validate-registry.py` rejects any budget above the model cap.

## Routing Matrix

Every task type in `routing.yaml`. Script tasks show no model because none is
called. "Forbidden on opus" marks types the downgrade rule protects.

| Task type | Class | Model ID | Effort | Input / output cap | Execution | Batch eligible | Forbidden on opus |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `link_validation` | A | none (script) | - | 0 / 0 | script | no | yes |
| `metadata_cleanup` | A | `claude-haiku-5-5` | low | 10,000 / 2,000 | hybrid | yes | yes |
| `metadata_validation` | A | none (script) | - | 0 / 0 | script | no | no |
| `tagging` | A | `claude-haiku-5-5` | low | 10,000 / 2,000 | model | yes | yes |
| `formatting` | A | `claude-haiku-5-5` | low | 10,000 / 2,000 | hybrid | no | yes |
| `index_build` | A | none (script) | - | 0 / 0 | script | no | yes |
| `duplicate_detection` | A | `claude-haiku-5-5` | low | 10,000 / 2,000 | hybrid | no | no |
| `daily_selection` | A | `claude-haiku-5-5` | low | 10,000 / 2,000 | hybrid | no | yes |
| `spaced_repetition_scheduling` | A | none (script) | - | 0 / 0 | script | no | yes |
| `knowledge_compression` | A | `claude-haiku-5-5` | low | 10,000 / 2,000 | model | yes | no |
| `difficulty_assessment` | A | `claude-haiku-5-5` | low | 10,000 / 2,000 | model | yes | no |
| `terminology_glossing` | A | `claude-haiku-5-5` | low | 10,000 / 2,000 | model | no | no |
| `repetitive_operation` | A | `claude-haiku-5-5` | low | 10,000 / 2,000 | hybrid | no | yes |
| `cost_reporting` | A | none (script) | - | 0 / 0 | script | no | no |
| `book_summary` | B | `claude-sonnet-5-5` | medium | 30,000 / 5,000 | model | no | no |
| `author_profile` | B | `claude-sonnet-5-5` | medium | 30,000 / 5,000 | model | no | no |
| `study_note` | B | `claude-sonnet-5-5` | medium | 30,000 / 5,000 | model | no | no |
| `concept_explanation` | B | `claude-sonnet-5-5` | medium | 30,000 / 5,000 | model | no | no |
| `poetry_analysis` | B | `claude-sonnet-5-5` | medium | 30,000 / 5,000 | model | no | no |
| `vocabulary_analysis` | B | `claude-sonnet-5-5` | medium | 30,000 / 5,000 | model | yes | no |
| `language_simplification` | B | `claude-sonnet-5-5` | medium | 30,000 / 5,000 | model | no | no |
| `daily_entry` | B | `claude-sonnet-5-5` | medium | 30,000 / 5,000 | model | yes | no |
| `citation_verification` | B | `claude-sonnet-5-5` | medium | 30,000 / 5,000 | hybrid | no | no |
| `arabic_root_analysis` | B | `claude-sonnet-5-5` | medium | 30,000 / 5,000 | model | no | no |
| `reflection_prompt` | B | `claude-sonnet-5-5` | medium | 30,000 / 5,000 | model | no | no |
| `qa_review` | B | `claude-sonnet-5-5` | medium | 30,000 / 5,000 | hybrid | no | no |
| `reading_path` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | model | no | no |
| `theme_analysis` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | model | no | no |
| `concept_mapping` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | model | no | no |
| `knowledge_graph_proposal` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | model | no | no |
| `influence_analysis` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | model | no | no |
| `comparative_analysis` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | model | no | no |
| `research_synthesis` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | model | no | no |
| `wisdom_extraction` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | model | no | no |
| `author_decoding` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | model | no | no |
| `quran_theme_mapping` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | model | no | no |
| `translation_comparison` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | model | no | no |
| `representation_check` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | hybrid | no | no |
| `risk_assessment` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | model | no | no |
| `schema_migration` | C | `claude-sonnet-5-5` | high | 30,000 / 5,000 | hybrid | no | no |
| `canon_ranking` | D | `claude-opus-5-5` | high | 100,000 / 10,000 | model | no | no |
| `bias_audit` | D | `claude-opus-5-5` | high | 100,000 / 10,000 | model | no | no |
| `islamic_philosophy` | D | `claude-opus-5-5` | high | 100,000 / 10,000 | model | no | no |
| `comparative_theology` | D | `claude-opus-5-5` | high | 100,000 / 10,000 | model | no | no |
| `tafsir_comparison` | D | `claude-opus-5-5` | high | 100,000 / 10,000 | model | no | no |
| `civilizational_analysis` | D | `claude-opus-5-5` | high | 100,000 / 10,000 | model | no | no |
| `governance` | E | `claude-opus-5-5` | xhigh | 100,000 / 10,000 | model | no | no |
| `architecture` | E | `claude-opus-5-5` | xhigh | 100,000 / 10,000 | model | no | no |
| `methodology_design` | E | `claude-opus-5-5` | xhigh | 100,000 / 10,000 | model | no | no |

Totals: 49 task types (14 A, 12 B, 14 C, 6 D, 3 E); 5 script-only,
9 hybrid, 35 model.

## Escalation Rules

A task spec may carry routing signals. The router compares them with the
triggers of the rung the task currently sits on. A trigger that fires moves
the task exactly one rung up and produces a justification record.

| From | To | Signal | Condition | Reason recorded |
| --- | --- | --- | --- | --- |
| haiku | sonnet | `source_count` | greater than 3 | More than 3 sources |
| haiku | sonnet | `comparative` | true | Comparative reasoning |
| haiku | sonnet | `multi_document_synthesis` | true | Multi-document synthesis |
| haiku | sonnet | `qa_failures` | 2 or more at haiku | Output failed QA twice at this tier |
| sonnet | opus | `canon_decision` | true | Canon decision |
| sonnet | opus | `methodology_design` | true | Methodology design |
| sonnet | opus | `cross_civilizational` | true | Cross-civilizational analysis |
| sonnet | opus | `strategic_planning` | true | Strategic planning |
| sonnet | opus | `qa_failures` | 2 or more at sonnet | Output failed QA twice at this tier |

Escalation constraints:

- After a climb the router resets `qa_failures` to 0, because the failures
  were counted at the previous rung; QA history alone never climbs two
  rungs in one decision. A task can still climb twice when a different
  trigger fires on each rung (for example `comparative` and then
  `canon_decision`), with a justification for each.
- A forbidden-on-opus task type may climb from haiku to sonnet but never to
  opus; its ceiling is sonnet.
- Escalated calls are charged to the `escalation-reserve` envelope (see
  [Cost Governance Framework](14-cost-governance-framework.md)). When the
  reserve is spent, further escalations that month need owner approval.
- Effort stays the class effort after a climb (the class describes the
  task, not the model); after a downgrade it becomes the new model's
  `default_effort` in `models.yaml`.

### Justification Record

Every climb writes one record into the step file of the run log,
`.bayan/runs/<run_id>/steps/NN.yaml`, and sets `escalated: true` on the
matching ledger line. A route without this record is rejected.

```yaml
route:
  task: comparative_analysis
  agent: canon-editor
  class: C
  default_model: sonnet
  final_model: opus
  model_id: claude-opus-5-5
  effort: high
  escalations:
    - from: sonnet
      to: opus
      signal: canon_decision
      value: true
      reason: Canon decision.
      evidence: >-
        Output feeds the Top 100 draft ranking in canon-revision step 5;
        candidates span three civilizations.
      expected_cost_usd: 0.22    # 30K in x 4.00 + 5K out x 20.00
      charged_to: escalation-reserve
      approved_by: router        # owner when the reserve is exhausted
  downgrades: []
  budget: {input: 30000, output: 5000}
  budget_justification: null
  review_gate: G4
  batch: false
```

## Downgrade Rules

Opus is never used for the following task types. The model comes from the
task's class, never from the calling agent's default, so an opus agent such
as `canon-editor` still gets haiku for tagging. Should a forbidden task ever
resolve to opus (for example after a registry edit), the router rewrites the
model to haiku (`downgrade_to: haiku`) and records the downgrade in the
decision's `downgrades` list.

| Forbidden on opus | Why it never needs opus |
| --- | --- |
| `link_validation` | Deterministic; a script decides |
| `tagging` | Controlled vocabulary, checkable output |
| `formatting` | Mechanical; markdownlint is the judge |
| `metadata_cleanup` | Schema-checked by `scripts/validate-metadata.py` |
| `repetitive_operation` | Same operation many times; cost scales linearly |
| `index_build` | Generated by `scripts/build-index.py` |
| `daily_selection` | Selection from history and calendar |
| `spaced_repetition_scheduling` | Deterministic scheduling algorithm |

The downgrade is applied before escalation and caps it: a forbidden task that
fires a haiku-to-sonnet trigger lands on sonnet and stops there.
`scripts/validate-registry.py` also refuses any registry entry that assigns
opus to these task types, so the runtime downgrade is a second line of
defence.

## Fallback Behaviour

| Situation | Action | Result marking | Gate effect |
| --- | --- | --- | --- |
| Model unavailable (outage, rate limit after retries) | Use the agent's `fallback_model` when it is available, one rung away and under the task's ceiling; otherwise the nearest available rung above, then below. The `forbidden_on_opus` ceiling still holds, so an outage never puts forbidden work on opus. An upward fallback is recorded as an escalation | `degraded: true` when the fallback is lower | Gate raised one level (max G4) when degraded |
| Fallback is lower than the default (opus to sonnet) | Run, but the output cannot merge until rerun on the default model or waived by the owner | `degraded: true`, `rerun_required: true` | G4 outputs stay blocked until rerun or waiver |
| Model refusal | Log the refusal; retry once on the same model with a clarified spec; never route around a refusal by switching model | `refused: true` | Second refusal goes to the owner as a finding |
| QA failure (first) | Retry once at the same tier with the QA findings in the Local context layer | `attempts: 2` | Unchanged |
| QA failure (second at a tier) | `qa_failures >= 2` trigger escalates one rung with justification | `escalated: true` | Unchanged |
| QA failure (second at opus) | Stop; return the packet to the owner | `failed` | Human decision |
| Budget overflow after compression and split | Require `budget_justification`; otherwise stop | `budget_overrun: true` | Unchanged |

Gate raise order: G0, G1, G2, G3, G4. A degraded G1 daily entry becomes G2
(every item read); a degraded G3 commentary becomes G4.

## Routing Algorithm

The pseudocode mirrors `route()` in `scripts/bayan/router.py`, called by
`scripts/route-task.py`. Input is a task spec; output is a route decision
written to the step file. Status is `ok`, `needs_justification` (an
escalation fired but the spec has no `justification`) or `blocked`.

```text
function route(spec):
    # spec: task, agent, signals, justification, input_tokens,
    #       output_tokens, incompressible, budget_justification,
    #       failed_models, interactive, change_classes
    tt  = routing.task_types[spec.task]   # unknown -> RoutingError
    cls = routing.classes[tt.class]
    d   = Decision(model=cls.model, effort=cls.effort, status="ok")

    # 1. Script short-circuit
    if tt.execution == "script":
        d.model = none; d.effort = none
        d.gate = gate(spec, default="G0")
        return d

    # 2. Forbidden-on-opus downgrade (sets the ceiling)
    ceiling = "opus"
    if spec.task in forbidden_on_opus:
        ceiling = "sonnet"
        if d.model == "opus":
            d.model = downgrade_to                    # haiku
            d.downgrades.append("forbidden on opus")

    # 3. Escalation, one rung per pass
    loop:
        rule = escalation_rule(from=d.model)          # none at opus
        if rule is none or rung(rule.to) > rung(ceiling): break
        fired = [t for t in rule.triggers if t matches spec.signals]
        if fired is empty: break
        d.escalations.append({from, to: rule.to, reasons: fired})
        d.model = rule.to
        signals.qa_failures = 0          # counted at the previous rung
        if spec.justification is missing:
            d.status = "needs_justification"

    # 4. Fallback when the chosen model failed or is unavailable
    if d.model in spec.failed_models:
        available = models <= ceiling that have not failed
        fb = agent.fallback_model if it is available and one rung away,
             else the nearest available rung above, else the nearest below
        if fb is none: d.status = "blocked"; return d
        if rung(fb) < rung(d.model): d.degraded = true
        else: d.escalations.append({from, to: fb, reasons: ["fallback"]})
        d.model = fb

    # 5. Model ID, caps and effort from models.yaml
    d.model_id = models[d.model].model_id
    d.budget   = models[d.model].budget             # input, output
    if d.downgrades: d.effort = models[d.model].default_effort

    # 6. Budget policy: compress, then split, then justify
    if spec.input_tokens > d.budget.input:
        if not spec.incompressible: action "compress_context"
        elif spec.budget_justification: action "accepted with justification"
        else: action "split_task or justify"; d.status = "blocked"
    if spec.output_tokens > d.budget.output:
        if spec.budget_justification: action "accepted with justification"
        else: action "split_task"

    # 7. Batch, gate and cost
    d.batch = spec.task in batch_eligible and not spec.interactive
    g = gate(spec, default = "G1" if d.model == "haiku" else "G2")
    d.gate = raise_one(g) if d.degraded else g      # capped at G4
    d.estimated_cost_usd = estimate_cost(d.model, tokens, d.batch)
    return d

function gate(spec, default):
    g = agents[spec.agent].quality.review_gate if spec.agent else default
    for c in spec.change_classes:
        g = stricter(g, permissions.mandatory_review[c])
    return g
```

The router decides the gate of the individual output. When the outputs of a
workflow are bundled into one PR, the PR takes the strictest of the step
gates and the workflow's own `review_gate`, and CODEOWNERS adds owner
approval for G4 paths (see
[Human Review Framework](15-human-review-framework.md)).
The per-agent and per-skill `token_budget` (smaller than the model cap) is
applied when the context is assembled by `scripts/build-context.py`.

## Worked Examples

| # | Request | Route decision | Why |
| --- | --- | --- | --- |
| 1 | `quality-assurance` runs `link_validation` in the weekly cycle | Script; no model; cost 0; gate G0 (agent gate) | Script short-circuit |
| 2 | `canon-editor` (default opus) runs `tagging` on 40 candidates | The task class, not the agent default, picks the model: `claude-haiku-5-5`, low; ceiling sonnet; batch; gate G4 (canon-editor agent gate) | Forbidden on opus; batch eligible |
| 3 | `study-notes` runs `knowledge_compression` with `multi_document_synthesis: true` (three notes merged) | haiku to sonnet with justification; effort stays low (class A); charged to escalation reserve; still batch; gate G2 | One haiku trigger fired |
| 4 | `canon-editor` runs `comparative_analysis` inside `canon-revision` with `canon_decision: true` | sonnet to opus with justification; effort high; gate G4 | Sonnet trigger fired |
| 5 | `study-notes` runs `book_summary` for a work whose full text is 120,000 tokens | sonnet stays; input over 30,000, so compress (ladder) then split into chapter chunks; no escalation | Never escalate for window size |
| 6 | `difficulty-assessor` output fails QA twice on haiku | haiku to sonnet (`qa_failures: 2`); the count resets after the climb, so it stops at sonnet; gate G1 | QA trigger |
| 7 | `quran-traditional-study` runs `tafsir_comparison` with `failed_models: [opus]` | Fallback sonnet; `degraded: true`; G3 raised to G4; rerun or owner waiver before merge | Fallback rule |
| 8 | `metadata` runs `metadata_cleanup` with `source_count: 5` | haiku to sonnet allowed; ceiling sonnet even if a sonnet trigger fires | Forbidden types cap at sonnet |

Example 5 in route-decision form:

```yaml
route:
  task: book_summary
  agent: study-notes
  class: B
  final_model: sonnet
  model_id: claude-sonnet-5-5
  effort: medium
  budget: {input: 30000, output: 5000}
  overflow_actions: [compress_context, split_task]
  split: {unit: chapter, chunks: 15, chunk_task: knowledge_compression}
  escalations: []
  review_gate: G2
  batch: false
```

## Changing a Model Generation

Model generations change; registry entries do not. To adopt a new
generation:

1. Edit only `system/registry/models.yaml`: `model_id`, `display_name`,
   `pricing`, `context_window`, `max_output_tokens` and, if justified,
   `budget` and `last_reviewed`.
2. Run `scripts/validate-registry.py` (budgets within caps, opus rules,
   envelopes) and `scripts/generate-registry-docs.py` to refresh
   `system/generated/routing-matrix.md`.
3. Run the golden-set evaluation on the new model for each class it serves
   ([Evaluation Framework](13-evaluation-framework.md)); compare accept
   rate, rubric score and tokens per artifact against the last month.
4. Re-run the cost estimate in
   [Cost Governance Framework](14-cost-governance-framework.md) with the new
   prices.
5. Open a PR on an `automation/*` branch. `system/**` is a CODEOWNERS path,
   so the change is G4: owner approval, rationale, 72-hour cooling-off.

No agent, skill, workflow or routing entry changes, because they all name
classes. If a new tier of model appears (a class between two rungs), that is
an architecture change to `escalation_ladder` and `routing.yaml`, not a model
swap.

## Model Routing Summary

Routing turns a task type into a class, a class into a model through
`models.yaml`, and then adjusts in a fixed order: scripts short-circuit,
forbidden types downgrade, escalation climbs one justified rung at a time,
budgets are met by compression and splitting rather than larger models, and
the strictest applicable gate is chosen, raised when a result is degraded.
Every decision is recorded in the run log and the usage ledger so that the
monthly cost report can audit it.
