import unittest

from helpers import TempRepo

from bayan import graph, metadata
from bayan.common import Report


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)

    def check(self, edges):
        self.repo.write("metadata/relationships/extra.yaml", edges)
        reg = self.repo.registries()
        lib = metadata.load(self.repo.root, reg)
        report = Report("graph")
        graph.validate(lib, reg, report)
        return {f.code for f in report.findings}

    def test_fixture_graph_is_valid(self):
        self.assertEqual(self.check([]), set())

    def test_signature_violation(self):
        self.assertIn("signature", self.check([{
            "source": "book-muqaddimah", "relationship": "studied_under",
            "target": "author-ibn-sina", "confidence": "tentative"}]))

    def test_inverse_form_rejected(self):
        self.assertIn("inverse-stored", self.check([{
            "source": "author-ibn-sina", "relationship": "influenced_by",
            "target": "author-al-farabi", "confidence": "high",
            "citations": ["x"]}]))

    def test_high_confidence_needs_citation(self):
        self.assertIn("citation", self.check([{
            "source": "author-ibn-sina", "relationship": "influenced",
            "target": "author-ibn-khaldun", "confidence": "high"}]))

    def test_dangling_and_duplicate(self):
        codes = self.check([
            {"source": "author-al-farabi", "relationship": "influenced",
             "target": "author-ibn-sina", "confidence": "tentative"},
            {"source": "author-al-farabi", "relationship": "influenced",
             "target": "author-nobody", "confidence": "tentative"}])
        self.assertTrue({"duplicate-edge", "dangling-node"} <= codes)

    def test_build_materialises_inverses_and_maps(self):
        reg = self.repo.registries()
        lib = metadata.load(self.repo.root, reg)
        built = graph.build(lib, reg)
        triples = {(e["source"], e["relationship"], e["target"])
                   for e in built["edges"]}
        self.assertIn(("author-al-farabi", "influenced", "author-ibn-sina"),
                      triples)
        self.assertIn(("author-ibn-sina", "influenced_by",
                       "author-al-farabi"), triples)
        # Derived from author_id on the book record.
        self.assertIn(("author-ibn-khaldun", "wrote", "book-muqaddimah"),
                      triples)
        influence = graph.subgraph(built, next(
            m for m in reg.graph["maps"] if m["id"] == "influence-map"))
        self.assertTrue(influence["edges"])
        near = graph.neighbourhood(built, ["author-ibn-sina"], depth=1)
        self.assertIn("author-al-farabi", {n["id"] for n in near["nodes"]})
        with self.assertRaises(ValueError):
            graph.neighbourhood(built, ["author-ibn-sina"], depth=3)


if __name__ == "__main__":
    unittest.main()
