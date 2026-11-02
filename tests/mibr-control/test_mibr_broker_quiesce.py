"""Installer quiesce helper: bound identity, graceful TERM and fail-closed PID parsing."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

from public_paths import NATIVE, ROOT
BOUND_PROCESS_INCLUDE = ROOT / "src/native/parity-session"
CC = shutil.which(os.environ.get("CC", "cc")) or shutil.which("gcc")
SOURCE = NATIVE / "mibr_broker_quiesce.c"


@unittest.skipUnless(CC and os.name == "posix" and hasattr(os, "geteuid") and os.geteuid() == 0,
                     "requires root-owned PID fixtures, POSIX C compiler and pidfd support")
@unittest.skipUnless(SOURCE.is_file() and (BOUND_PROCESS_INCLUDE / "bound_process.h").is_file(),
                     "broker-quiesce source and bound-process interface are unavailable")
class BrokerQuiesceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="mibr-quiesce-build-")
        cls.root = Path(cls.tmp.name)
        cls.bin = cls.root / "mibr-broker-quiesce"
        subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror",
                        "-DALT111_SETTINGS_TEST", "-I", str(BOUND_PROCESS_INCLUDE),
                        str(SOURCE), "-o", str(cls.bin)],
                       check=True, capture_output=True, text=True)
        cls.good_exe = cls.root / "mibr-v3-service"
        cls.good_src = cls.root / "service.c"
        cls.good_src.write_text("#include <unistd.h>\nint main(void){for(;;)sleep(1);}\n")
        subprocess.run([CC, str(cls.good_src), "-o", str(cls.good_exe)],
                       check=True, capture_output=True, text=True)
        cls.stubborn_src = cls.root / "stubborn.c"
        cls.stubborn_src.write_text(
            "#include <signal.h>\n#include <unistd.h>\n"
            "int main(void){signal(SIGTERM,SIG_IGN);for(;;)sleep(1);}\n")
        cls.stubborn_exe = cls.root / "mibr-v3-service-stubborn"
        subprocess.run([CC, str(cls.stubborn_src), "-o", str(cls.stubborn_exe)],
                       check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mibr-quiesce-case-")
        self.pidfile = Path(self.temp.name) / "service.pid"

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, expected, code, check=False):
        args = [str(self.bin), str(self.pidfile), str(expected)]
        if check:
            args.append("--check")
        result = subprocess.run(args,
                                capture_output=True, text=True, timeout=12)
        self.assertEqual(result.returncode, code, result.stderr)
        return result

    def write_pid(self, pid):
        self.pidfile.write_text(str(pid) + "\n")
        self.pidfile.chmod(0o666)  # target volatile mount reports this mode

    def test_expected_executable_receives_term_and_exits(self):
        process = subprocess.Popen([str(self.good_exe), "30"])
        try:
            self.write_pid(process.pid)
            result = self.invoke(self.good_exe, 0)
            self.assertIn("BROKER_QUIESCED", result.stdout)
            self.assertEqual(process.wait(timeout=2), -15)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=2)

    def test_wrong_executable_is_not_signalled(self):
        process = subprocess.Popen(["sleep", "30"])
        try:
            self.write_pid(process.pid)
            self.invoke(self.good_exe, 4)
            self.assertIsNone(process.poll())
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=2)

    def test_check_verifies_exact_live_executable_without_signalling(self):
        process = subprocess.Popen([str(self.good_exe), "30"])
        try:
            self.write_pid(process.pid)
            result = self.invoke(self.good_exe, 0, check=True)
            self.assertIn("BROKER_IDENTITY_VERIFIED", result.stdout)
            self.assertIsNone(process.poll(), "--check must leave the verified process running")
            mismatch = self.invoke(self.stubborn_exe, 4, check=True)
            self.assertIn("MIBR_QUIESCE_IDENTITY_MISMATCH", mismatch.stderr)
            self.assertIsNone(process.poll(), "identity failure must not signal")
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=2)

    def test_malformed_pidfile_fails_closed(self):
        self.pidfile.write_text("not-a-pid\n")
        self.pidfile.chmod(0o666)
        self.invoke(self.good_exe, 2)

    def test_stale_well_formed_pid_is_harmless(self):
        process = subprocess.Popen(["sleep", "1"])
        pid = process.pid
        process.wait(timeout=3)
        self.write_pid(pid)
        result = self.invoke(self.good_exe, 0)
        self.assertIn("BROKER_ALREADY_EXITED", result.stdout)

    def test_unresponsive_exact_executable_times_out_without_forced_kill(self):
        process = subprocess.Popen([str(self.stubborn_exe)])
        try:
            self.write_pid(process.pid)
            started = time.monotonic()
            self.invoke(self.stubborn_exe, 6)
            elapsed = time.monotonic() - started
            self.assertGreaterEqual(elapsed, 9.5)
            self.assertLess(elapsed, 11.5)
            self.assertIsNone(process.poll(), "helper must not force-kill after timeout")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=2)


if __name__ == "__main__":
    unittest.main()
