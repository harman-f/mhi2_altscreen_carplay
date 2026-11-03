"""Host test of control/scripts/mibr-menu.ksh: stores the menu file from the SD card."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
SCRIPT = HERE / "modules" / "broker" / "runtime" / "mibr-control" / "mibr-menu.ksh"


class MenuScript(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.src = self.tmp / "mibr-menu.txt"
        self.dir = self.tmp / "config"
        self.dir.mkdir()
        self.env = dict(os.environ, MIBR_MENU_SRC=str(self.src), MIBR_MENU_DIR=str(self.dir), MIBR_VIEW_NOMOUNT="1")

    def run_script(self, *args):
        sh = shutil.which("ksh") or shutil.which("bash")
        p = subprocess.run([sh, str(SCRIPT), *args], capture_output=True, text=True, env=self.env, timeout=20)
        return p.returncode, p.stdout.strip().splitlines()[-1]

    def test_stores_the_file(self):
        self.src.write_bytes(b"MIBR_MENU/1\nx\n")
        self.assertEqual(self.run_script("load"), (0, "result=OK"))
        self.assertEqual((self.dir / "mibr-menu.conf").read_bytes(), b"MIBR_MENU/1\nx\n")
        self.assertEqual([p.name for p in self.dir.iterdir()], ["mibr-menu.conf"])

    def test_no_file_keeps_the_stored_one(self):
        (self.dir / "mibr-menu.conf").write_bytes(b"old")
        self.assertEqual(self.run_script("load"), (1, "result=NO_FILE"))
        self.assertEqual((self.dir / "mibr-menu.conf").read_bytes(), b"old")

    def test_size_limit(self):
        (self.dir / "mibr-menu.conf").write_bytes(b"old")
        self.src.write_bytes(b"x" * 16385)
        self.assertEqual(self.run_script("load"), (1, "result=TOO_LARGE"))
        self.src.write_bytes(b"")
        self.assertEqual(self.run_script("load"), (1, "result=TOO_LARGE"))
        self.assertEqual((self.dir / "mibr-menu.conf").read_bytes(), b"old")

    def test_write_failure_leaves_nothing(self):
        self.src.write_bytes(b"new")
        self.env["MIBR_MENU_DIR"] = str(self.tmp / "absent")
        self.assertEqual(self.run_script("load"), (1, "result=WRITE_FAILED"))

    def test_usage(self):
        self.assertEqual(self.run_script("other"), (1, "result=USAGE"))


if __name__ == "__main__":
    unittest.main()
