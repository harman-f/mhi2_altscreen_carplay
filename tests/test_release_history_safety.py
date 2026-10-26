"""Regression gate: retired developer publisher cannot mutate tags/releases."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/release-mu1440-aid10.yml"
POLICY = ROOT / "docs/build/RELEASE_HISTORY_POLICY.md"
HISTORY = ROOT / "release/CURRENT.md"


class ReleaseHistorySafety(unittest.TestCase):
    def test_retired_workflow_has_no_write_capability(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("Legacy developer publisher retired", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotRegex(workflow, r"(?m)^\s*push\s*:")
        self.assertNotRegex(workflow, r"(?im)\bgh\s+release\s+(?:create|delete|edit|upload)\b")
        self.assertNotRegex(workflow, r"(?im)\bgit\s+push\b")
        self.assertNotRegex(workflow, r"(?im)\bgh\s+api\b")
        self.assertNotIn("actions/upload-release-asset", workflow.lower())
        self.assertNotIn("softprops/action-gh-release", workflow.lower())

    def test_history_and_immutable_policy_are_distinct(self):
        policy = POLICY.read_text(encoding="utf-8")
        history = HISTORY.read_text(encoding="utf-8")
        self.assertIn("retired", policy.lower())
        self.assertIn("immutable", policy.lower())
        self.assertIn("withdrawn", history.lower())
        self.assertIn("mu1440-aid10-dev-current", history)
        self.assertIn("not an installable public 1.3.2", history.lower())


if __name__ == "__main__":
    unittest.main()
