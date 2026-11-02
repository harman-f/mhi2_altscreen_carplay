"""r8 Java MibrV3Session against the real native MIBR/3 host service (PR102).

Needs the host builds that mibr-control-api-v3-offline.yml produces:
MIBR_V3_NATIVE_SERVICE_BIN (mibr_v3_service.c, -DALT111_SETTINGS_TEST) and
MIBR_PINNED_ALT111_CLI (original settings_cli.c), plus javac/java. Host only.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parent
JAVA = APP / "java/de/mibr/hmi"
BIN = os.environ.get("MIBR_V3_NATIVE_SERVICE_BIN")
CLI = os.environ.get("MIBR_PINNED_ALT111_CLI")
SOURCES = ("MibrSettingsCatalog", "MibrMenuDefinition", "MibrI18n", "MibrDraftChoiceModel",
           "MibrPopupEditorModel", "MibrScalingState", "MibrV3Protocol", "MibrV3Client", "MibrV3Session")


@unittest.skipUnless(BIN and CLI and shutil.which("javac"), "needs native host service, CLI and javac")
class NativeE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="v3-e2e-")
        cls.classes = Path(cls.tmp.name) / "classes"
        cls.classes.mkdir()
        srcs = [str(JAVA / (n + ".java")) for n in SOURCES] + [str(HERE / "MibrV3NativeE2E.java")]
        subprocess.run(["javac", "--release", "8", "-nowarn", "-d", str(cls.classes)] + srcs,
                       check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_mode(self, mode):
        base = Path(tempfile.mkdtemp(prefix=mode + "-", dir=self.tmp.name))
        (base / "temp").mkdir()
        (base / "persistent").mkdir()
        secret = base / "hmi.secret"
        secret.write_text("c" * 64 + "\n")
        secret.chmod(0o600)
        env = {**os.environ, "ALT111_SETTINGS_TEMP_ROOT": str(base / "temp"),
               "ALT111_SETTINGS_PERSISTENT_ROOT": str(base / "persistent"),
               "MIBR_V3_HOST_SCALING_PATH": str(base / "persistent" / "display-scaling.conf")}
        if mode in ("durable", "deferred"):
            profile = base / "cpvc-r5.profile"
            shutil.copyfile(APP.parents[2] / "cpvc-r5/CPVC-Install/profile/default.profile", profile)
            env["MIBR_V3_HOST_PROFILE_PATH"] = str(profile)
            if mode == "deferred":
                env["MIBR_V3_PERSIST_DELAY_MS"] = "4000"
                env["MIBR_V3_PERSIST_MAX_MS"] = "8000"
            subprocess.run([CLI, "batch", "--input", str(profile), "--layer", "temp"],
                           env=env, check=True, capture_output=True, text=True, timeout=5)
        service = subprocess.Popen([BIN, "--port", "0", "--secret-file", str(secret)], env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            ready = service.stdout.readline().strip()
            self.assertTrue(ready.startswith("MIBR_V3_HOST_SERVICE_PORT="), ready)
            port = ready.split("=", 1)[1]
            run = subprocess.run(["java", "-cp", str(self.classes), "de.mibr.hmi.MibrV3NativeE2E",
                                  port, str(secret), mode], capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("MIBR_V3_NATIVE_E2E_PASS mode=" + mode, run.stdout)
            if mode == "deferred":
                # Reply came before the flush; the profile follows after the quiet period.
                import re, time
                m = re.search(r"maneuver (\S+)->(\S+)", run.stdout)
                self.assertTrue(m, run.stdout)
                old = "navigation.maneuver=" + m.group(1) + "\n"
                new = "navigation.maneuver=" + m.group(2) + "\n"
                self.assertIn(old, profile.read_text(), "profile still old right after the reply")
                end = time.time() + 15
                while time.time() < end and new not in profile.read_text():
                    time.sleep(0.2)
                self.assertIn(new, profile.read_text(), "coalesced flush wrote the profile")
                self.assertTrue((profile.parent / "cpvc-r5.profile.lastgood").is_file(), "backup kept")
            if mode == "durable":
                self.assertNotIn("navigation.maneuver=top\n", profile.read_text())
                temp = (base / "temp").rglob("*")
                self.assertTrue(any(p.is_file() for p in temp), "SET materialized the TEMP layer")
                marker = base / "temp" / "mibr-alt111-gen2-reacquire"
                self.assertTrue(marker.is_file() and marker.read_text() == "request\n",
                                "durable PRESENTATION SET requested one GEN2 SHOW (marker)")
            return run.stdout
        finally:
            service.terminate()
            service.wait(timeout=5)
            service.stdout.close()
            service.stderr.close()

    def test_readonly_service(self):
        self.run_mode("readonly")

    def test_durable_host_service(self):
        self.run_mode("durable")

    def test_deferred_write_behind(self):
        self.run_mode("deferred")


if __name__ == "__main__":
    unittest.main()
