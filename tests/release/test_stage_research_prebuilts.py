"""Negative and positive gates for private Research-prebuilt staging (synthetic only)."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/release"))
SPEC = importlib.util.spec_from_file_location(
    "stage_research_prebuilts", ROOT / "tools/release/stage_research_prebuilts.py"
)
stage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage)


class ResearchPrebuiltTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        (self.repo / "native").mkdir()
        (self.repo / "native/src.c").write_text("int main(void) {return 0;}\n")
        self.git("add", "native/src.c")
        self.git("commit", "-qm", "native")
        self.native = self.root / "staged-native"
        self.hmi = self.root / "staged-hmi"
        self.archive = self.root / "reference.zip"
        self.lock = {
            "schema": 1,
            "reference_version": "1.5.0-beta.11",
            "reviewed_public_source_commit": self.git("rev-parse", "HEAD"),
            "research_commit": "a" * 40,
            "profiles": ["skoda-mu1440-p4526", "seat-mu1409-p4708",
                         "seat-mu1447-p4709"],
            "git_objects": {"native": self.git("rev-parse", "HEAD:native")},
        }
        binary_rows, sha_rows = [], []
        with zipfile.ZipFile(self.archive, "w", zipfile.ZIP_DEFLATED) as z:
            for rel, member in sorted(stage.native_map().items()):
                content = "b\x7fELF synthetic " + rel.encode()
                digest = hashlib.sha256(content).hexdigest()
                z.writestr(member, content)
                inside = member[len(stage.PREFIX):]
                sha_rows.append(digest + "  " + inside)
                binary_rows.append({"path": inside, "sha256": digest})
            ext_path = stage.PREFIX + "common/menu/bin/" + stage.EXTENDER
            ext = b"synthetic JAR"
            z.writestr(ext_path, ext)
            sha_rows.append(hashlib.sha256(ext).hexdigest() + "  " +
                            ext_path[len(stage.PREFIX):])
            meta = {
                "version": self.lock["reference_version"], "complete": True,
                "profiles": self.lock["profiles"], "binaries": binary_rows,
                "native_build": {"source_commit": "b" * 40,
                                 "compiler": "synthetic", "image_source": "synthetic"},
            }
            z.writestr(stage.PREFIX + "package.json", json.dumps(meta))
            z.writestr(stage.PREFIX + "PACKAGE.sha256", "\n".join(sha_rows) + "\n")
        self.lock["archive_sha256"] = stage.sha256_file(self.archive)

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.repo), *args], check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    def test_stage_and_independent_receipt_verification(self):
        stage.stage(self.repo, self.archive, self.native, self.hmi, self.lock)
        verified = stage.verify_staged(self.repo, self.native, self.hmi, self.lock)
        self.assertEqual(verified["reference_archive_sha256"], self.lock["archive_sha256"])
        self.assertEqual(verified["built_from"], "b" * 40)

    def test_modified_source_rejected_even_with_same_archive(self):
        (self.repo / "native/src.c").write_text("int main(void) {return 1;}\n")
        with self.assertRaisesRegex(stage.PrebuiltError, "STALE"):
            stage.stage(self.repo, self.archive, self.native, self.hmi, self.lock)

    def test_corrupt_reference_archive_rejected(self):
        self.archive.write_bytes(self.archive.read_bytes() + b"tampered")
        with self.assertRaisesRegex(stage.PrebuiltError, "SHA256_MISMATCH"):
            stage.stage(self.repo, self.archive, self.native, self.hmi, self.lock)

    def test_modified_stage_binary_rejected(self):
        stage.stage(self.repo, self.archive, self.native, self.hmi, self.lock)
        rel = sorted(stage.native_map())[0]
        (self.native / rel).write_bytes(b"tampered")
        with self.assertRaisesRegex(stage.PrebuiltError, "FILE_CHANGED"):
            stage.verify_staged(self.repo, self.native, self.hmi, self.lock)

    def test_modified_receipt_provenance_rejected(self):
        stage.stage(self.repo, self.archive, self.native, self.hmi, self.lock)
        (self.native / "SOURCE_COMMIT.txt").write_text("c" * 40 + "\n")
        with self.assertRaisesRegex(stage.PrebuiltError, "PROVENANCE_CHANGED"):
            stage.verify_staged(self.repo, self.native, self.hmi, self.lock)


if __name__ == "__main__":
    unittest.main()
