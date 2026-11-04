"""r23: boot replay falls back to .lastgood when the profile is missing, unreadable or rejected."""
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "modules/carplay/runtime/cpvc/cpvc_config.sh"
GOOD = "preset.id=mibr_legacy" + chr(10) + "navigation.compass=yes" + chr(10)
BAD = "preset.id=mibr_legacy" + chr(10) + "navigation.compass=JUNK" + chr(10)
HELPER = """#!/bin/sh
# stub native helper: batch --input FILE --layer temp  accepts only files without JUNK
[ "$1" = batch ] || exit 2
grep -q JUNK "$3" && exit 3
cp "$3" "$APPROOT/temp-loaded"
exit 0
"""


@unittest.skipUnless(shutil.which("sh") and shutil.which("ksh") or shutil.which("bash"), "needs a shell")
@unittest.skipUnless(SCRIPT.is_file(), "Research-only CPVC compatibility script is omitted from the public source tree")
class LastGoodFallback(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpvc-fb-")
        root = Path(self.tmp.name)
        self.base = root / "mibr"  # the single MIBR root, selected through MIBR_ROOT
        (self.base / "config/cockpit").mkdir(parents=True)
        (self.base / "bin").mkdir()
        self.bin = root / "stubs"
        self.bin.mkdir()
        helper = self.base / "bin" / "alt111-settings"
        helper.write_text(HELPER)
        helper.chmod(helper.stat().st_mode | stat.S_IXUSR)
        for name in ("mount", "sync"):
            p = self.bin / name
            p.write_text("#!/bin/sh" + chr(10) + "exit 0" + chr(10))
            p.chmod(0o755)
        (root / "enabled").write_text("1")
        text = SCRIPT.read_text()
        text = text.replace("export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/armle/bin:/mnt/app/armle/usr/bin",
                            "export PATH=" + str(self.bin) + ":/usr/bin:/bin")
        text = text.replace("ENABLED=$MIBR_ROOT/config/features/mibr-cpvc.enabled", "ENABLED=" + str(root / "enabled"))
        text = text.replace("/tmp/mibr-cpvc-profile-ready", str(root / "ready"))
        text = text.replace("/tmp/mibr-alt111-settings.journal", str(root / "journal"))
        text = text.replace('ZOOM=/tmp/mibr-alt111-zoom-v1.enabled', 'ZOOM=' + str(root / "zoom"))
        self.script = root / "cpvc_config.sh"
        self.script.write_text(text)
        self.root = root
        self.profile = self.base / "config/cockpit" / "cpvc-r5.profile"
        self.lastgood = self.base / "config/cockpit" / "cpvc-r5.profile.lastgood"

    def tearDown(self):
        self.tmp.cleanup()

    def run_replay(self):
        env = {"PATH": str(self.bin) + ":/usr/bin:/bin", "APPROOT": str(self.root), "MIBR_ROOT": str(self.base)}
        shell = shutil.which("ksh") or shutil.which("bash") or "sh"
        return subprocess.run([shell, str(self.script), "_boot-replay"], env=env, capture_output=True,
                              text=True, timeout=20)

    def test_good_profile_is_untouched(self):
        self.profile.write_text(GOOD)
        self.lastgood.write_text(GOOD)
        run = self.run_replay()
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("CPVC_BOOT_PROFILE=PASS", run.stdout)
        self.assertNotIn("FALLBACK", run.stdout)
        self.assertEqual(self.profile.read_text(), GOOD)

    def test_rejected_profile_is_replaced_by_lastgood(self):
        self.profile.write_text(BAD)
        self.lastgood.write_text(GOOD)
        run = self.run_replay()
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("CPVC_BOOT_PROFILE_FALLBACK=LASTGOOD_RESTORED", run.stdout)
        self.assertIn("CPVC_BOOT_PROFILE=PASS", run.stdout)
        self.assertEqual(self.profile.read_text(), GOOD)
        self.assertEqual((self.base / "config/cockpit" / "cpvc-r5.profile.corrupt").read_text(), BAD)
        self.assertTrue((self.root / "ready").exists())

    def test_missing_profile_uses_lastgood(self):
        self.lastgood.write_text(GOOD)
        run = self.run_replay()
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(self.profile.read_text(), GOOD)

    def test_both_broken_still_fails_closed(self):
        self.profile.write_text(BAD)
        self.lastgood.write_text(BAD)
        run = self.run_replay()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("CPVC_BOOT_PROFILE=FAIL_TRANSACTION", run.stdout)
        self.assertFalse((self.root / "ready").exists())
        self.assertEqual(self.profile.read_text(), BAD)

    def test_no_lastgood_fails_closed(self):
        self.profile.write_text(BAD)
        run = self.run_replay()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("FALLBACK=NO_LASTGOOD", run.stdout)


if __name__ == "__main__":
    unittest.main()
