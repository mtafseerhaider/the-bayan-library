"""Reference model router.

Implements system/registry/routing.yaml: route every task to the smallest
model that can reliably do it, escalate one rung at a time only with a
written justification, downgrade forbidden work away from Opus, and keep
context inside the model's token budget.

The router is pure: it never calls a model. An orchestrator calls
`route()` before each model call and stores the decision in the run log.
"""

from __future__ import annotations

import operator
from dataclasses import asdict, dataclass, field
from typing import Any

from .registry import Registries

OPERATORS = {"eq": operator.eq, "gt": operator.gt, "gte": operator.ge,
             "lt": operator.lt, "lte": operator.le}
GATE_ORDER = ["G0", "G1", "G2", "G3", "G4"]


@dataclass
class Decision:
    task: str
    complexity_class: str
    execution: str
    model: str | None
    model_id: str | None
    effort: str | None
    input_budget: int
    output_budget: int
    status: str = "ok"                # ok | needs_justification | blocked
    escalations: list[dict] = field(default_factory=list)
    downgrades: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    review_gate: str = "G0"
    batch: bool = False
    degraded: bool = False
    estimated_cost_usd: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class RoutingError(ValueError):
    pass


def _stricter(a: str, b: str) -> str:
    return a if GATE_ORDER.index(a) >= GATE_ORDER.index(b) else b


def _fires(trigger: dict, signals: dict) -> bool:
    value = signals.get(trigger["signal"])
    if value is None:
        return False
    return OPERATORS[trigger["operator"]](value, trigger["value"])


def estimate_cost(reg: Registries, model: str, input_tokens: int,
                  output_tokens: int, batch: bool = False,
                  cached_tokens: int = 0) -> float:
    pricing = reg.model(model)["pricing"]
    uncached = max(0, input_tokens - cached_tokens)
    cost = (uncached * pricing["input_per_mtok"]
            + cached_tokens * pricing.get("cache_read_per_mtok",
                                          pricing["input_per_mtok"])
            + output_tokens * pricing["output_per_mtok"]) / 1_000_000
    if batch:
        cost *= reg.models["discounts"]["batch_api_multiplier"]
    return round(cost, 6)


def route(reg: Registries, spec: dict[str, Any]) -> Decision:
    """Route one task.

    spec keys:
      task (required)            task type from routing.yaml
      agent                      agent_id; its review gate is applied
      signals                    {source_count, comparative, ...}
      input_tokens, output_tokens  estimates for the planned call
      justification              why an escalation is needed
      budget_justification       why a budget overflow is needed
      incompressible             context cannot be compressed further
      change_classes             e.g. [canon_change]; raises the gate
      interactive                a reader is waiting (disables batch)
      failed_models              models that failed or are unavailable
    """
    task = spec.get("task")
    entry = reg.task_type(task) if task else None
    if entry is None:
        raise RoutingError(f"unknown task type {task!r}; add it to "
                           "system/registry/routing.yaml")
    cls = reg.complexity_class(entry["class"])
    signals = spec.get("signals", {}) or {}
    ladder = reg.models["escalation_ladder"]
    rules = reg.routing

    decision = Decision(task=task, complexity_class=entry["class"],
                        execution=entry["execution"], model=cls["model"],
                        model_id=None, effort=cls["effort"],
                        input_budget=0, output_budget=0)

    # 1. Deterministic work never calls a model.
    if entry["execution"] == "script":
        decision.model = None
        decision.effort = None
        decision.notes.append("script execution: no model call")
        decision.review_gate = _gate(reg, spec, "G0")
        return decision

    # 2. Downgrade rules: some work is never done on Opus.
    forbidden = set(rules["downgrade_rules"]["forbidden_on_opus"])
    ceiling = ladder[-1]
    if task in forbidden:
        ceiling = ladder[-2]
        if decision.model == "opus":
            decision.model = rules["downgrade_rules"]["downgrade_to"]
            decision.downgrades.append(
                f"{task} is forbidden on opus; downgraded to "
                f"{decision.model}")

    # 3. Escalation, one rung at a time, with justification.
    while True:
        rule = next((r for r in rules["escalation_rules"]
                     if r["from"] == decision.model), None)
        if rule is None or rule["to"] not in ladder:
            break
        # A rule climbs exactly one rung (validate-registry enforces it);
        # anything else is ignored here so a misedited rule cannot loop.
        if ladder.index(rule["to"]) != ladder.index(decision.model) + 1 or \
                ladder.index(rule["to"]) > ladder.index(ceiling):
            break
        fired = [t for t in rule["triggers"] if _fires(t, signals)]
        if not fired:
            break
        reasons = [t["reason"] for t in fired]
        decision.escalations.append({"from": rule["from"], "to": rule["to"],
                                     "reasons": reasons})
        decision.model = rule["to"]
        # QA failures were counted at the previous rung; they must not
        # push the task up a second rung in the same decision.
        signals = {**signals, "qa_failures": 0}
        if rule["justification_required"] and not spec.get("justification"):
            decision.status = "needs_justification"

    # 4. Fallback when the chosen model failed or is unavailable. The
    #    agent's fallback_model is used when it is available, one rung
    #    away and under the ceiling; otherwise the nearest available rung
    #    above, then the nearest below. The ceiling still holds, so
    #    forbidden work never reaches opus by way of an outage, and an
    #    upward fallback is recorded as an escalation.
    failed = set(spec.get("failed_models", []) or [])
    if decision.model in failed:
        rung = ladder.index(decision.model)
        available = [m for m in ladder if m not in failed
                     and ladder.index(m) <= ladder.index(ceiling)]
        agent = reg.agents.get(spec.get("agent", ""), {})
        fallback = agent.get("fallback_model")
        if fallback not in available or \
                abs(ladder.index(fallback) - rung) != 1:
            above = [m for m in available if ladder.index(m) > rung]
            below = [m for m in available if ladder.index(m) < rung]
            fallback = above[0] if above else below[-1] if below else None
        if fallback is None:
            decision.status = "blocked"
            decision.notes.append("no model available")
            return decision
        if ladder.index(fallback) < rung:
            decision.degraded = True
            decision.notes.append(
                f"fallback {decision.model} -> {fallback}: result is "
                "degraded and the review gate is raised one level")
        else:
            decision.escalations.append({
                "from": decision.model, "to": fallback,
                "reasons": [f"fallback: {decision.model} failed or "
                            "unavailable"]})
        decision.model = fallback

    model = reg.model(decision.model)
    decision.model_id = model["model_id"]
    decision.input_budget = model["budget"]["max_input_tokens"]
    decision.output_budget = model["budget"]["max_output_tokens"]
    if decision.effort is None or decision.downgrades:
        decision.effort = model["default_effort"]

    # 5. Budget policy: compress first, then split, then justify.
    want_in = int(spec.get("input_tokens", 0) or 0)
    want_out = int(spec.get("output_tokens", 0) or 0)
    if want_in > decision.input_budget:
        if not spec.get("incompressible"):
            decision.actions.append(
                f"compress_context: {want_in} -> {decision.input_budget} "
                "tokens via the retrieval ladder")
            want_in = decision.input_budget
        elif spec.get("budget_justification"):
            decision.actions.append("input budget exceeded with "
                                    "justification")
        else:
            decision.actions.append("split_task or provide "
                                    "budget_justification")
            decision.status = "blocked"
    if want_out > decision.output_budget:
        if spec.get("budget_justification"):
            decision.actions.append("output budget exceeded with "
                                    "justification")
        else:
            decision.actions.append("split_task: output exceeds budget")
            want_out = decision.output_budget

    # 6. Batch, gate and cost.
    batch_tasks = set(rules["downgrade_rules"].get("batch_eligible", []))
    decision.batch = task in batch_tasks and not spec.get("interactive")
    gate = _gate(reg, spec, "G1" if decision.model == "haiku" else "G2")
    if decision.degraded:
        gate = GATE_ORDER[min(GATE_ORDER.index(gate) + 1, 4)]
    decision.review_gate = gate
    decision.estimated_cost_usd = estimate_cost(
        reg, decision.model, want_in, want_out, decision.batch)
    return decision


def _gate(reg: Registries, spec: dict, default: str) -> str:
    gate = default
    agent = reg.agents.get(spec.get("agent", ""))
    if agent:
        gate = agent["quality"]["review_gate"]
    mandatory = {m["change_class"]: m["gate"]
                 for m in reg.permissions["mandatory_review"]}
    for change in spec.get("change_classes", []) or []:
        if change in mandatory:
            gate = _stricter(gate, mandatory[change])
    return gate
