"""Actual host-C source regression for MIBR language persistence and GPS demo."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
from public_paths import NATIVE


class NativeDemo(unittest.TestCase):
    def build_and_run(self, test_source, sources):
        compiler = shutil.which(os.environ.get("CC", "cc"))
        if compiler is None:
            self.skipTest("host C compiler not installed")
        with tempfile.TemporaryDirectory(prefix="mibr-native-test-") as tmp:
            binary = Path(tmp) / "regression"
            cmd = [compiler, "-O1", "-std=c99", "-Wall", "-Wextra", "-Werror",
                   "-I", str(NATIVE), str(HERE / test_source)]
            cmd += [str(NATIVE / name) for name in sources]
            cmd += ["-o", str(binary)]
            compile_result = subprocess.run(cmd, text=True, capture_output=True)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            result = subprocess.run([binary], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("PASS", result.stdout)

    def test_live_nmea_without_new_sender(self):
        self.build_and_run("gps_demo_host_test.c", ["mibr_gps_demo.c"])

    def test_atomic_language_preference(self):
        self.build_and_run("menu_language_host_test.c", ["mibr_menu_language.c"])

    def test_atomic_durable_switches(self):
        self.build_and_run("durable_switch_host_test.c", ["mibr_durable_switch.c"])

    def test_shared_app_rw_lease(self):
        self.build_and_run("app_rw_lease_host_test.c", ["mibr_app_rw_lease.c"])

    def test_embeddable_original_owner_module_compiles(self):
        compiler = shutil.which(os.environ.get("CC", "cc"))
        if compiler is None:
            self.skipTest("host C compiler not installed")
        with tempfile.TemporaryDirectory(prefix="mibr-owner-test-") as tmp:
            for name in ("mibr_gps_demo_owner.c", "mibr_gps_demo_ipc.c"):
                cmd = [compiler, "-std=c99", "-Wall", "-Wextra", "-Werror",
                       "-I", str(NATIVE), "-c", str(NATIVE / name),
                       "-o", str(Path(tmp) / (name + ".o"))]
                result = subprocess.run(cmd, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
