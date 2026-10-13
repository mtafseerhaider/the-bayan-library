"""Load the system registries and check them for internal consistency.

The registries in system/registry/ are the source of truth for agents,
skills, routing, permissions, memory, the graph ontology, workflows and
budgets. This module validates each file against its JSON Schema and then
enforces the cross-file rules that a schema cannot express.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from . import schemas
from .common import Report, load_yaml, rel

CLASS_MODEL = {"A": "haiku", "B": "sonnet", "C": "sonnet",
               "D": "opus", "E": "opus"}

# registry file -> schema file (relative to system/schemas/registry)
SINGLE_FILES = {
    "models.yaml": "models.schema.json",
    "routing.yaml": "routing.schema.json",
    "permissions.yaml": "permissions.schema.json",
    "review-gates.yaml": "review-gates.schema.json",
    "memory.yaml": "memory.schema.json",
    "knowledge-graph.yaml": "knowledge-graph.schema.json",
    "workflows.yaml": "workflows.schema.json",
    "budgets.yaml": "budgets.schema.json",
    "skills.yaml": "skill.schema.json",
}


@dataclass
class Registries:
    root: Path
    models: dict
    routing: dict
    permissions: dict
    gates: dict
    memory: dict
    graph: dict
    workflows: dict
    budgets: dict
    skills: dict[str, dict]
    agents: dict[str, dict]
    agent_files: dict[str, str]

    def model(self, name: str) -> dict:
        return self.models["models"][name]

    def task_type(self, task: str) -> dict | None:
        for entry in self.routing["task_types"]:
            if entry["task"] == task:
                return entry
        return None

    def complexity_class(self, cls: str) -> dict:
        for entry in self.routing["complexity_classes"]:
            if entry["class"] == cls:
                return entry
        raise KeyError(cls)


def registry_dir(root: Path) -> Path:
    return root / "system" / "registry"


def schema_dir(root: Path) -> Path:
    return root / "system" / "schemas" / "registry"


def load(root: Path, report: Report | None = None) -> Registries:
    """Load every registry, recording schema violations in `report`."""
    reg_dir, sch_dir = registry_dir(root), schema_dir(root)
    data: dict[str, Any] = {}
    for name, schema in SINGLE_FILES.items():
        path = reg_dir / name
        content = load_yaml(path)
        data[name] = content
        if report is not None:
            for message in schemas.errors(sch_dir / schema, content):
                report.add("critical", "schema", message, rel(path, root))

    agents: dict[str, dict] = {}
    agent_files: dict[str, str] = {}
    for path in sorted((reg_dir / "agents").glob("*.yaml")):
        content = load_yaml(path)
        if report is not None:
            for message in schemas.errors(sch_dir / "agent.schema.json",
                                          content):
                report.add("critical", "schema", message, rel(path, root))
        for agent in content.get("agents", []):
            agent = {**agent, "family": content.get("family")}
            agent_id = agent.get("agent_id")
            if agent_id in agents and report is not None:
                report.add("critical", "duplicate-agent",
                           f"agent_id {agent_id!r} defined twice",
                           rel(path, root))
            agents[agent_id] = agent
            agent_files[agent_id] = rel(path, root)

    skills = {s["skill_id"]: s for s in data["skills.yaml"]["skills"]}
    if report is not None:
        ids = [s["skill_id"] for s in data["skills.yaml"]["skills"]]
        for dup in {i for i in ids if ids.count(i) > 1}:
            report.add("critical", "duplicate-skill",
                       f"skill_id {dup!r} defined twice", "skills.yaml")

    return Registries(
        root=root,
        models=data["models.yaml"],
        routing=data["routing.yaml"],
        permissions=data["permissions.yaml"],
        gates=data["review-gates.yaml"],
        memory=data["memory.yaml"],
        graph=data["knowledge-graph.yaml"],
        workflows=data["workflows.yaml"],
        budgets=data["budgets.yaml"],
        skills=skills,
        agents=agents,
        agent_files=agent_files,
    )


def topological_order(skills: dict[str, dict]) -> list[str]:
    """Return skills in dependency order; raise ValueError on a cycle."""
    order: list[str] = []
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(node: str, trail: list[str]) -> None:
        if state.get(node) == 2:
            return
        if state.get(node) == 1:
            cycle = " -> ".join([*trail[trail.index(node):], node])
            raise ValueError(f"dependency cycle: {cycle}")
        state[node] = 1
        for dep in skills.get(node, {}).get("dependencies", []):
            if dep in skills:
                visit(dep, [*trail, node])
        state[node] = 2
        order.append(node)

    for skill_id in sorted(skills):
        visit(skill_id, [])
    return order


def transitive_dependencies(skills: dict[str, dict], skill_id: str
                            ) -> list[str]:
    seen: list[str] = []
    stack = list(skills[skill_id]["dependencies"])
    while stack:
        dep = stack.pop(0)
        if dep not in seen and dep in skills:
            seen.append(dep)
            stack.extend(skills[dep]["dependencies"])
    return seen


def check(reg: Registries, report: Report) -> None:
    """Cross-file consistency rules."""
    models = reg.models["models"]
    tiers = {t["tier"]: t for t in reg.permissions["tiers"]}
    gates = {g["gate"] for g in reg.gates["gates"]}
    layers = {layer["id"] for layer in reg.memory["layers"]}
    opus_forbidden = set(reg.routing["downgrade_rules"]["forbidden_on_opus"])
    task_names = {t["task"] for t in reg.routing["task_types"]}

    # Models and classes.
    for name in reg.models["escalation_ladder"]:
        if name not in models:
            report.add("critical", "ladder", f"unknown model {name!r}",
                       "models.yaml")
    for cls in reg.routing["complexity_classes"]:
        if CLASS_MODEL[cls["class"]] != cls["model"]:
            report.add("critical", "class-model",
                       f"class {cls['class']} must route to "
                       f"{CLASS_MODEL[cls['class']]}, not {cls['model']}",
                       "routing.yaml")
    for task in opus_forbidden:
        if task not in task_names:
            report.add("major", "unknown-task",
                       f"forbidden_on_opus lists unknown task {task!r}",
                       "routing.yaml")
        entry = reg.task_type(task)
        if entry and CLASS_MODEL[entry["class"]] == "opus":
            report.add("critical", "opus-forbidden",
                       f"task {task!r} is forbidden on opus but its class "
                       f"{entry['class']} routes to opus", "routing.yaml")
    for task in reg.routing["downgrade_rules"].get("batch_eligible", []):
        if task not in task_names:
            report.add("major", "unknown-task",
                       f"batch_eligible lists unknown task {task!r}",
                       "routing.yaml")

    # Skills.
    for skill_id, skill in reg.skills.items():
        where = f"skills.yaml#{skill_id}"
        expected = CLASS_MODEL[skill["complexity_class"]]
        if skill["recommended_model"] != expected:
            report.add("major", "skill-model",
                       f"class {skill['complexity_class']} skills should "
                       f"recommend {expected}, not "
                       f"{skill['recommended_model']}", where)
        cap = models[skill["recommended_model"]]["budget"]
        _check_budget(report, where, skill["token_budget"], cap)
        if skill["execution"] == "script" and \
                any(skill["token_budget"].values()):
            report.add("major", "script-budget",
                       "script skills make no model call; token budget "
                       "must be 0/0", where)
        for dep in skill["dependencies"]:
            if dep not in reg.skills:
                report.add("critical", "unknown-skill",
                           f"depends on unknown skill {dep!r}", where)
            if dep == skill_id:
                report.add("critical", "self-dependency",
                           "skill depends on itself", where)
    try:
        topological_order(reg.skills)
    except ValueError as exc:
        report.add("critical", "skill-cycle", str(exc), "skills.yaml")

    # Agents.
    agent_ids = set(reg.agents)
    for agent_id, agent in reg.agents.items():
        where = f"{reg.agent_files[agent_id]}#{agent_id}"
        expected = CLASS_MODEL[agent["complexity_class"]]
        if agent["default_model"] != expected:
            report.add("critical", "agent-model",
                       f"class {agent['complexity_class']} agents default "
                       f"to {expected}, not {agent['default_model']}", where)
        if agent["fallback_model"] == agent["default_model"]:
            report.add("major", "fallback",
                       "fallback model equals default model", where)
        if agent["permission_level"] not in tiers:
            report.add("critical", "tier",
                       f"unknown tier {agent['permission_level']}", where)
        cap = models[agent["default_model"]]["budget"]
        _check_budget(report, where, agent["token_budget"], cap)
        for skill in agent["required_skills"]:
            if skill not in reg.skills:
                report.add("critical", "unknown-skill",
                           f"requires unknown skill {skill!r}", where)
        for kind in ("read", "write"):
            for layer in agent["memory"][kind]:
                if layer not in layers:
                    report.add("critical", "memory",
                               f"unknown memory layer {layer!r}", where)
        if not set(agent["memory"]["write"]) <= set(agent["memory"]["read"]):
            report.add("major", "memory",
                       "agents must be able to read what they write", where)
        if ("personal-reflection" in agent["memory"]["write"]
                and agent["permission_level"] > 2):
            report.add("critical", "privacy",
                       "only tier 1-2 agents may write personal "
                       "reflection memory", where)
        if agent["quality"]["review_gate"] not in gates:
            report.add("critical", "gate", "unknown review gate", where)
        if agent["reports_to"] != "owner" and \
                agent["reports_to"] not in agent_ids:
            report.add("critical", "reports-to",
                       f"reports to unknown agent {agent['reports_to']!r}",
                       where)
        for other in agent["collaborates_with"]:
            if other not in agent_ids:
                report.add("major", "collaborator",
                           f"collaborates with unknown agent {other!r}",
                           where)
    _check_reporting_cycles(reg, report)

    # Workflows.
    workflow_ids = set()
    budget_ids = {w["workflow_id"] for w in reg.budgets["workflows"]}
    for workflow in reg.workflows["workflows"]:
        where = f"workflows.yaml#{workflow['workflow_id']}"
        workflow_ids.add(workflow["workflow_id"])
        if workflow["review_gate"] not in gates:
            report.add("critical", "gate", "unknown review gate", where)
        if workflow["budget_ref"] not in budget_ids:
            report.add("critical", "budget-ref",
                       f"no budget named {workflow['budget_ref']!r}", where)
        for step in workflow["steps"]:
            if step["agent"] not in agent_ids:
                report.add("critical", "unknown-agent",
                           f"step uses unknown agent {step['agent']!r}",
                           where)
            for skill in step["skills"]:
                if skill not in reg.skills:
                    report.add("critical", "unknown-skill",
                               f"step uses unknown skill {skill!r}", where)

    # Budgets.
    monthly = reg.budgets["monthly"]["total_cap"]
    envelope_sum = round(sum(e["cap"] for e in reg.budgets["envelopes"]), 2)
    if abs(envelope_sum - monthly) > 0.005:
        report.add("critical", "envelopes",
                   f"envelopes sum to {envelope_sum}, cap is {monthly}",
                   "budgets.yaml")
    for entry in reg.budgets.get("agents", []):
        if entry["agent_id"] not in agent_ids:
            report.add("major", "unknown-agent",
                       f"budget for unknown agent {entry['agent_id']!r}",
                       "budgets.yaml")
    families = {a["family"] for a in reg.agents.values()}
    covered = set()
    for envelope in reg.budgets["envelopes"]:
        for item in envelope["covers"]:
            if item not in agent_ids | families | {"escalations"}:
                report.add("major", "envelope",
                           f"envelope {envelope['id']!r} covers unknown "
                           f"{item!r}", "budgets.yaml")
            covered.add(item)
    for agent_id, agent in reg.agents.items():
        if agent_id not in covered and agent["family"] not in covered:
            report.add("major", "envelope",
                       f"agent {agent_id!r} is not covered by any budget "
                       "envelope", "budgets.yaml")

    # Knowledge graph ontology.
    node_types = {n["type"] for n in reg.graph["node_types"]}
    prefixes = [n["prefix"] for n in reg.graph["node_types"]]
    for dup in {p for p in prefixes if prefixes.count(p) > 1}:
        report.add("critical", "prefix", f"duplicate prefix {dup!r}",
                   "knowledge-graph.yaml")
    rel_types = {r["type"] for r in reg.graph["relationship_types"]}
    for relation in reg.graph["relationship_types"]:
        for node in relation["source"] + relation["target"]:
            if node not in node_types:
                report.add("critical", "node-type",
                           f"{relation['type']} uses unknown node type "
                           f"{node!r}", "knowledge-graph.yaml")
        if relation.get("symmetric") and \
                relation["inverse"] != relation["type"]:
            report.add("major", "symmetric",
                       f"symmetric {relation['type']} must be its own "
                       "inverse", "knowledge-graph.yaml")
    for graph_map in reg.graph["maps"]:
        for node in graph_map["node_types"]:
            if node not in node_types:
                report.add("critical", "map", f"{graph_map['id']} uses "
                           f"unknown node type {node!r}",
                           "knowledge-graph.yaml")
        for relation in graph_map["relationship_types"]:
            if relation not in rel_types:
                report.add("critical", "map", f"{graph_map['id']} uses "
                           f"unknown relationship {relation!r}",
                           "knowledge-graph.yaml")

    # Permission tiers must be cumulative and gates must exist.
    for tier in reg.permissions["tiers"]:
        if tier["default_review_gate"] not in gates:
            report.add("critical", "gate",
                       f"tier {tier['tier']} uses unknown gate",
                       "permissions.yaml")
    for item in reg.permissions["mandatory_review"]:
        if item["gate"] not in gates:
            report.add("critical", "gate",
                       f"{item['change_class']} uses unknown gate",
                       "permissions.yaml")


def _check_budget(report: Report, where: str, budget: dict, cap: dict
                  ) -> None:
    if budget["input"] > cap["max_input_tokens"]:
        report.add("critical", "token-budget",
                   f"input budget {budget['input']} exceeds model cap "
                   f"{cap['max_input_tokens']}", where)
    if budget["output"] > cap["max_output_tokens"]:
        report.add("critical", "token-budget",
                   f"output budget {budget['output']} exceeds model cap "
                   f"{cap['max_output_tokens']}", where)


def _check_reporting_cycles(reg: Registries, report: Report) -> None:
    for start in reg.agents:
        seen = [start]
        current = reg.agents[start]["reports_to"]
        while current != "owner" and current in reg.agents:
            if current in seen:
                report.add("critical", "reporting-cycle",
                           " -> ".join([*seen, current]),
                           reg.agent_files[start])
                break
            seen.append(current)
            current = reg.agents[current]["reports_to"]


def tiers_allowed_to_write(reg: Registries, path: str) -> list[int]:
    """Return the tiers whose cumulative write_paths include `path`."""
    allowed = []
    for tier in sorted(reg.permissions["tiers"], key=lambda t: t["tier"]):
        paths = []
        for other in reg.permissions["tiers"]:
            if other["tier"] <= tier["tier"]:
                paths.extend(other["write_paths"])
        protected = [p for t in reg.permissions["tiers"]
                     for p in t.get("protected_paths", [])]
        if any(fnmatch(path, p) for p in paths) and \
                not any(fnmatch(path, p) for p in protected):
            allowed.append(tier["tier"])
    return allowed


def run(root: Path) -> Report:
    report = Report("Registry validation")
    reg = load(root, report)
    if not report.failed("critical"):
        check(reg, report)
    return report
