import importlib.util
import subprocess
import sys
import unittest

from helpers import REPO

SCRIPT = REPO / "scripts" / "check-permissions.py"


def load_script():
    spec = importlib.util.spec_from_file_location("check_permissions",
                                                  SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CheckPermissionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cp = load_script()

    def test_blank_template_yields_no_agent(self):
        template = (REPO / ".github" / "pull_request_template.md"
                    ).read_text(encoding="utf-8")
        self.assertIsNone(self.cp.agent_from_body(template))
        self.assertIsNone(self.cp.agent_from_body("- agent_id:\n"
                                                  "- workflow_id: x\n"))

    def test_agent_line_is_read(self):
        body = "## AI Provenance\n\n- agent_id: `daily-word`\n- run_id: 1\n"
        self.assertEqual(self.cp.agent_from_body(body), "daily-word")
        self.assertEqual(self.cp.agent_from_body("agent_id: metadata"),
                         "metadata")

    def test_owner_paths_come_from_codeowners(self):
        patterns = self.cp.owner_patterns(REPO)
        self.assertIn("scripts/", patterns)
        self.assertIn("README.md", patterns)
        self.assertTrue(self.cp.needs_owner("scripts/bayan/router.py",
                                            patterns))
        self.assertTrue(self.cp.needs_owner("README.md", patterns))
        self.assertFalse(self.cp.needs_owner("metadata/books/book-x.yaml",
                                             patterns))

    def test_missing_agent_is_a_usage_error(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(REPO),
             "metadata/books/book-x.yaml"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("agent_id", result.stderr)

    def test_tier_check(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(REPO),
             "--agent", "daily-word", "canon/top-100-books/README.md"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("out-of-tier", result.stdout)


if __name__ == "__main__":
    unittest.main()
