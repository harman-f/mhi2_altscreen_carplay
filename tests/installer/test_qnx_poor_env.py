"""Installer tests in a QNX-like host environment (MU1440 target shell rules).

The first real QNX run (2026-11-05) failed on limits that a Linux host hides:
no printf (builtin or binary), no sed/find/sort/cut/tr/date, awk outside the login PATH,
and ksh splitting only expansion results on IFS. These tests re-run the installer and
migration suites under mksh (pdksh line, printf is not a builtin) with a PATH that holds
only the tools declared in NEED_TOOLS (installer/lib/mibr-common.ksh) plus awk and the
python3 behind the synthetic sha256 helper. Any undeclared external command fails here.
See docs/testing/MU1440_QNX_SHELL_COMPATIBILITY.md.

Set MIBR_TEST_KSH to a pdksh/mksh binary when it is not on PATH; without one the
emulated suites are skipped (the static gate below always runs).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_mibr_install as tmi
import test_migrate_root as tmr

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from check_mu1440_target_shell import scan  # noqa: E402

_ksh = os.environ.get("MIBR_TEST_KSH") or "mksh"
KSH = shutil.which(_ksh)
INSTALLER_SCRIPTS = sorted(list((REPO / "installer").glob("*.ksh")) + list((REPO / "installer/lib").glob("*.ksh")))
# Everything the beta package runs on the unit: installer plus module runtime scripts.
TARGET_SCRIPTS = INSTALLER_SCRIPTS + sorted(p for p in (REPO / "modules").glob("*/runtime/**/*")
                                            if p.suffix in (".sh", ".ksh") and p.is_file())
# Absent or unproven on the MU1440; must never be reachable from the emulated PATH.
FORBIDDEN = ("printf", "sed", "tr", "find", "sort", "uniq", "cut", "date", "tee", "sha256sum",
             "basename", "dirname", "wc", "od", "xargs", "stat", "readlink", "mktemp")


def need_tools():
    text = (REPO / "installer/lib/mibr-common.ksh").read_text()
    m = re.search(r'^NEED_TOOLS="([^"]+)"', text, re.M)
    assert m, "NEED_TOOLS manifest missing in mibr-common.ksh"
    return m.group(1).split()


def poor_bin(base):
    d = Path(base) / "qnx-bin"
    d.mkdir()
    for t in need_tools() + ["awk", "python3"]:
        src = shutil.which(t)
        assert src, "host lacks " + t
        (d / t).symlink_to(src)
    (d / "sh").symlink_to(KSH)
    (d / "ksh").symlink_to(KSH)
    return str(d)


class StaticGate(unittest.TestCase):
    def test_target_shell_gate_passes(self):
        problems = []
        for p in TARGET_SCRIPTS:
            problems += scan(p)
        self.assertEqual(problems, [])

    def test_manifest_has_no_forbidden_tool(self):
        self.assertEqual(sorted(set(need_tools()) & set(FORBIDDEN)), [])

    def test_no_tmp_subdirectory_default(self):
        # MU1440 /tmp (= /dev/shmem) holds flat files only: /tmp may be the last fallback, never first.
        for p in INSTALLER_SCRIPTS:
            for line in p.read_text().splitlines():
                if re.search(r'mkdir[^\n]*\$\{TMPDIR:-/tmp\}', line):
                    self.fail("%s: mkdir under ${TMPDIR:-/tmp}: %s" % (p.name, line.strip()))


@unittest.skipUnless(KSH, "no mksh/pdksh (set MIBR_TEST_KSH)")
class ShellPrimitives(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qnxpoor-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bin = poor_bin(self.tmp)

    def ksh(self, script, path=None):
        env = {"PATH": path or self.bin, "HOME": str(self.tmp), "MIBR_TOOL_DIRS": self.bin}
        return subprocess.run([KSH, "-c", script], env=env, capture_output=True, text=True, timeout=30)

    def test_printf_absent_in_emulation(self):
        r = self.ksh("printf x")
        self.assertNotEqual(r.returncode, 0)

    def test_out_is_verbatim(self):
        probe = r"-n a\tb\\c %s $x"
        r = self.ksh('PKG=/nonexistent; . %s/installer/lib/mibr-common.ksh; echo "ok=$OUT_OK impl=$OUT_IMPL"; '
                     'out \'%s\'' % (REPO, probe))
        self.assertEqual(r.returncode, 0, r.stderr)
        first, second = r.stdout.split("\n")[:2]
        self.assertTrue(first.startswith("ok=1"), r.stdout)
        self.assertEqual(second, probe)

    def test_find_cmd_splits_search_path(self):
        tooldir = self.tmp / "armle-usr-bin"
        tooldir.mkdir()
        tool = tooldir / "mibr-probe-tool"
        tool.write_text("#!/bin/sh\nexit 0\n")
        tool.chmod(0o755)
        # the entry point replaces PATH (M.I.B. bootstrap); the unit dirs come from TOOL_DIRS
        r = subprocess.run([KSH, "-c", "PKG=/nonexistent; . %s/installer/lib/mibr-common.ksh; find_cmd mibr-probe-tool"
                            % REPO], env={"PATH": self.bin, "HOME": str(self.tmp),
                                          "MIBR_TOOL_DIRS": "/nonexistent:%s:%s" % (tooldir, self.bin)},
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(r.stdout.strip(), str(tool))

    def test_unit_tool_dirs_are_searched(self):
        # On the unit awk lives outside the login PATH; find_cmd must reach it via TOOL_DIRS.
        tooldir = self.tmp / "armle-usr-bin"
        tooldir.mkdir()
        (tooldir / "awk").symlink_to(shutil.which("awk"))
        env = {"PATH": "/nonexistent", "MIBR_TOOL_DIRS": "/nonexistent2:%s" % tooldir, "HOME": str(self.tmp)}
        r = subprocess.run([KSH, "-c", "PKG=/nonexistent; . %s/installer/lib/mibr-common.ksh; find_cmd awk" % REPO],
                           env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.stdout.strip(), str(tooldir / "awk"), r.stderr)

    def test_mkwork_falls_back_when_tmpdir_unusable(self):
        # (permission bits do not stop root, so model "unusable" as a non-directory)
        ro = self.tmp / "not-a-dir"
        ro.write_text("")
        r = self.ksh('TMPDIR=%s; PKG=/nonexistent; . %s/installer/lib/mibr-common.ksh; mkwork && echo "W=$W"; '
                     '[ -n "$W" ] && rm -rf "$W"' % (ro, REPO))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("W=", r.stdout)
        self.assertNotIn(str(ro), r.stdout)


def _poor(cls):
    """Same test cases, run by mksh with the QNX-poor PATH."""
    def setUp(self):
        cls.setUp(self)
        self.poor_path = poor_bin(self.tmp)

    attrs = {"setUp": setUp, "shell": KSH or "mksh"}
    if hasattr(cls, "run_inst"):
        def env(self, extra=None):
            e = cls.env(self, extra)
            e["PATH"] = self.poor_path
            e["MIBR_TOOL_DIRS"] = self.poor_path
            return e
        attrs["env"] = env
    else:
        def run_cmd(self, cmd, id_="T1", extra=None, env=None, mapf=None):
            e = dict(env or {})
            e["PATH"] = self.poor_path
            e["MIBR_TOOL_DIRS"] = self.poor_path
            return cls.run_cmd(self, cmd, id_=id_, extra=extra, env=e, mapf=mapf)
        attrs["run_cmd"] = run_cmd
    return unittest.skipUnless(KSH, "no mksh/pdksh (set MIBR_TEST_KSH)")(
        type("QnxPoor_" + cls.__name__, (cls,), attrs))


QnxPoor_TestInstall = _poor(tmi.TestInstall)
QnxPoor_TestInterrupted = _poor(tmi.TestInterrupted)
QnxPoor_TestUninstallRollback = _poor(tmi.TestUninstallRollback)
QnxPoor_TestManifestMode = _poor(tmi.TestManifestMode)
QnxPoor_Migrate = _poor(tmr.Cases_sh)

if __name__ == "__main__":
    unittest.main()
