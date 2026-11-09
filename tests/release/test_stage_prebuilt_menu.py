"""Regression tests for release-time use of pinned profile menu artifacts."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "tools/release/stage_prebuilt_menu.py"
SPEC = importlib.util.spec_from_file_location("stage_prebuilt_menu", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class MenuPrebuiltFreshnessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.run_git("init", "-q")
        self.run_git("config", "user.email", "test@example.invalid")
        self.run_git("config", "user.name", "Test")
        (self.repo / "menu").mkdir()
        (self.repo / "menu/Adapter.java").write_text("class Adapter {}\n", encoding="utf-8")
        self.run_git("add", "menu/Adapter.java")
        self.run_git("commit", "-qm", "initial menu sources")
        self.baseline = self.run_git("rev-parse", "HEAD").strip()

    def run_git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            text=True, check=True, capture_output=True,
        ).stdout

    def changed(self):
        return module.changed_paths(self.repo, self.baseline, ("menu",))

    def test_unchanged_public_inputs_pass(self):
        self.assertEqual(self.changed(), [])

    def test_committed_java_changes_block_stale_reference(self):
        (self.repo / "menu/Adapter.java").write_text("class Adapter { int v; }\n")
        self.run_git("add", "menu/Adapter.java")
        self.run_git("commit", "-qm", "modify Java")
        self.assertIn("menu/Adapter.java", self.changed())

    def test_uncommitted_or_new_java_blocks_reference(self):
        (self.repo / "menu/Adapter.java").write_text("class Adapter { int v; }\n")
        self.assertTrue(any("uncommitted" in p for p in self.changed()))
        (self.repo / "menu/Other.java").write_text("class Other {}\n")
        self.assertTrue(any("Other.java" in p for p in self.changed()))

    def test_unrelated_document_change_does_not_invalidate_menu(self):
        (self.repo / "README.md").write_text("docs only\n")
        self.run_git("add", "README.md")
        self.run_git("commit", "-qm", "docs")
        self.assertEqual(self.changed(), [])


if __name__ == "__main__":
    unittest.main()
