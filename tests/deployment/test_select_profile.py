"""installer/select-profile.ksh: SHA-256 selector with train cross-check. Host-only, fake files."""
import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "installer/select-profile.ksh"
LIST = ROOT / "installer/config/profiles.list"
SHELLS = [s for s in (shutil.which("sh"), shutil.which("dash"), shutil.which("ksh"), shutil.which("bash")) if s]
SHELLS = sorted(set(os.path.realpath(s) for s in SHELLS))
FW = "MHI2_ER_TEST_FAKE"


class SelectProfile(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        # fake sha tool on PATH: prints the digest of the file content, plus file name like sha256sum
        bindir = self.tmp / "bin"
        bindir.mkdir()
        tool = bindir / "sha256sum"
        tool.write_text('#!/bin/sh\n[ -r "$1" ] || exit 1\nprintf "%s  %s\\n" "$(cat "$1" | python3 -c '
                        "'import sys,hashlib;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'"
                        ')" "$1"\n')
        tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
        self.env = {"PATH": str(bindir) + ":" + os.environ["PATH"]}
        self.jxe = self.tmp / "lsd.jxe"
        self.jxe.write_bytes(b"fake-jxe-A")
        self.h = hashlib.sha256(b"fake-jxe-A").hexdigest()

    def lst(self, *lines):
        p = self.tmp / "profiles.list"
        p.write_text("# generated\n" + "\n".join(lines) + "\n")
        return p

    def run_sel(self, shell, lst, *extra, jxe=None):
        args = [shell, str(SCRIPT), str(lst), "--jxe", str(jxe or self.jxe)] + list(extra)
        return subprocess.run(args, capture_output=True, text=True, env=self.env)

    def each(self, fn):
        for sh in SHELLS:
            with self.subTest(shell=sh):
                fn(sh)

    def test_match(self):
        l = self.lst("%s p-one %s 1" % (self.h, FW), "%s p-two %s 1" % ("1" * 64, FW))
        def f(sh):
            r = self.run_sel(sh, l, "--train", FW)
            self.assertEqual((r.returncode, r.stdout), (0, "PROFILE=p-one\n"))
        self.each(f)

    def test_train_mismatch_or_missing(self):
        l = self.lst("%s p-one %s 1" % (self.h, FW))
        def f(sh):
            self.assertEqual(self.run_sel(sh, l, "--train", "OTHER").returncode, 3)
            r = self.run_sel(sh, l)
            self.assertEqual(r.returncode, 3)
            self.assertEqual(r.stdout, "")
            self.assertEqual(self.run_sel(sh, l, "--train", "").returncode, 3)
        self.each(f)

    def test_empty_expected_needs_no_train(self):
        l = self.lst("%s p-one - 1" % self.h)
        self.each(lambda sh: self.assertEqual(self.run_sel(sh, l).stdout, "PROFILE=p-one\n"))

    def test_unknown(self):
        l = self.lst("%s p-two %s 1" % ("2" * 64, FW))
        self.each(lambda sh: self.assertEqual(self.run_sel(sh, l, "--train", FW).returncode, 4))

    def test_ambiguous(self):
        l = self.lst("%s p-one %s 1" % (self.h, FW), "%s p-two %s 1" % (self.h, FW))
        def f(sh):
            r = self.run_sel(sh, l, "--train", FW)
            self.assertEqual((r.returncode, r.stdout), (5, ""))
        self.each(f)

    def test_disabled(self):
        l = self.lst("%s p-one %s 0" % (self.h, FW))
        def f(sh):
            r = self.run_sel(sh, l, "--train", FW)
            self.assertEqual((r.returncode, r.stdout), (6, ""))
        self.each(f)

    def test_unreadable(self):
        l = self.lst("%s p-one %s 1" % (self.h, FW))
        def f(sh):
            self.assertEqual(self.run_sel(sh, l, jxe=self.tmp / "absent").returncode, 2)
            self.assertEqual(self.run_sel(sh, self.tmp / "nolist").returncode, 2)
            self.assertEqual(self.run_sel(sh, self.lst("garbage line")).returncode, 2)
            self.assertEqual(self.run_sel(sh, l, "--bogus").returncode, 2)
        self.each(f)

    def test_broken_hash_tool(self):
        l = self.lst("%s p-one %s 1" % (self.h, FW))
        (self.tmp / "bin/sha256sum").write_text("#!/bin/sh\necho notahash x\n")
        self.each(lambda sh: self.assertEqual(self.run_sel(sh, l, "--train", FW).returncode, 2))

    def test_read_only(self):
        l = self.lst("%s p-one %s 1" % (self.h, FW))
        before = sorted(p.name for p in self.tmp.iterdir())
        self.each(lambda sh: self.run_sel(sh, l, "--train", FW))
        self.assertEqual(before, sorted(p.name for p in self.tmp.iterdir()))
        self.assertEqual(self.jxe.read_bytes(), b"fake-jxe-A")

    def test_no_bashisms(self):
        text = SCRIPT.read_text()
        for bad in ("[[", "local ", "function ", "<<<", "echo -e", "readlink -f", "=~"):
            self.assertNotIn(bad, text)

    def test_committed_list_selects_enabled_only(self):
        # real generated list: every digest line parses and P4708 is disabled
        rows = [l.split() for l in LIST.read_text().splitlines() if l and not l.startswith("#")]
        self.assertEqual(len(rows), len({r[0] for r in rows}))
        self.assertTrue(all(len(r) == 4 and r[3] in ("0", "1") for r in rows))
        self.assertEqual({r[1]: r[3] for r in rows}["seat-mu1409-p4708"], "0")


if __name__ == "__main__":
    unittest.main()
