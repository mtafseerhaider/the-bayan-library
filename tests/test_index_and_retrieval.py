import json
import unittest

from helpers import TempRepo

from bayan import index, metadata, retrieval


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)
        self.lib = metadata.load(self.repo.root, self.repo.registries())

    def test_build_is_deterministic_and_detects_drift(self):
        files = index.build(self.lib)
        self.assertEqual(files, index.build(self.lib))
        self.assertTrue(index.drift(self.lib, files))     # not written yet
        index.write(self.lib, files)
        self.assertEqual(index.drift(self.lib, files), [])
        cards = [json.loads(line) for line in
                 files["metadata/index/book.jsonl"].splitlines()]
        self.assertEqual([c["id"] for c in cards],
                         ["book-muqaddimah", "book-the-book-of-healing"])
        tokens = cards[0]["tokens"]
        self.assertTrue(0 < tokens["card"] and 0 < tokens["summary"]
                        < tokens["executive"])


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)
        lib = metadata.load(self.repo.root, self.repo.registries())
        index.write(lib, index.build(lib))

    def test_small_budget_stays_on_cards(self):
        pack = retrieval.build(self.repo.root, {"book-muqaddimah": 1.0},
                               budget=60)
        self.assertEqual(pack["items"][0]["layer"], "card")
        self.assertLessEqual(pack["used_tokens"], 60)

    def test_ladder_climbs_in_order_within_budget(self):
        pack = retrieval.build(self.repo.root, {
            "book-muqaddimah": 1.0, "author-ibn-khaldun": 0.5},
            budget=200, max_layer="executive")
        layers = {i["id"]: i["layer"] for i in pack["items"]}
        self.assertEqual(layers["book-muqaddimah"], "executive")
        self.assertLessEqual(pack["used_tokens"], 200)

    def test_full_content_is_chunked(self):
        pack = retrieval.build(self.repo.root, {"book-muqaddimah": 1.0},
                               budget=10000)
        item = pack["items"][0]
        self.assertEqual(item["layer"], "full")
        self.assertEqual(item["chunks"], 4)

    def test_missing_targets_reported(self):
        pack = retrieval.build(self.repo.root, {"book-nope": 1.0}, 500)
        self.assertEqual(pack["missing"], ["book-nope"])


if __name__ == "__main__":
    unittest.main()
