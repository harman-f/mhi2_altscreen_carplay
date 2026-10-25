"""Guard against destructive cleanup of historical MU1440 releases.

The legacy 'dev-current' alias has its own historical behavior. This gate
covers all *unrelated* release/tag identities, which must never be deleted
as a side effect of updating that alias.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/release-mu1440-aid10.yml"


class ReleaseHistorySafety(unittest.TestCase):
    def test_legacy_release_has_no_global_cleanup(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('TAG: mu1440-aid10-dev-current', text)
        self.assertIn('gh release create "$TAG"', text)
        self.assertNotIn('gh release list', text)
        self.assertNotIn('gh release delete "$OLD"', text)
        self.assertNotIn('git ls-remote --tags', text)
        self.assertNotIn('git push origin ":refs/tags/$OLD"', text)
        self.assertNotRegex(text, r'gh\s+release\s+delete\s+\$\{?OLD')
        self.assertNotRegex(text, r'gh\s+release\s+delete\s+--.*\$\{?OLD')

    def test_legacy_release_requires_publication_checks(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('Final release audit', text)
        self.assertIn('Assemble self-contained SD-root package', text)
        self.assertIn('sha256sum "$ZIP_NAME"', text)


if __name__ == "__main__":
    unittest.main()
