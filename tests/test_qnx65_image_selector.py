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
            "QNX65_LEGACY_REBUILD_ALLOWED": "0",
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

    def test_missing_reference_fails_without_rebuild(self):
        result = self.check_status("", 15)
        self.assertIn("QNX_IMAGE_NOT_CONFIGURED=FAIL", result.stderr)

    def test_mutable_tag_is_rejected(self):
        result = self.check_status("ghcr.io/example/toolchain:latest", 10)
        self.assertIn("QNX_IMAGE_REF=FAIL", result.stderr)

    def test_malformed_digest_is_rejected(self):
        result = self.check_status("ghcr.io/example/toolchain@sha256:bad", 10)
        self.assertIn("QNX_IMAGE_REF=FAIL", result.stderr)


if __name__ == "__main__":
    unittest.main()
