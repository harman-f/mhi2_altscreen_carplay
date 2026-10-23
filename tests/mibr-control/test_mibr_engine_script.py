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


if __name__ == "__main__":
    unittest.main()
