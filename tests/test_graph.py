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

    def test_unknown_confidence_is_a_finding_not_a_crash(self):
        self.assertIn("evidence", self.check([{
            "source": "author-al-farabi", "relationship": "influenced",
            "target": "author-ibn-khaldun", "confidence": "medium"}]))

    def test_derived_edges_must_fit_the_ontology(self):
        # Drop `author` from `wrote`: the book's author_id then implies an
        # edge the ontology forbids, reported against the record and left
        # out of the build.
        path = "system/registry/knowledge-graph.yaml"
        data = self.repo.read_yaml(path)
        for relation in data["relationship_types"]:
            if relation["type"] == "wrote":
                relation["source"] = ["poet"]
        self.repo.write(path, data)
        reg = self.repo.registries()
        lib = metadata.load(self.repo.root, reg)
        report = Report("graph")
        graph.validate(lib, reg, report)
        # Reported against each record that implies the edge: the book's
        # author_id and the author's major_works.
        hits = {f.location for f in report.findings if f.code == "signature"}
        self.assertTrue(any("book-muqaddimah" in h for h in hits), hits)
        self.assertTrue(any("author-ibn-khaldun" in h for h in hits), hits)
        triples = {(e["source"], e["relationship"], e["target"])
                   for e in graph.build(lib, reg)["edges"]}
        self.assertNotIn(("author-ibn-khaldun", "wrote", "book-muqaddimah"),
                         triples)

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
