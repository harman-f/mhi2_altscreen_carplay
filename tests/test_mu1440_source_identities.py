"""Regression tests for the branch-scoped MU1440 QNX identity contract."""

import hashlib
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.verify_mu1440_source_identities import (  # noqa: E402
    select_expected_identities,
    verify_identity_files,
)


RELEASE_REF = "main"
CANDIDATE_REF = "work/suggestui-root-advertisement-review-20261025"
RELEASE_PIN = "a" * 64
CANDIDATE_PIN = "b" * 64


class SourceIdentityContractTests(unittest.TestCase):
    def setUp(self):
        self.production = {
            "libaltscreen111.so": RELEASE_PIN,
            "alt111-settings": "c" * 64,
        }
        self.overrides = {CANDIDATE_REF: {"libaltscreen111.so": CANDIDATE_PIN}}

    def test_main_keeps_the_production_library_pin(self):
        profile, expected = select_expected_identities(RELEASE_REF, self.production, self.overrides)
        self.assertEqual(profile, "production-baseline")
        self.assertEqual(expected["libaltscreen111.so"], RELEASE_PIN)

    def test_exact_review_branch_uses_candidate_pin_and_keeps_other_pins(self):
        profile, expected = select_expected_identities(CANDIDATE_REF, self.production, self.overrides)
        self.assertEqual(profile, "review-candidate")
        self.assertEqual(expected["libaltscreen111.so"], CANDIDATE_PIN)
        self.assertEqual(expected["alt111-settings"], self.production["alt111-settings"])

    def test_unlisted_branch_uses_production_and_rejects_candidate_binary(self):
        profile, expected = select_expected_identities("work/another-branch", self.production, self.overrides)
        self.assertEqual(profile, "production-baseline")
        self.assertEqual(expected["libaltscreen111.so"], RELEASE_PIN)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "libaltscreen111.so").write_bytes(b"candidate")
            (output / "alt111-settings").write_bytes(b"settings")
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                rc = verify_identity_files(
                    output,
                    "work/another-branch",
                    {"libaltscreen111.so": hashlib.sha256(b"release").hexdigest(),
                     "alt111-settings": hashlib.sha256(b"settings").hexdigest()},
                    {},
                )
            self.assertEqual(rc, 1)

    def test_review_branch_still_rejects_unrelated_artifact_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "libaltscreen111.so").write_bytes(b"candidate")
            (output / "alt111-settings").write_bytes(b"tampered settings")
            production = {
                "libaltscreen111.so": hashlib.sha256(b"release").hexdigest(),
                "alt111-settings": hashlib.sha256(b"settings").hexdigest(),
            }
            overrides = {
                CANDIDATE_REF: {"libaltscreen111.so": hashlib.sha256(b"candidate").hexdigest()}
            }
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                rc = verify_identity_files(output, CANDIDATE_REF, production, overrides)
            self.assertEqual(rc, 1)

    def test_override_cannot_weaken_another_component_pin(self):
        with self.assertRaisesRegex(ValueError, "may not change identities"):
            select_expected_identities(
                CANDIDATE_REF,
                self.production,
                {CANDIDATE_REF: {"alt111-settings": "d" * 64}},
            )

    def test_missing_source_ref_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "explicit non-empty"):
            select_expected_identities("", self.production, self.overrides)


if __name__ == "__main__":
    unittest.main()
