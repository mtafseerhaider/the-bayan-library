import unittest

from helpers import TempRepo, registry


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo(with_fixture=False)
        self.addCleanup(self.repo.cleanup)

    def run_checks(self):
        return registry.run(self.repo.root)

    def codes(self):
        return {f.code for f in self.run_checks().findings}

    def test_committed_registries_are_valid(self):
        report = self.run_checks()
        self.assertEqual(report.findings, [], [f.render()
                                               for f in report.findings])

    def test_every_agent_has_exactly_one_tier(self):
        reg = self.repo.registries()
        self.assertEqual(len(reg.agents), 46)
        for agent in reg.agents.values():
            self.assertIn(agent["permission_level"], range(1, 6))

    def test_required_agents_present(self):
        reg = self.repo.registries()
        for agent_id in ("chief-librarian", "canon-editor", "metadata",
                         "knowledge-graph", "reading-guide", "documentation",
                         "research", "learning-coach", "study-notes",
                         "islamic-civilization", "quran-learning", "poetry",
                         "daily-wisdom", "automation", "quality-assurance",
                         "risk-management"):
            self.assertIn(agent_id, reg.agents)

    def test_agent_model_must_match_class(self):
        path = "system/registry/agents/core.yaml"
        data = self.repo.read_yaml(path)
        data["agents"][0]["default_model"] = "haiku"   # chief-librarian, E
        self.repo.write(path, data)
        self.assertIn("agent-model", self.codes())

    def test_skill_cycle_detected(self):
        path = "system/registry/skills.yaml"
        data = self.repo.read_yaml(path)
        skills = {s["skill_id"]: s for s in data["skills"]}
        skills["source-retrieval"]["dependencies"] = ["book-summarization"]
        self.repo.write(path, data)
        self.assertIn("skill-cycle", self.codes())

    def test_budget_over_model_cap(self):
        path = "system/registry/skills.yaml"
        data = self.repo.read_yaml(path)
        data["skills"][0]["token_budget"]["input"] = 50000   # haiku: 10K
        self.repo.write(path, data)
        self.assertIn("token-budget", self.codes())

    def test_envelopes_must_sum_to_cap(self):
        path = "system/registry/budgets.yaml"
        data = self.repo.read_yaml(path)
        data["monthly"]["total_cap"] = 61
        self.repo.write(path, data)
        self.assertIn("envelopes", self.codes())

    def test_unknown_skill_reference(self):
        path = "system/registry/agents/daily.yaml"
        data = self.repo.read_yaml(path)
        data["agents"][0]["required_skills"].append("no-such-skill")
        self.repo.write(path, data)
        self.assertIn("unknown-skill", self.codes())

    def test_opus_never_runs_forbidden_tasks(self):
        path = "system/registry/routing.yaml"
        data = self.repo.read_yaml(path)
        for task in data["task_types"]:
            if task["task"] == "tagging":
                task["class"] = "D"
        self.repo.write(path, data)
        self.assertIn("opus-forbidden", self.codes())

    def test_skill_dependencies_are_acyclic(self):
        reg = self.repo.registries()
        order = registry.topological_order(reg.skills)
        position = {s: i for i, s in enumerate(order)}
        for skill in reg.skills.values():
            for dep in skill["dependencies"]:
                self.assertLess(position[dep], position[skill["skill_id"]])

    def test_tier_write_paths(self):
        reg = self.repo.registries()
        self.assertEqual(registry.tiers_allowed_to_write(
            reg, "canon/top-100-books/README.md"), [4, 5])
        self.assertEqual(registry.tiers_allowed_to_write(
            reg, "metadata/books/book-x.yaml"), [3, 4, 5])
        self.assertEqual(registry.tiers_allowed_to_write(
            reg, "notes/reflections/2026-10-13.md"), [])
        self.assertEqual(registry.tiers_allowed_to_write(
            reg, ".github/workflows/validate.yml"), [5])


if __name__ == "__main__":
    unittest.main()
