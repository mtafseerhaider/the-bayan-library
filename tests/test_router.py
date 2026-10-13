import unittest

from helpers import TempRepo

from bayan import router


class RouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo = TempRepo(with_fixture=False)
        cls.reg = repo.registries()
        repo.cleanup()

    def route(self, **spec):
        return router.route(self.reg, spec)

    def test_simple_task_uses_haiku(self):
        d = self.route(task="tagging", input_tokens=2000, output_tokens=200)
        self.assertEqual((d.model, d.model_id), ("haiku", "claude-haiku-5-5"))
        self.assertEqual(d.status, "ok")
        self.assertTrue(d.batch)

    def test_script_tasks_call_no_model(self):
        d = self.route(task="link_validation")
        self.assertIsNone(d.model)
        self.assertEqual(d.estimated_cost_usd, 0.0)

    def test_haiku_to_sonnet_needs_justification(self):
        d = self.route(task="knowledge_compression",
                       signals={"source_count": 5})
        self.assertEqual(d.model, "sonnet")
        self.assertEqual(d.status, "needs_justification")
        d = self.route(task="knowledge_compression",
                       signals={"source_count": 5},
                       justification="Five chapters must be merged.")
        self.assertEqual(d.status, "ok")

    def test_three_sources_do_not_escalate(self):
        d = self.route(task="tagging", signals={"source_count": 3})
        self.assertEqual(d.model, "haiku")

    def test_two_rung_escalation(self):
        d = self.route(task="knowledge_compression", justification="x",
                       signals={"comparative": True,
                                "cross_civilizational": True})
        self.assertEqual(d.model, "opus")
        self.assertEqual(len(d.escalations), 2)

    def test_qa_failures_climb_one_rung_only(self):
        d = self.route(task="tagging", justification="x",
                       signals={"qa_failures": 2})
        self.assertEqual(d.model, "sonnet")

    def test_forbidden_tasks_never_reach_opus(self):
        d = self.route(task="tagging", justification="x",
                       signals={"comparative": True, "canon_decision": True})
        self.assertEqual(d.model, "sonnet")

    def test_expert_task_uses_opus_with_mandatory_gate(self):
        d = self.route(task="canon_ranking", agent="canon-editor",
                       input_tokens=60000, change_classes=["ranking_change"])
        self.assertEqual(d.model_id, "claude-opus-5-5")
        self.assertEqual(d.review_gate, "G4")

    def test_budget_overflow_compresses_then_blocks(self):
        d = self.route(task="book_summary", input_tokens=45000)
        self.assertEqual(d.status, "ok")
        self.assertTrue(d.actions[0].startswith("compress_context"))
        d = self.route(task="book_summary", input_tokens=45000,
                       incompressible=True)
        self.assertEqual(d.status, "blocked")
        d = self.route(task="book_summary", input_tokens=45000,
                       incompressible=True,
                       budget_justification="Primary text cannot be cut.")
        self.assertEqual(d.status, "ok")

    def test_fallback_is_degraded_and_raises_gate(self):
        d = self.route(task="canon_ranking", agent="canon-editor",
                       failed_models=["opus"])
        self.assertEqual(d.model, "sonnet")
        self.assertTrue(d.degraded)

    def test_unknown_task(self):
        with self.assertRaises(router.RoutingError):
            self.route(task="write_poem_from_scratch")

    def test_cost_estimate(self):
        cost = router.estimate_cost(self.reg, "sonnet", 1_000_000, 0)
        self.assertEqual(cost, 2.0)
        self.assertEqual(router.estimate_cost(self.reg, "sonnet",
                                              1_000_000, 0, batch=True), 1.0)


if __name__ == "__main__":
    unittest.main()
