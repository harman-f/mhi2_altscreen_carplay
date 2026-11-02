"""Runs Java host tests for the MIBR/3 route, binding, and socket clients."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[1]
H = P / "java/de/mibr/hmi"
T = P / "tests"
ROOT = P.parents[2]
GENERATED = Path(tempfile.mkdtemp(prefix="mibr-v3-generated-"))
MAIN = ("MibrV3Protocol", "MibrV3Client", "MibrV3Bootstrap", "MibrV3Session", "MibrV3Route",
        "MibrI18n", "MibrPopupEditorModel", "MibrScalingState", "MibrDraftChoiceModel", "MibrVersionInfo",
        "MibrCarPlayMenuModel", "MibrGpsDemoState", "MibrVdataDiag", "MibrEngineState", "MibrViewState", "MibrElementSpec", "MibrElementEngine", "MibrElementTree", "MibrCanonicalElementMenu",
        "MibrDurableSwitch", "MibrPlatformDefaults", "MibrSafeArea", "MibrMenuCatalog", "MibrMenuFunctions", "MibrMenuLayout", "MibrExpert")


class V3JavaHost(unittest.TestCase):
    def test_route_binding_socket(self):
        javac, java = shutil.which("javac"), shutil.which("java")
        if not javac or not java:
            self.skipTest("JDK required")
        generated = subprocess.run([
            shutil.which("python3") or "python3", str(P / "generate_catalog.py"),
            "--registry", str(ROOT / "settings/registry.json"),
            "--menu", str(P / "menu-definition.json"), "--out-dir", str(GENERATED),
        ], capture_output=True, text=True)
        self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
        out = Path(tempfile.mkdtemp(prefix="mibr-v3-host-"))
        sources = [str(H / (n + ".java")) for n in MAIN] + [
                   str(GENERATED / "MibrMenuDefinition.java"),
                   str(GENERATED / "MibrSettingsCatalog.java")] + [str(T / (n + ".java")) for n in
                   ("MibrV3RouteTest", "MibrV3BindingTest", "MibrV3SocketTest", "MibrScalingBindingTest", "MibrCarPlayMenuModelTest", "MibrAdvancedOptionsTest")]
        run = subprocess.run([javac, "-encoding", "UTF-8", "-source", "8", "-target", "8", "-nowarn", "-d", str(out)] + sources,
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        for cls, marker in (("MibrV3RouteTest", "MIBR_V3_ROUTE_PASS"),):
            run = subprocess.run([java, "-Dmibr.menu.standard=" + str(ROOT / "tools/menu-editor/standard-menu.txt"),
                                  "-cp", str(out), "de.mibr.hmi." + cls], capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn(marker, run.stdout)
        run = subprocess.run([java, "-Dmibr.menu.standard=" + str(ROOT / "tools/menu-editor/standard-menu.txt"),
                              "-cp", str(out), "de.mibr.hmi.MibrCarPlayMenuModelTest"], capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("MIBR_CARPLAY_MENU_MODEL_PASS", run.stdout)
        run = subprocess.run([java, "-Dmibr.menu.standard=" + str(ROOT / "tools/menu-editor/standard-menu.txt"),
                              "-cp", str(out), "de.mibr.hmi.MibrAdvancedOptionsTest"], capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("MIBR_ADVANCED_OPTIONS_HOST_PASS", run.stdout)
        for cls in ("MibrV3BindingTest", "MibrV3SocketTest", "MibrScalingBindingTest"):
            run = subprocess.run([java, "-Dmibr.menu.standard=" + str(ROOT / "tools/menu-editor/standard-menu.txt"),
                                  "-cp", str(out), "de.mibr.hmi." + cls], capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
