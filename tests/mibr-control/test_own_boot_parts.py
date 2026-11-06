"""Host tests for the boot entry, the RGI launcher wrapper and the P1 boot probe source.

The scripts hard-code unit paths, so each test copies the real script into a temporary tree and rewrites only those
path prefixes, like test_cpvc_lastgood_fallback.py. Host shell only; not QNX or vehicle evidence.
"""
import os
import shutil
import stat
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from public_paths import ROOT, RUNTIME

BOOT = RUNTIME / "boot.ksh"
GUARD = RUNTIME / "boot-guard.ksh"
CPVC = ROOT / "modules/carplay/runtime/cpvc/cpvc_config.sh"
WRAPPER = ROOT / "modules/navigation/runtime/mm-ipod-rgi.sh"
PROBE = ROOT / "modules/menu/source/extender-p1"
SH = shutil.which("bash") or shutil.which("sh")


def put(path, text, mode=0o755):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(mode)


class Syntax(unittest.TestCase):
    def test_scripts_parse(self):
        for script in (BOOT, GUARD, CPVC, WRAPPER):
            with self.subTest(script=script.name):
                self.assertTrue(script.read_text().startswith("#!/bin/"))
                self.assertEqual(subprocess.run([SH, "-n", str(script)]).returncode, 0)
                if shutil.which("ksh"):
                    self.assertEqual(subprocess.run(["ksh", "-n", str(script)]).returncode, 0)

    def test_boot_scripts_have_no_local_or_private_paths(self):
        for script in (BOOT, GUARD, CPVC, WRAPPER):
            text = script.read_text()
            for bad in ("/home/", "C:\\", "E:\\", "/Users/", "github.com"):
                self.assertNotIn(bad, text, script.name)


class BootEntry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mibr-boot-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.app = self.root / "mnt/app"
        text = BOOT.read_text().replace("/tmp/", str(self.root) + "/").replace("/mnt/app", str(self.app))
        text = text.replace("/bin/ksh", SH)
        self.script = self.root / "boot.ksh"
        put(self.script, text)
        self.m = self.app / "root/mibr"
        self.a = self.m / "scripts"
        self.calls = self.root / "calls"
        for name in ("direct_ts_auto_start.sh", "cpvc_config.sh", "parity_drive_supervisor.sh"):
            put(self.a / name, '#!/bin/sh\necho "%s $*" >> "%s"\n' % (name, self.calls))
        put(self.a / "mibr-v3-boot.ksh", '#!/bin/sh\necho v3 >> "%s"\n' % self.calls)

    def run_boot(self):
        r = subprocess.run([SH, str(self.script)], capture_output=True, text=True, env={"PATH": os.environ["PATH"]})
        done = self.calls.read_text().split("\n") if self.calls.exists() else []
        return r, sorted(x for x in done if x)

    def test_disabled_switch_starts_nothing(self):
        (self.m / "state/boot").mkdir(parents=True)
        (self.m / "state/boot/disabled").write_text("x")
        r, calls = self.run_boot()
        self.assertEqual((r.returncode, r.stdout.strip(), calls), (0, "MIBR_KIT_BOOT=DISABLED", []))

    def test_legacy_kill_switch_is_not_read(self):
        # E4: no second permanent kill switch. A leftover mibr-kit/disabled must not stop the start.
        (self.app / "root/mibr-kit").mkdir(parents=True)
        (self.app / "root/mibr-kit/disabled").write_text("x")
        r, _ = self.run_boot()
        time.sleep(0.3)
        self.assertIn("MIBR_KIT_BOOT=DONE", r.stdout)
        self.assertNotIn("DISABLED", r.stdout)

    def test_without_cpvc_marker_supervisor_starts_alone(self):
        r, _ = self.run_boot()
        time.sleep(0.3)
        calls = sorted(x for x in self.calls.read_text().split("\n") if x)
        self.assertEqual(r.returncode, 0)
        self.assertIn("MIBR_KIT_BOOT=DONE", r.stdout)
        self.assertIn("direct_ts_auto_start.sh ", calls)
        self.assertIn("parity_drive_supervisor.sh ", calls)
        self.assertNotIn("cpvc_config.sh _boot-replay", calls)
        self.assertIn("v3", calls)

    def test_cpvc_replay_failure_keeps_stock_and_still_exits_zero(self):
        (self.m / "config/features").mkdir(parents=True, exist_ok=True)
        (self.m / "config/features/mibr-cpvc.enabled").write_text("1")
        put(self.a / "cpvc_config.sh", "#!/bin/sh\nexit 24\n")
        r, calls = self.run_boot()
        self.assertEqual(r.returncode, 0)
        self.assertEqual((self.root / "mibr-cpvc-boot.state").read_text().strip(), "CPVC_BOOT=PROFILE_FAILED_STOCK_ONLY")
        self.assertNotIn("parity_drive_supervisor.sh ", calls)

    def test_cpvc_replay_success_starts_supervisor_after_replay(self):
        (self.m / "config/features").mkdir(parents=True, exist_ok=True)
        (self.m / "config/features/mibr-cpvc.enabled").write_text("1")
        r, _ = self.run_boot()
        time.sleep(0.3)
        calls = [x for x in self.calls.read_text().split("\n") if x]
        self.assertLess(calls.index("cpvc_config.sh _boot-replay"), calls.index("parity_drive_supervisor.sh "))


class RgiWrapper(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mibr-rgi-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.app = self.root / "mnt/app"
        self.shm = self.root / "shmem"
        self.shm.mkdir()
        self.etc = self.root / "etc/mm"
        put(self.etc / "iap2.cfg", "[vehicle]\nengine=gas\n", 0o644)
        self.out = self.root / "out"
        text = WRAPPER.read_text().replace("/mnt/app", str(self.app)).replace("/dev/shmem", str(self.shm))
        text = text.replace("/etc/mm/iap2.cfg", str(self.etc / "iap2.cfg"))
        text = text.replace("PATH=/proc/boot:/bin:/usr/bin:", "PATH=/bin:/usr/bin:")
        self.script = self.root / "mm-ipod-rgi"
        put(self.script, text)
        put(self.app / "armle/usr/sbin/mm-ipod",
            '#!/bin/sh\necho "args=$* preload=${LD_PRELOAD:-none}" > "%s"\n' % self.out)
        put(self.app / "root/mibr/bin/mibr-rgi", '#!/bin/sh\necho helper > "%s.helper"\n' % self.out)

    def run_wrapper(self, *args, preload=None):
        env = {"PATH": os.environ["PATH"]}
        if preload:
            env["LD_PRELOAD"] = preload
        r = subprocess.run([SH, str(self.script), *args], capture_output=True, text=True, env=env)
        time.sleep(0.2)
        return r

    def test_enabled_start_preloads_library_and_uses_exact_ram_copy(self):
        r = self.run_wrapper("-a", "b", preload="/lib/other.so")
        self.assertEqual(r.returncode, 0, r.stderr)
        lib = str(self.app / "root/mibr/bin/libmibr_rgi_ipod.so")
        self.assertEqual(self.out.read_text().strip(), "args=-a b preload=%s:/lib/other.so" % lib)
        self.assertEqual((self.shm / "mibr-rgi-iap2.cfg").read_bytes(), (self.etc / "iap2.cfg").read_bytes())
        self.assertTrue(Path(str(self.out) + ".helper").exists())

    def test_stock_start_after_rejection_kill_switch_or_ident_section(self):
        for arrange in (lambda: (self.shm / "mibr-rgi-rejected").write_text(""),
                        lambda: (self.app / "root/mibr/state/boot").mkdir(parents=True) or (self.app / "root/mibr/state/boot/disabled").write_text(""),
                        lambda: (self.etc / "iap2.cfg").write_text("[ident]\nx=1\n")):
            with self.subTest():
                for p in (self.shm / "mibr-rgi-rejected", self.app / "root/mibr/state/boot/disabled", self.out,
                          Path(str(self.out) + ".helper")):
                    p.unlink(missing_ok=True)
                put(self.etc / "iap2.cfg", "[vehicle]\nengine=gas\n", 0o644)
                arrange()
                self.run_wrapper()
                self.assertEqual(self.out.read_text().strip(), "args= preload=none")
                self.assertFalse(Path(str(self.out) + ".helper").exists())

    def test_legacy_kill_switch_is_not_read(self):
        (self.app / "root/mibr-kit").mkdir(parents=True)
        (self.app / "root/mibr-kit/disabled").write_text("")
        self.run_wrapper()
        self.assertIn("preload=", self.out.read_text())
        self.assertNotIn("preload=none", self.out.read_text())
        self.assertTrue(Path(str(self.out) + ".helper").exists())

    def test_missing_stock_config_aborts_without_exec(self):
        (self.etc / "iap2.cfg").unlink()
        self.assertEqual(self.run_wrapper().returncode, 1)
        self.assertFalse(self.out.exists())


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"), "needs a host JDK")
class ProbeHostTest(unittest.TestCase):
    def test_lifecycle_host_test_passes_and_status_record_is_bounded(self):
        r = subprocess.run(["sh", str(PROBE / "tests/run_host.sh")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("P1_HOST_TEST_PASS", r.stdout)

    def test_probe_source_has_no_oem_or_network_or_thread_use(self):
        src = "".join(p.read_text() for p in (PROBE / "java").rglob("*.java"))
        for banned in ("java.net", "new Thread", "Class.forName", "System.load", "Runtime.getRuntime", "ProcessBuilder"):
            self.assertNotIn(banned, src)
        self.assertEqual(sorted(p.name for p in (PROBE / "java").rglob("*.java")),
                         ["MibrExtenderCore.java", "MibrStartupHook.java"])


if __name__ == "__main__":
    unittest.main()
