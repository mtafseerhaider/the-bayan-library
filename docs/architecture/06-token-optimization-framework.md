# Token Optimization Framework

## Purpose

This document defines how agents in The Bayan Library assemble the smallest
context that can reliably solve a task, how that context is retrieved,
prioritized, compressed and cached, and how token budgets are enforced. It
explains the reference context assembler, `scripts/build-context.py` (shared
code in `scripts/bayan/retrieval.py` and `scripts/bayan/index.py`).

At the target scale (10,000+ books, 100,000+ notes, 20,000+ concepts) no
agent can read the repository. Agents read index cards and climb a retrieval
ladder only as far as the task requires.

Source of truth: `system/registry/models.yaml` (per-model token caps and
prices), `system/registry/routing.yaml` (`budget_policy`),
`system/registry/memory.yaml` (layer token limits) and
`system/registry/skills.yaml` (per-skill token budgets).

Related documents: [Model Routing Framework](05-model-routing-framework.md),
[Memory Architecture](07-memory-architecture.md),
[Knowledge Graph Architecture](08-knowledge-graph-architecture.md),
[Cost Governance Framework](14-cost-governance-framework.md) and the
[Metadata Schema](../07-metadata-schema.md).

## Techniques

| Technique | What it does | Where it is implemented |
| --- | --- | --- |
| Context minimization | Load only the minimum context layer the task needs | `build-context.py` layer selection |
| Progressive retrieval | Climb Metadata, Summary, Executive Summary, Full Content; stop when sufficient | Retrieval ladder |
| Hierarchical retrieval | Index shard, then record card, then section, then chunk | `metadata/index/<type>.jsonl`, chunk cards |
| Context compression | Shrink an over-budget pack while preserving must-keep claims | `context-compression` skill (haiku) |
| Semantic caching | Reuse prior outputs for the same normalized task and unchanged records | Run cache keyed by content hashes |
| Summary memory | Hand-off cards and project memory replace transcripts | [Memory Architecture](07-memory-architecture.md) |
| Chunking | Split long works by chapter or section with overlap | Chunk rules below |
| Relevance filtering | Drop candidates below a score threshold before any model sees them | Prioritization algorithm |

## Context Layers

A model call is assembled from five layers, ordered from most stable to most
volatile so that the stable prefix is cacheable. The rule is: load only the
minimum necessary layer.

| Layer | Contains | Token target | Loaded when |
| --- | --- | --- | --- |
| 1 Global | System prompt: charter principles excerpt, style rules, the agent's registry card, the skill contract and output schema | <= 1,500 | Always; first in the prompt; cached |
| 2 Repository | Registry excerpts the task needs (gate, vocabulary, relationship signatures) and filtered index cards | <= 4,000 (memory.yaml `repository`) | Only when the task must locate, resolve or validate IDs |
| 3 Project | `system/memory/projects/<id>.md` | <= 1,500 (memory.yaml `project`) | Only when the run belongs to a project |
| 4 Document | Retrieval-ladder material for the target records | Remainder of the budget | When the task reads content |
| 5 Local | Task spec, newest hand-off cards, QA findings for a retry, the chunk being worked | <= 2,000 plus the chunk | Always; last in the prompt |

Layer budget for a call, with a safety margin of 5% of the cap:

```text
document_budget = cap.input - global - repository - project - local
                  - safety_margin
```

For a haiku call (10,000 cap) that leaves roughly 5,000 to 6,000 tokens of
document context; for sonnet about 25,000; for opus about 90,000.

## Retrieval Ladder

| Rung | Artifact | Size target | Source | Typical use |
| --- | --- | --- | --- | --- |
| 0 Metadata | Index card: id, type, title, 1-line summary, tags, civilization, path, token estimates | <= 80 tokens | `metadata/index/<type>.jsonl` | Selection, tagging, linking, daily choice |
| 1 Summary | Record summary | <= 120 words (about 160 tokens) | Record front matter or summary file | Comparison lists, reading paths |
| 2 Executive Summary | Structured overview: argument, structure, key concepts, significance | <= 600 words (about 800 tokens) | Summary file | Notes, profiles, analysis |
| 3 Full Content | Text in chunks with chunk cards | Chunks of <= 8,000 tokens | Source file, chunk cards | Summarization, citation checks, close reading |

Each index card carries `tokens: {card, summary, executive, full}` so that
the assembler can plan a pack without opening files. Canonical records must
carry rungs 1 and 2 (see [Memory Architecture](07-memory-architecture.md)),
so rung 3 is rarely needed outside ingestion.

## Retrieval Algorithm

```text
function retrieve(task, budget):
    # 1. Candidate generation from index shards (no file reads)
    shards = index_shards_for(task.target_types)   # e.g. books, concepts
    C = {}
    C += exact_ids(task.target_ids)                # always included
    C += filter(shards, type in task.types,
                tags & task.tags, civilization in task.civs,
                period overlaps task.period)
    if task.seed_ids:
        C += graph_neighbourhood(task.seed_ids, map=task.map_id,
                                 depth <= 2, degree_cap = 50)
    C = dedupe(C)

    # 2. Score and filter
    for c in C: c.score = relevance(c, task)        # see below
    C = [c for c in C if c.score >= 0.35 or c.id in task.target_ids]

    # 3. Prioritize under budget (next section) and climb the ladder
    pack = prioritize(C, budget.document)
    return pack                                      # with token counts

function relevance(c, task):
    tag   = jaccard(c.tags, task.tags)
    text  = lexical_overlap(c.summary, task.query)   # BM25 on cards
    graph = 1 / (1 + hops(c, task.seed_ids))         # 1, 0.5, 0.33
    exact = 1 if c.id in task.target_ids else 0
    return max(exact, 0.4*tag + 0.35*text + 0.25*graph)
```

## Prioritization Algorithm

Priority balances what a record is worth against what it costs to load.

```text
value(c)    = relevance(c) * authority(c) * recency(c)
priority(c) = value(c) / cost(c, rung)

authority:  canonical (G3/G4 reviewed) 1.0 | G2 reviewed 0.85
            G1 sampled 0.7 | draft 0.4 | tentative edge 0.5
recency:    1.0 for library content (timeless)
            0.5 ^ (age_days / 30) for session and project memory items
cost:       c.tokens[rung]  from the index card

function prioritize(C, B):
    pack = []; used = 0
    # pass 1: every candidate at rung 0 (cards) in priority order
    for c in sort(C, by=priority(c, rung=0), desc):
        if used + c.tokens.card > B: break
        pack.add(c, rung=0); used += c.tokens.card
    # pass 2: upgrade the best items one rung at a time
    while True:
        best = argmax over c in pack with next_rung(c) <= task.max_rung
               of value(c) / delta_cost(c)
        if best is none or used + delta_cost(best) > B: break
        upgrade(best); used += delta_cost(best)
    return pack
```

`task.max_rung` comes from the skill: tagging and daily selection stop at
rung 0; concept explanation at rung 2; book summarization and citation
verification may reach rung 3.

## Compression Algorithm

Compression runs only when the pack still exceeds the budget after
prioritization (the first `on_input_overflow` action in `routing.yaml`).

```text
function compress(pack, B, must_keep):
    # step 1: free compression, no model call
    for item in pack sorted by priority asc:
        if item.rung > 0: downgrade one rung       # use stored summaries
        if fits(pack, B): return pack
    # step 2: drop lowest-priority non-target items
    drop items with priority < p20 and id not in targets
    if fits(pack, B): return pack
    # step 3: model compression with the context-compression skill
    out = call(skill="context-compression", model=haiku,
               input=pack, target=B, must_keep=must_keep)
    # fidelity guard
    for fact in must_keep:
        if fact.claim_id not in out.kept: fail("compression lost a claim")
    if any citation in out not traceable to an input chunk:
        fail("compression invented a citation")
    record(out.dropped)                            # listed in the step file
    return out.pack
    # still too big: split_task, then require budget_justification
```

Must-keep facts are the target IDs, every citation that will appear in the
output, and every claim flagged by QA in an earlier attempt.

## Caching

Three caches work together.

| Cache | Key | Invalidation | Saves |
| --- | --- | --- | --- |
| Prompt cache (provider) | Exact prefix bytes | Any change to the prefix | Input cost of the stable prefix at `cache_read_per_mtok` |
| Semantic cache (run cache) | `sha256(normalize(task) + sorted(id:content_hash) + model_id + prompt_version)` | Any referenced record's content hash changes, or prompt or model changes | The whole call |
| Output reuse | Accepted outputs in the repository | Record change triggers a regeneration proposal | Re-deriving summaries, cards, compressions |

```text
function assemble_prompt(task, pack):
    return concat(
        GLOBAL(agent, skill),        # identical for every call of the skill
        REPOSITORY_EXCERPT(task),    # sorted, stable ordering
        PROJECT_MEMORY(task),        # stable within a project
        cache_breakpoint(),
        DOCUMENT(pack),              # sorted by id for stable bytes
        LOCAL(task))                 # task spec and hand-off cards last

function cached_call(task, pack):
    key = sha256(normalize(task) + join(sorted(r.id + ":" + r.hash
                 for r in pack)) + model_id + prompt_version)
    if key in run_cache and run_cache[key].accepted: return it
    out = call_model(assemble_prompt(task, pack))
    run_cache[key] = out
    return out

normalize(task): lowercase, strip whitespace, sort list fields,
                 drop run_id and timestamps
```

The workflow idempotency key `(run_id, step, inputs_hash)` described in
[Workflow Architecture](09-workflow-architecture.md) is the run-local form
of the same idea. Cache hits are recorded on the ledger as
`cache_read_tokens` so `scripts/cost-report.py` can compute `cache_hit_rate`
(target at least 0.5).

## Token Budget Framework

| Model | Max input | Max output | Typical agents |
| --- | --- | --- | --- |
| haiku | 10,000 | 2,000 | `metadata`, `quality-assurance`, `daily-word`, `difficulty-assessor` |
| sonnet | 30,000 | 5,000 | `study-notes`, `knowledge-graph`, `reading-guide`, `research` |
| opus | 100,000 | 10,000 | `chief-librarian`, `canon-editor`, `islamic-civilization` |

The effective budget is the smallest of the model cap, the agent's
`token_budget` and the skill's `token_budget`. Overflow follows
`budget_policy`: input overflow runs `compress_context`, `split_task`,
`require_justification`; output overflow runs `split_task`,
`require_justification`. A larger model is never used to obtain a larger
window.

### Budget Justification Schema

Written to the step file as `budget_justification` when a call must exceed
its budget after compression and splitting.

```yaml
budget_justification:
  run_id: canon-revision-20261013T060000Z-3fa2
  step: 5
  agent: canon-editor
  task: canon_ranking
  model: opus
  budget: {input: 80000, output: 10000}      # skill canon-ranking
  requested: {input: 96000, output: 10000}
  overflow: {input: 16000, output: 0}
  actions_tried: [compress_context, split_task]
  why_not_split: Ranking must compare all 100 candidates in one pass.
  must_keep: [candidate cards, scoring rubric, bias-audit findings]
  expected_cost_usd: 0.58
  approved_by: router          # owner when above the model cap
```

A justification may raise a budget only up to the model cap. Exceeding the
model cap is not possible; the task must be split.

## Chunking Long Works

| Rule | Value |
| --- | --- |
| Boundary | Chapter, then section, then paragraph; never mid-sentence |
| Chunk size | <= 8,000 tokens so a chunk plus prompt fits haiku's 10,000 cap |
| Overlap | 400 tokens (last paragraph of the previous chunk) |
| Chunk ID | `<record-id>#c<NN>`, for example `book-<slug>#c07` |
| Chunk card | id, parent id, ordinal, heading, 1-line summary, tokens, offsets |
| Index location | Chunk cards beside record cards in the retrieval index (planned; today `build-context.py` splits full content at Markdown H2 sections on the fly) |
| Digest | Each chunk gets a <= 600-token digest via `knowledge_compression` (haiku, batch) |
| Reduce | Summaries are written from digests, not from full text |

Chunk cards let citation verification open a single chunk instead of the
whole work.

## Worked Example: One Book Ingestion

A 120,000-token work through `book-ingestion`. Prices from `models.yaml`;
batch-eligible tasks at 50%.

| Step | Task / model | Input tokens | Output tokens | Cost USD |
| --- | --- | --- | --- | --- |
| Chunk digests | `knowledge_compression`, haiku, 15 x (8,000 + 400 overlap + 1,000 prefix), batch | 141,000 | 9,000 | 0.0093 |
| Layered summaries | `book_summary`, sonnet: 15 digests (9,000) + prefix and card (1,700) | 10,700 | 3,000 | 0.0514 |
| Concept notes | `study_note`, sonnet, 2 x 5,000 | 10,000 | 2,400 | 0.0440 |
| Graph proposals | `knowledge_graph_proposal`, sonnet | 6,000 | 1,000 | 0.0220 |
| Tags | `tagging`, haiku, batch | 3,000 | 200 | 0.0002 |
| Difficulty | `difficulty_assessment`, haiku, batch | 5,000 | 600 | 0.0004 |
| Record and duplicates | `duplicate_detection`, haiku | 4,000 | 500 | 0.0007 |
| QA scoring | `qa_review`, sonnet | 10,000 | 1,000 | 0.0300 |
| Citation check | `citation_verification`, sonnet | 6,000 | 800 | 0.0200 |
| Total | | 195,700 | 18,500 | 0.178 |

Arithmetic for the two largest lines:

```text
digests  = 141,000 x 0.10/1e6 + 9,000 x 0.50/1e6
         = 0.0141 + 0.0045 = 0.0186; x 0.5 batch = 0.0093
summary  = 10,700 x 2.00/1e6 + 3,000 x 10.00/1e6
         = 0.0214 + 0.0300 = 0.0514
```

Without the framework (hypothetical; the router would refuse it), the full
text would be sent to sonnet for the summary, the notes (twice), the graph
proposals, QA and citations: `6 x 120,000 = 720,000` input tokens and about
11,400 output tokens, or `1.44 + 0.114 = 1.554` USD. The optimized run uses
42,700 sonnet input tokens instead of 720,000 (94% fewer) and costs 0.178
USD (89% less), inside the `book-ingestion` per-run cap of 0.60.

Prompt caching adds a further saving: a 2,000-token stable prefix reused by
the six sonnet calls gives five cache reads, `5 x 2,000 x (2.00 - 0.20)/1e6
= 0.018` USD, about 10% of the run.

## Expected Savings

| Lever | Typical reduction | Measured by |
| --- | --- | --- |
| Index cards instead of files | 95%+ of selection input | `tokens_per_artifact` |
| Retrieval ladder stop at rung 1 or 2 | 70 to 90% of document input | ladder rung histogram in step files |
| Chunk digests on haiku | 85 to 95% vs sonnet on full text | book-ingestion cost per run |
| Prompt caching | up to 90% of prefix input | `cache_hit_rate` >= 0.5 |
| Batch API | 50% of eligible calls | `batch_share` >= 0.8 |
| Semantic cache and output reuse | whole calls avoided | ledger `cache_read_tokens`, reruns |

## Token Optimization Summary

Context is assembled in five layers from stable to volatile, and only the
layers a task needs are loaded. Content is read through a four-rung ladder,
candidates are scored by relevance, authority, recency and cost, and packs
are compressed with a fidelity guard before any budget is exceeded. Stable
prefixes cache, identical tasks over unchanged records reuse outputs, and
long works are chunked and digested on haiku. The result is a book
ingestion at about 0.18 USD instead of about 1.55 USD.
