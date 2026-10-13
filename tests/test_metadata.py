import unittest

from helpers import TempRepo

from bayan import metadata, paths


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)

    def validate(self):
        report, lib = metadata.run(self.repo.root, self.repo.registries())
        return report, lib

    def codes(self):
        return {f.code for f in self.validate()[0].findings}

    def test_fixture_is_valid_in_both_layouts(self):
        report, lib = self.validate()
        self.assertEqual(report.findings, [],
                         [f.render() for f in report.findings])
        self.assertEqual(len(lib.records), 5)
        self.assertEqual(len(lib.relationships), 1)

    def test_duplicate_id(self):
        self.repo.write("metadata/authors/author-al-farabi.yaml", {
            "id": "author-al-farabi", "name": "Dup",
            "civilization": "Islamic Civilization", "disciplines": ["x"]})
        self.assertIn("duplicate-id", self.codes())

    def test_prefix_must_match_type(self):
        self.repo.write("metadata/books/author-wrong.yaml", {
            "id": "author-wrong", "title": "T", "author_id":
            "author-ibn-sina", "publication_year": 1, "language": "Arabic",
            "civilization": "X", "genre": ["Y"]})
        self.assertIn("prefix", self.codes())

    def test_missing_required_field(self):
        self.repo.write("metadata/books/book-no-author.yaml", {
            "id": "book-no-author", "title": "T", "publication_year": 1,
            "language": "Arabic", "civilization": "X", "genre": ["Y"]})
        self.assertIn("schema", self.codes())

    def test_dangling_reference(self):
        self.repo.write("metadata/books/book-orphan.yaml", {
            "id": "book-orphan", "title": "T", "author_id":
            "author-nobody", "publication_year": 1, "language": "Arabic",
            "civilization": "X", "genre": ["Y"]})
        self.assertIn("dangling-reference", self.codes())

    def test_shard_file_name_must_match_id(self):
        self.repo.write("metadata/books/wrong-name.yaml", {
            "id": "book-right", "title": "T", "author_id":
            "author-ibn-sina", "publication_year": 1, "language": "Arabic",
            "civilization": "X", "genre": ["Y"]})
        self.assertIn("file-name", self.codes())

    def test_tags_must_come_from_vocabulary(self):
        data = self.repo.read_yaml("metadata/books/book-muqaddimah.yaml")
        data["tags"].append("not-a-tag")
        self.repo.write("metadata/books/book-muqaddimah.yaml", data)
        self.assertIn("tag", self.codes())

    def test_deprecated_needs_replacement(self):
        data = self.repo.read_yaml("metadata/books/book-muqaddimah.yaml")
        data["status"] = "deprecated"
        self.repo.write("metadata/books/book-muqaddimah.yaml", data)
        self.assertIn("deprecation", self.codes())


class ReadingPathTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)

    def run_paths(self):
        lib = metadata.load(self.repo.root, self.repo.registries())
        return {f.code for f in paths.run(lib).findings}

    def test_size_order_and_membership(self):
        self.repo.write("metadata/reading-paths.yaml", [{
            "id": "path-islamic-history", "title": "Islamic History",
            "level": "Beginner",
            "included_books": ["book-muqaddimah", "book-the-book-of-healing",
                               "book-missing"]}])
        self.repo.write("metadata/relationships/order.yaml", [{
            "source": "book-the-book-of-healing",
            "relationship": "prerequisite_of", "target": "book-muqaddimah",
            "confidence": "tentative"}])
        codes = self.run_paths()
        self.assertTrue({"path-size", "prerequisite-order", "missing-work",
                         "outcomes"} <= codes, codes)


if __name__ == "__main__":
    unittest.main()
