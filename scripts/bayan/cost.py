"""Usage ledger aggregation and the monthly cost report.

Ledger format: JSON Lines, one object per model call:

    {"ts": "2026-10-13T04:00:12Z", "run_id": "daily-2026-10-13",
     "workflow_id": "daily-cycle", "agent_id": "daily-word",
     "skill_id": "vocabulary-analysis", "model": "claude-haiku-5-5",
     "input_tokens": 4100, "output_tokens": 620, "cache_read_tokens": 3000,
     "task": "vocabulary_analysis", "batch": true, "escalated": false,
     "accepted": true}
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .registry import Registries
from .router import estimate_cost


def read_ledger(paths: list[Path]) -> list[dict]:
    rows = []
    for path in paths:
        for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number}: {exc}") from exc
    return rows


def model_class(reg: Registries, model_id: str) -> str:
    for name, model in reg.models["models"].items():
        if model["model_id"] == model_id or name == model_id:
            return name
    raise ValueError(f"unknown model {model_id!r} in ledger")


def envelope_for(reg: Registries, agent_id: str, escalated: bool) -> str:
    family = reg.agents.get(agent_id, {}).get("family")
    if escalated:
        for env in reg.budgets["envelopes"]:
            if "escalations" in env["covers"]:
                return env["id"]
    for env in reg.budgets["envelopes"]:       # agent ID beats family
        if agent_id in env["covers"]:
            return env["id"]
    for env in reg.budgets["envelopes"]:
        if family in env["covers"]:
            return env["id"]
    return "unassigned"


def summarise(reg: Registries, rows: list[dict]) -> dict:
    totals = defaultdict(float)
    by = {k: defaultdict(float) for k in
          ("agent", "workflow", "model", "envelope", "run")}
    run_workflow = {}
    accepted = 0
    batch_tasks = set(reg.routing["downgrade_rules"].get("batch_eligible",
                                                         []))
    for row in rows:
        name = model_class(reg, row["model"])
        cost = estimate_cost(reg, name, row.get("input_tokens", 0),
                             row.get("output_tokens", 0),
                             bool(row.get("batch")),
                             row.get("cache_read_tokens", 0))
        totals["cost"] += cost
        totals["calls"] += 1
        totals["input"] += row.get("input_tokens", 0)
        totals["output"] += row.get("output_tokens", 0)
        totals["cached"] += row.get("cache_read_tokens", 0)
        eligible = row.get("task") is None or row.get("task") in batch_tasks
        totals["eligible_calls"] += 1 if eligible else 0
        totals["batch_calls"] += 1 if row.get("batch") and eligible else 0
        totals["escalated_calls"] += 1 if row.get("escalated") else 0
        totals["escalated_cost"] += cost if row.get("escalated") else 0
        if name == "opus":
            totals["opus_cost"] += cost
        if row.get("accepted"):
            accepted += 1
        by["agent"][row.get("agent_id", "unknown")] += cost
        by["workflow"][row.get("workflow_id", "ad-hoc")] += cost
        by["model"][name] += cost
        by["envelope"][envelope_for(reg, row.get("agent_id", ""),
                                    bool(row.get("escalated")))] += cost
        run = row.get("run_id", "unknown")
        by["run"][run] += cost
        run_workflow[run] = row.get("workflow_id", "ad-hoc")
    cost = totals["cost"]
    metrics = {
        "total_cost": round(cost, 4),
        "calls": int(totals["calls"]),
        "accepted_artifacts": accepted,
        "cost_per_accepted_artifact":
            round(cost / accepted, 4) if accepted else None,
        "opus_share": round(totals["opus_cost"] / cost, 4) if cost else 0.0,
        "escalation_rate": round(totals["escalated_calls"] /
                                 totals["calls"], 4) if rows else 0.0,
        "escalation_share": round(totals["escalated_cost"] / cost, 4)
        if cost else 0.0,
        "cache_hit_rate": round(totals["cached"] / totals["input"], 4)
        if totals["input"] else 0.0,
        # Share of batch-eligible calls (rows with a `task` field are
        # matched against routing.yaml; rows without one count as eligible).
        "batch_share": round(totals["batch_calls"] /
                             totals["eligible_calls"], 4)
        if totals["eligible_calls"] else 0.0,
        "tokens_per_artifact": {
            "input": round(totals["input"] / accepted) if accepted else None,
            "output": round(totals["output"] / accepted)
            if accepted else None,
        },
    }
    return {"metrics": metrics,
            "by": {k: dict(sorted(v.items())) for k, v in by.items()},
            "run_workflow": run_workflow}


def alerts(reg: Registries, summary: dict) -> list[str]:
    found = []
    budgets = reg.budgets
    cap = budgets["monthly"]["total_cap"]
    spent = summary["metrics"]["total_cost"]
    for threshold in sorted(budgets["monthly"]["alert_thresholds"]):
        if spent >= cap * threshold:
            level = "STOP" if threshold >= budgets["monthly"].get(
                "hard_stop_at", 1.0) else "ALERT"
            found.append(f"{level}: monthly spend ${spent:.2f} reached "
                         f"{int(threshold * 100)}% of ${cap:.2f}")
    for env in budgets["envelopes"]:
        used = summary["by"]["envelope"].get(env["id"], 0.0)
        if used > env["cap"]:
            found.append(f"ALERT: envelope {env['id']} ${used:.2f} over "
                         f"cap ${env['cap']:.2f}")
    for entry in budgets.get("agents", []):
        used = summary["by"]["agent"].get(entry["agent_id"], 0.0)
        if used > entry["monthly_cap"]:
            found.append(f"ALERT: agent {entry['agent_id']} ${used:.2f} "
                         f"over cap ${entry['monthly_cap']:.2f}")
    caps = {w["workflow_id"]: w["per_run_cap"] for w in budgets["workflows"]}
    for run, used in summary["by"]["run"].items():
        workflow = summary["run_workflow"].get(run)
        if workflow in caps and used > caps[workflow]:
            found.append(f"ALERT: run {run} ({workflow}) ${used:.2f} over "
                         f"per-run cap ${caps[workflow]:.2f}")
    escalation = budgets["escalation"]
    metrics = summary["metrics"]
    if metrics["opus_share"] > escalation["max_opus_share"]:
        found.append(f"ALERT: opus share {metrics['opus_share']:.0%} above "
                     f"{escalation['max_opus_share']:.0%}")
    if metrics["escalation_share"] > escalation["max_escalation_share"]:
        found.append(f"ALERT: escalation share "
                     f"{metrics['escalation_share']:.0%} above "
                     f"{escalation['max_escalation_share']:.0%}")
    return found


def render(reg: Registries, summary: dict, period: str) -> str:
    metrics = summary["metrics"]
    cap = reg.budgets["monthly"]["total_cap"]
    lines = [f"# Cost Report {period}", "",
             "Generated by `scripts/cost-report.py` from the usage ledger.",
             "", "## Summary", "",
             "| Metric | Value |", "| --- | ---: |",
             f"| Total spend | ${metrics['total_cost']:.2f} of "
             f"${cap:.2f} |",
             f"| Model calls | {metrics['calls']} |",
             f"| Accepted artifacts | {metrics['accepted_artifacts']} |",
             f"| Cost per accepted artifact | "
             f"{_money(metrics['cost_per_accepted_artifact'])} |",
             f"| Opus share | {metrics['opus_share']:.1%} |",
             f"| Escalation rate | {metrics['escalation_rate']:.1%} |",
             f"| Cache hit rate | {metrics['cache_hit_rate']:.1%} |",
             f"| Batch share | {metrics['batch_share']:.1%} |", ""]
    found = alerts(reg, summary)
    lines += ["## Alerts", ""]
    lines += [f"- {a}" for a in found] if found else ["- None."]
    lines.append("")
    caps = {e["id"]: e["cap"] for e in reg.budgets["envelopes"]}
    for key, title in (("envelope", "Envelopes"), ("model", "Models"),
                       ("workflow", "Workflows"), ("agent", "Agents")):
        lines += [f"## {title}", "", "| Name | Spend | Cap |",
                  "| --- | ---: | ---: |"]
        for name, used in summary["by"][key].items():
            limit = caps.get(name) if key == "envelope" else None
            lines.append(f"| {name} | ${used:.4f} | "
                         f"{_money(limit) if limit else '-'} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _money(value) -> str:
    return "-" if value is None else f"${value:.2f}"
