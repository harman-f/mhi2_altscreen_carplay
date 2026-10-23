"""Host test of control/scripts/mibr-engine.ksh against a copy of the real iap2.cfg (r43 candidate)."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
SCRIPT = HERE / "runtime" / "mibr-control" / "mibr-engine.ksh"
CFG = "[location]\nenable=yes\n\n[vehicle]\nengine=gas\n\n[power]\nengine=gas\n"


def run(sh, tmp, *args):
    env = dict(os.environ, MIBR_ENGINE_CFG=str(tmp / "iap2.cfg"), MIBR_ENGINE_BOOT=str(tmp / "boot"),
               MIBR_ENGINE_LOCK=str(tmp / "lock"), MIBR_ENGINE_NOMOUNT="1")
    p = subprocess.run([sh, str(SCRIPT), *args], capture_output=True, text=True, env=env)
    out = dict(l.split("=", 1) for l in p.stdout.splitlines() if "=" in l)
    return p.returncode, out


def run_with_mock_mount(sh, tmp, *args, fail_uw=False, fail_ur=False, fail_cp=False, fail_stage=False):
    system = tmp / "system"
    cfg = system / "etc" / "mm" / "iap2.cfg"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(CFG)
    bindir = tmp / "mockbin"
    bindir.mkdir()
    mount = bindir / "mount"
    mount.write_text("""#!/bin/sh
echo "$1 $2" >> "$MIBR_ENGINE_MOUNT_LOG"
case "$1" in
  -uw)
    for f in "$MIBR_ENGINE_CFG".engine.*; do
      [ -e "$f" ] && exit 72
    done
    [ "$MIBR_ENGINE_FAIL_STAGE" = 1 ] && mkdir "$MIBR_ENGINE_CFG.engine.$PPID"
    [ "$MIBR_ENGINE_FAIL_UW" = 1 ] && exit 1
    ;;
  -ur)
    if [ "$MIBR_ENGINE_FAIL_STAGE" != 1 ]; then
      for f in "$MIBR_ENGINE_CFG".engine.*; do
        [ -e "$f" ] && exit 73
      done
    fi
    [ "$MIBR_ENGINE_FAIL_UR" = 1 ] && exit 1
    ;;
esac
exit 0
""")
    mount.chmod(0o755)
    if fail_cp:
        cp = bindir / "cp"
        cp.write_text("#!/bin/sh\nexit 1\n")
        cp.chmod(0o755)
    env = dict(os.environ, MIBR_ENGINE_CFG=str(cfg), MIBR_ENGINE_MOUNT=str(system),
               MIBR_ENGINE_BOOT=str(tmp / "boot"), MIBR_ENGINE_LOCK=str(tmp / "lock"),
               MIBR_ENGINE_MOUNT_LOG=str(tmp / "mount.log"), MIBR_ENGINE_NOMOUNT="0",
               MIBR_ENGINE_FAIL_UW="1" if fail_uw else "0",
               MIBR_ENGINE_FAIL_UR="1" if fail_ur else "0",
               MIBR_ENGINE_FAIL_STAGE="1" if fail_stage else "0",
               PATH=str(bindir) + os.pathsep + os.environ.get("PATH", ""))
    p = subprocess.run([sh, str(SCRIPT), *args], capture_output=True, text=True, env=env)
    out = dict(l.split("=", 1) for l in p.stdout.splitlines() if "=" in l)
    log = (tmp / "mount.log").read_text().splitlines()
    return p.returncode, out, log, cfg


class EngineScript(unittest.TestCase):
    def shells(self):
        result = []
        for shell in (shutil.which("bash"), shutil.which("ksh"), shutil.which("sh")):
            if not shell or shell in result:
                continue
            try:
                subprocess.run([shell, "-c", "exit 0"], capture_output=True, timeout=3, check=True)
            except (OSError, subprocess.SubprocessError):
                continue
            result.append(shell)
        return result

    def test_get_set_roundtrip_and_pending(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                tmp = Path(d)
                (tmp / "iap2.cfg").write_text(CFG)
                before = (tmp / "iap2.cfg").read_text()
                rc, o = run(sh, tmp, "get")
                self.assertEqual((rc, o["engine"], o["announced"], o["pending"], o["result"]), (0, "gas", "gas", "0", "OK"))
                rc, o = run(sh, tmp, "set", "diesel")
                self.assertEqual((rc, o["engine"], o["announced"], o["pending"]), (0, "diesel", "gas", "1"))
                after = (tmp / "iap2.cfg").read_text()
                self.assertEqual(before.replace("[vehicle]\nengine=gas", "[vehicle]\nengine=diesel"), after)
                self.assertEqual(len(before.splitlines()), len(after.splitlines()))
                rc, o = run(sh, tmp, "set", "gas")          # back to the announced value: nothing pending
                self.assertEqual((rc, o["engine"], o["pending"]), (0, "gas", "0"))
                self.assertEqual(before, (tmp / "iap2.cfg").read_text())
                self.assertEqual([p.name for p in tmp.iterdir() if ".engine" in p.name], [])

    def test_rejects_bad_value_and_layout(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                tmp = Path(d)
                (tmp / "iap2.cfg").write_text(CFG)
                for bad in ("petrol", "gas;rm -rf /", "", "Diesel"):
                    rc, o = run(sh, tmp, "set", bad)
                    self.assertEqual((rc, o["result"]), (1, "BAD_VALUE"))
                self.assertEqual(CFG, (tmp / "iap2.cfg").read_text())
                (tmp / "iap2.cfg").write_text("[location]\nenable=yes\n")
                rc, o = run(sh, tmp, "set", "diesel")
                self.assertEqual((rc, o["result"]), (1, "NO_VEHICLE_BLOCK"))
                self.assertEqual("[location]\nenable=yes\n", (tmp / "iap2.cfg").read_text())

    def test_engine_line_outside_vehicle_untouched(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                tmp = Path(d)
                (tmp / "iap2.cfg").write_text("[other]\nengine=gas\n[vehicle]\nenable=yes\nengine=gas\n[power]\nengine=gas\n")
                rc, o = run(sh, tmp, "set", "cng")
                self.assertEqual((rc, o["engine"]), (0, "cng"))
                self.assertEqual((tmp / "iap2.cfg").read_text(),
                                 "[other]\nengine=gas\n[vehicle]\nenable=yes\nengine=cng\n[power]\nengine=gas\n")

    def test_lock_is_a_pid_file_stale_is_stolen_live_blocks(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                tmp = Path(d)
                (tmp / "iap2.cfg").write_text(CFG)
                (tmp / "lock").write_text("999999\n")          # dead pid: stale, stolen
                rc, o = run(sh, tmp, "get")
                self.assertEqual((rc, o["result"]), (0, "OK"))
                self.assertFalse((tmp / "lock").exists())
                (tmp / "lock").write_text(str(os.getpid()) + "\n")   # live pid: busy
                rc, o = run(sh, tmp, "set", "diesel")
                self.assertEqual((rc, o["result"]), (1, "BUSY"))
                self.assertEqual(CFG, (tmp / "iap2.cfg").read_text())

    def test_mounts_rw_before_staging_and_restores_ro_after_write_failure(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                tmp = Path(d)
                rc, o, log, cfg = run_with_mock_mount(sh, tmp, "set", "diesel", fail_cp=True)
                self.assertEqual((rc, o["result"]), (1, "WRITE_FAILED"))
                self.assertEqual(log, [f"-uw {cfg.parents[2]}", f"-ur {cfg.parents[2]}"])
                self.assertEqual(CFG, cfg.read_text())
                self.assertEqual([], list(cfg.parent.glob("iap2.cfg.engine.*")))

    def test_failed_rw_remount_still_requests_ro_without_staging(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                tmp = Path(d)
                rc, o, log, cfg = run_with_mock_mount(sh, tmp, "set", "diesel", fail_uw=True)
                self.assertEqual((rc, o["result"]), (1, "REMOUNT_FAILED"))
                self.assertEqual(log, [f"-uw {cfg.parents[2]}", f"-ur {cfg.parents[2]}"])
                self.assertEqual(CFG, cfg.read_text())
                self.assertEqual([], list(cfg.parent.glob("iap2.cfg.engine.*")))

    def test_staging_creation_failure_still_requests_ro(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                tmp = Path(d)
                rc, o, log, cfg = run_with_mock_mount(sh, tmp, "set", "diesel", fail_stage=True)
                self.assertEqual((rc, o["result"]), (1, "NO_TMP"))
                self.assertEqual(log, [f"-uw {cfg.parents[2]}", f"-ur {cfg.parents[2]}"])
                self.assertEqual(CFG, cfg.read_text())
                blockers = list(cfg.parent.glob("iap2.cfg.engine.*"))
                self.assertEqual(len(blockers), 1)
                self.assertTrue(blockers[0].is_dir())
                blockers[0].rmdir()

    def test_ro_restore_failure_is_reported_after_write_failure(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                tmp = Path(d)
                rc, o, log, _ = run_with_mock_mount(sh, tmp, "set", "diesel", fail_cp=True, fail_ur=True)
                self.assertEqual((rc, o["result"]), (1, "RO_RESTORE_FAILED"))
                self.assertEqual(log[-1].split()[0], "-ur")


if __name__ == "__main__":
    unittest.main()
