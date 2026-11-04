#!/usr/bin/env python3
"""Host-only fail-closed smoke tests for the QNX CI image selector."""
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "ci_qnx65_image.sh"


class TestQnxImageSelector(unittest.TestCase):
    def check_status(self, image, expected):
        env = dict(os.environ)
        env.update({
            "QNX65_VERIFIED_IMAGE": image,
        })
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT)], env=env, cwd=ROOT,
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, expected, result.stderr)
        return result

    def test_shell_syntax(self):
        result = subprocess.run(["/bin/bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_committed_default_digest(self):
        self.assertEqual(
            (ROOT / "tools/qnx65-image.lock").read_text().strip(),
            "ghcr.io/harman-f/mhi2-qnx65-armv7@sha256:20d7d2bb16d6718d204afc7714b0e73227651935a9981a8bd2e2087cef48dd0d",
        )
        self.assertIn("PIN_FILE=tools/qnx65-image.lock", SCRIPT.read_text())
        self.assertNotIn("QNX65_LEGACY_REBUILD_ALLOWED", SCRIPT.read_text())

    def test_unapproved_but_valid_digest_fails(self):
        result = self.check_status("ghcr.io/other/toolchain@sha256:" + "0" * 64, 17)
        self.assertIn("QNX_IMAGE_PIN_MISMATCH=FAIL", result.stderr)

    def test_mutable_tag_is_rejected(self):
        result = self.check_status("ghcr.io/example/toolchain:latest", 10)
        self.assertIn("QNX_IMAGE_REF=FAIL", result.stderr)

    def test_malformed_digest_is_rejected(self):
        result = self.check_status("ghcr.io/example/toolchain@sha256:bad", 10)
        self.assertIn("QNX_IMAGE_REF=FAIL", result.stderr)


if __name__ == "__main__":
    unittest.main()
