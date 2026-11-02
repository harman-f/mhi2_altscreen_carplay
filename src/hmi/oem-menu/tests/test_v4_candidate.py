"""Packaging checks only; synthetic headers never substitute for a J9 build."""
import importlib.util
import io
import json
import subprocess
import tempfile
from pathlib import Path
import unittest
import zipfile

PATH = Path(__file__).resolve().parents[1] / "release/visual-qa-v4-owned-ssm/make_candidate.py"
if PATH.is_file():
    SPEC = importlib.util.spec_from_file_location("v4_candidate", PATH)
    V4 = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(V4)
else:
    V4 = None


def jar(extra=None, major=46):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        for name in sorted(V4.REQUIRED | V4.BRIDGES | set(extra or ())):
            archive.writestr(name, b"\xca\xfe\xba\xbe\x00\x00" + major.to_bytes(2, "big"))
    return data.getvalue()


@unittest.skipUnless(PATH.is_file(), "private vehicle-candidate packager is not part of the public source tree")
class V4Candidate(unittest.TestCase):
    def test_finite_ownership_and_major_gate(self):
        self.assertEqual(len(V4.inspect_jar(jar())), len(V4.REQUIRED | V4.BRIDGES))
        for extra in ("org/korho/Donor.class", "de/vw/mib/widgets/View.class",
                      "de/mibr/hmi/MibrContainer.class"):
            with self.assertRaises(AssertionError):
                V4.inspect_jar(jar([extra]))
        with self.assertRaises(AssertionError):
            V4.inspect_jar(jar(major=48))

    def test_conditional_vehicle_candidate_checks_preimage_and_independent_rollback(self):
        assets = PATH.parents[4] / "design/icon-assets-20261017/generated/native_transparent"
        with tempfile.TemporaryDirectory(prefix="mibr-v4-preflight-") as tmp:
            temp = Path(tmp)
            sample = temp / "synthetic-host-only.jar"
            sample.write_bytes(jar())
            output = temp / "probe.zip"
            V4.make_candidate(sample, assets, "0" * 40, "777", output)
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                names = set(archive.namelist())
                self.assertIn("vehicle-readonly-preflight.ps1", names)
                self.assertIn("VEHICLE_PRETEST.md", names)
                self.assertIn("install-pr93-visual.ksh", names)
                self.assertFalse(any(name.startswith("stage-") or name.startswith("rollback-") for name in names))
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest["draft_pr"], 93)
                self.assertEqual(manifest["source_commit"], "0" * 40)
                self.assertEqual(manifest["status"], "CONDITIONAL_VEHICLE_VISUAL_INSTALL")
                self.assertEqual(manifest["preflight"]["scope"], "WINDOWS_LOCAL_OR_READONLY_SCP_ONLY")
                self.assertEqual(manifest["installer"], "install-pr93-visual.ksh")
                self.assertEqual(manifest["stage_path"], "/net/mmx/fs/sda0/esd/carplay-test/mibr-pr93-visual")
                self.assertEqual(manifest["rollback"], "/mnt/app/root/mibr-pr93-visual-rollback.ksh")
                for record in manifest["files"]:
                    import hashlib
                    contents = archive.read(record["path"])
                    self.assertEqual(hashlib.sha256(contents).hexdigest(), record["sha256"])
                    self.assertEqual(len(contents), record["bytes"])
                preflight = archive.read("vehicle-readonly-preflight.ps1").decode()
                self.assertIn("[switch]$ReadOnlyVehicle", preflight)
                self.assertIn("StrictHostKeyChecking=yes", preflight)
                self.assertIn("PR93_READONLY_PREIMAGE_CAPTURE_PASS", preflight)
                self.assertIn("& $ssh", preflight)
                self.assertIn("PRESENT", preflight)
                self.assertIn("ABSENT", preflight)
                self.assertIn("ICON_PRESENCE_PROBE_FAILED", preflight)
                self.assertIn("BatchMode=yes", preflight)
                self.assertNotIn("mount -uw", preflight)
                self.assertNotIn("scp.exe -", preflight)
                self.assertNotIn("--install", preflight)
                self.assertEqual(preflight.count("& $scp -O @opts"), 2)
                self.assertNotIn("& $ssh -O", preflight)
                installer = archive.read("install-pr93-visual.ksh").decode()
                self.assertIn("cmp \"$TARGET\" \"$STAGE/preimage/R4.before.jar\"", installer)
                self.assertIn("BACK=$APP/root/mibr-pr93-visual-backup", installer)
                self.assertIn('REC=$APP/root/mibr-pr93-visual-rollback.ksh', installer)
                self.assertIn('--check|--install', installer)
                self.assertIn('--restore', installer)
                self.assertIn('ro || fail RESTORE_APP_RO', installer)
                self.assertIn("PASS_ON_DISK_ONLY_HOST_READBACK_REQUIRED", installer)
                self.assertNotIn("reboot", installer.lower())
                self.assertNotIn("ApplyApproved", preflight)

    def test_offline_boundary_and_exact_asset_set(self):
        self.assertEqual(len(V4.ASSETS), 4)
        self.assertIn("CONDITIONAL_VEHICLE_VISUAL_INSTALL", V4.README)
        self.assertIn("BACK", V4.README.upper())
        self.assertIn("local DRAFT", V4.README)
        self.assertIn("Host readback", V4.README)
        self.assertNotIn("no staging, installation or restart entrypoints", V4.README)
        install = PATH.parent / "install-pr93-visual.ksh"
        check = subprocess.run(["bash", "-n", str(install)], capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)


if __name__ == "__main__":
    unittest.main()
