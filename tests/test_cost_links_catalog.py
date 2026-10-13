import json
import unittest

from helpers import REPO, TempRepo

from bayan import catalog, cost, links


class CostTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo(with_fixture=False)
        self.addCleanup(self.repo.cleanup)
        self.reg = self.repo.registries()

    def ledger(self, rows):
        path = self.repo.root / "ledger.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        return cost.read_ledger([path])

    def test_summary_and_alerts(self):
        rows = self.ledger([
            {"run_id": "r1", "workflow_id": "daily-cycle",
             "agent_id": "daily-word", "model": "claude-haiku-5-5",
             "input_tokens": 4000, "output_tokens": 600, "batch": True,
             "accepted": True},
            {"run_id": "r2", "workflow_id": "canon-revision",
             "agent_id": "canon-editor", "model": "claude-opus-5-5",
             "input_tokens": 3_000_000, "output_tokens": 400_000,
             "escalated": False, "accepted": True},
        ])
        summary = cost.summarise(self.reg, rows)
        self.assertAlmostEqual(summary["metrics"]["total_cost"],
                               0.00035 + 12.0 + 8.0, places=3)
        found = cost.alerts(self.reg, summary)
        self.assertTrue(any("canon-editor" in a for a in found))
        self.assertTrue(any("opus share" in a for a in found))
        text = cost.render(self.reg, summary, "2026-10")
        self.assertIn("# Cost Report 2026-10", text)


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo(with_fixture=False)
        self.addCleanup(self.repo.cleanup)

    def test_broken_links_and_anchors(self):
        self.repo.write("a.md", "# A\n\n## Real Heading\n\n"
                        "[ok](#real-heading) [bad](#nope) [gone](b.md)\n"
                        "[ext](https://example.org)\n\n```text\n"
                        "[ignored](c.md)\n```\n")
        report = links.run(self.repo.root, [self.repo.root / "a.md"])
        codes = sorted(f.code for f in report.findings)
        self.assertEqual(codes, ["broken-anchor", "broken-link"])

    def test_slug(self):
        self.assertEqual(links.github_slug("Phase 1: Foundation"),
                         "phase-1-foundation")


class CatalogTests(unittest.TestCase):
    def test_committed_catalogs_are_current(self):
        repo = TempRepo(with_fixture=False)
        self.addCleanup(repo.cleanup)
        for name, content in catalog.build(repo.registries()).items():
            self.assertEqual((REPO / name).read_text(), content, name)


if __name__ == "__main__":
    unittest.main()
