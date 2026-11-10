"""Regression tests for fail-closed profile HMI source fingerprints."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "tools/release/verify_menu_source_lock.py"
SPEC = importlib.util.spec_from_file_location("verify_menu_source_lock", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class MenuSourceLockTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.write("modules/menu/source/java/Menu.java", "class Menu {}\n")
        self.write("settings/registry.json", "{}\n")
        for root in module.HMI_ROOTS:
            profile = root.split("/")[2]
            self.write(f"modules/profiles/{profile}/profile.json", "{}\n")
            self.write(f"{root}/README.md", "HMI source\n")
            self.write(f"{root}/java/Profile.java", "class Profile {}\n")
            # This exact legacy binary path is deliberately outside the lock.
            self.write(f"{root}/prebuilt/MIBR-CarPlay.jar", "synthetic jar\n")
        self.git("add", ".")
        self.git("commit", "-qm", "baseline")
        self.lock = self.make_lock()

    def write(self, path, content):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.repo), *args], check=True, text=True,
            capture_output=True,
        ).stdout.strip()

    def make_lock(self):
        objects = {
            "modules/menu/source": self.git("rev-parse", "HEAD:modules/menu/source"),
            "settings/registry.json": self.git("rev-parse", "HEAD:settings/registry.json"),
        }
        for root in module.HMI_ROOTS:
            profile = root.split("/")[2]
            profile_path = f"modules/profiles/{profile}/profile.json"
            objects[profile_path] = self.git("rev-parse", "HEAD:" + profile_path)
            paths = self.git("ls-tree", "-r", "--name-only", "HEAD", "--", root).splitlines()
            omitted = root + "/" + module.EXCLUDED_JAR
            self.assertIn(omitted, paths)
            self.assertEqual(len(paths) - 1, sum(path != omitted for path in paths))
            for path in paths:
                if path != omitted:
                    objects[path] = self.git("rev-parse", "HEAD:" + path)
        return {"schema": 2, "hmi_roots": list(module.HMI_ROOTS), "git_objects": objects}

    def test_unchanged_sources_pass_and_only_exact_prebuilt_is_unlocked(self):
        self.assertEqual(module.verify(self.repo, self.lock)["status"], "PASS")
        path = module.HMI_ROOTS[0] + "/prebuilt/MIBR-CarPlay.jar"
        self.write(path, "different bytes\n")
        self.git("add", path)
        self.git("commit", "-qm", "replace excluded private release input")
        # The exact JAR path is excluded from the source freshness lock.
        self.assertEqual(module.verify(self.repo, self.lock)["status"], "PASS")

    def test_committed_java_change_blocks_stale_lock(self):
        path = module.HMI_ROOTS[0] + "/java/Profile.java"
        self.write(path, "class Profile { int changed; }\n")
        self.git("add", path)
        self.git("commit", "-qm", "modify Java")
        with self.assertRaisesRegex(module.LockError, "MENU_SOURCE_LOCK_STALE"):
            module.verify(self.repo, self.lock)

    def test_new_tracked_java_file_blocks_path_set(self):
        path = module.HMI_ROOTS[1] + "/java/NewProfile.java"
        self.write(path, "class NewProfile {}\n")
        self.git("add", path)
        self.git("commit", "-qm", "add Java source")
        with self.assertRaisesRegex(module.LockError, "MENU_SOURCE_HMI_PATH_SET_MISMATCH"):
            module.verify(self.repo, self.lock)

    def test_uncommitted_existing_java_change_blocks_lock(self):
        self.write(module.HMI_ROOTS[0] + "/java/Profile.java", "class Profile { int changed; }\n")
        with self.assertRaisesRegex(module.LockError, "MENU_SOURCE_LOCK_STALE"):
            module.verify(self.repo, self.lock)

    def test_unrelated_documentation_does_not_invalidate_lock(self):
        self.write("README.md", "docs only\n")
        self.git("add", "README.md")
        self.git("commit", "-qm", "unrelated docs")
        self.assertEqual(module.verify(self.repo, self.lock)["status"], "PASS")

    def test_untracked_hmi_file_blocks_lock(self):
        self.write(module.HMI_ROOTS[2] + "/java/Untracked.java", "class Untracked {}\n")
        with self.assertRaisesRegex(module.LockError, "MENU_SOURCE_LOCK_STALE"):
            module.verify(self.repo, self.lock)

    def test_missing_profile_fails_closed(self):
        root = module.HMI_ROOTS[2]
        self.git("rm", "-qr", root)
        self.git("commit", "-qm", "remove profile HMI")
        with self.assertRaisesRegex(module.LockError, "MENU_SOURCE_PROFILE_MISSING"):
            module.verify(self.repo, self.lock)

    def test_missing_locked_profile_metadata_fails_closed(self):
        path = "modules/profiles/seat-mu1447-p4709/profile.json"
        self.git("rm", path)
        self.git("commit", "-qm", "remove profile metadata")
        with self.assertRaisesRegex(module.LockError, "MENU_SOURCE_LOCK_STALE"):
            module.verify(self.repo, self.lock)

    def test_old_lock_schema_is_rejected(self):
        old = json.loads(json.dumps(self.lock))
        old["schema"] = 1
        with self.assertRaisesRegex(module.LockError, "MENU_SOURCE_LOCK_SCHEMA_UNSUPPORTED"):
            module.verify(self.repo, old)

    def test_lock_missing_one_hmi_file_is_rejected(self):
        altered = json.loads(json.dumps(self.lock))
        altered["git_objects"].pop(module.HMI_ROOTS[0] + "/java/Profile.java")
        with self.assertRaisesRegex(module.LockError, "MENU_SOURCE_HMI_PATH_SET_MISMATCH"):
            module.verify(self.repo, altered)


if __name__ == "__main__":
    unittest.main()
