"""End-to-end test of the modular assembler: synthetic native/HMI inputs -> real ZIP -> validator.

All inputs are synthetic; no OEM bytes. Host-only.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/release"))
sys.path.insert(0, str(ROOT / "tools"))
import build_modular as bm  # noqa: E402
import validate_modular_package as vmp  # noqa: E402

SINGLE = "skoda-mu1440-p4526"


class BuildModularZip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        t = Path(cls.td.name)
        cls.native, cls.inst, cls.hmi = t / "bo", t / "inst", t / "hmi"
        bm.fake_native(cls.native)
        bm.fake_installer(cls.inst)
        bm.fake_hmi(cls.hmi)
        cls.t = t

    @classmethod
    def tearDownClass(cls):
        cls.td.cleanup()

    def build(self, name, **kw):
        kw.setdefault("hmi_dir", self.hmi)
        files, meta = bm.assemble(self.native, ROOT, self.inst, allow_dirty=True, **kw)
        return bm.write_zip(files, self.t / name), meta

    def test_three_profile_zip_deterministic_and_valid(self):
        a, meta = self.build("a.zip")
        b, _ = self.build("sub/b.zip")
        self.assertEqual(a, b)
        self.assertEqual(meta["package_status"], "complete")
        self.assertEqual(len(meta["profiles"]), 3)
        self.assertTrue(all(isinstance(v["install_enabled"], bool) for v in meta["profile_info"].values()))
        out = self.t / "extracted"
        with zipfile.ZipFile(self.t / "a.zip") as z:
            z.extractall(out)
        vmp.validate(out)                      # extracted tree
        vmp.validate(self.t / "a.zip", True)   # the ZIP itself
        listing = bm.load_zip(self.t / "a.zip")
        self.assertEqual(bm.check_docs(listing), [])
        for name in (bm.README, bm.MATRIX):
            text = listing[name].decode()
            self.assertIn("/mnt/app/root/mibr", text)
            self.assertNotIn("altscreen-u2", text)
        profiles_list = listing["installer/config/profiles.list"].decode()
        self.assertIn("seat-mu1409-p4708 MHI2_ER_SEG11_P4708_MU1409 1", profiles_list)
        pj = json.loads(listing["package.json"])
        self.assertTrue(all(r["status"] == "SOURCE_BUILD_PASS" for r in pj["binaries"]))
        self.assertTrue(all(pj["native_build"][k] for k in ("source_commit", "compiler", "image_source")))
        self.assertFalse(any(n.endswith(bm.BUILD_SUFFIX) for n in listing))

    def test_input_change_changes_zip(self):
        a, _ = self.build("c.zip")
        (self.hmi / SINGLE / "MIBR-CarPlay.jar").write_bytes(b"PK other")
        try:
            b, _ = self.build("d.zip")
        finally:
            (self.hmi / SINGLE / "MIBR-CarPlay.jar").write_bytes(b"PK synthetic jar " + SINGLE.encode())
        self.assertNotEqual(a, b)

    def test_incomplete_package(self):
        digest, meta = self.build("inc.zip", hmi_dir=None)
        self.assertEqual(meta["package_status"], "incomplete")
        self.assertEqual(sorted(m for m in meta["missing_inputs"]),
                         sorted("profiles/%s/hmi/MIBR-CarPlay.jar" % p for p in meta["profiles"]))
        vmp.validate(self.t / "inc.zip")
        with self.assertRaises(vmp.PackageError):
            vmp.validate(self.t / "inc.zip", True)

    def test_single_profile_scope_and_wrapper(self):
        _, meta = self.build("one.zip", profiles=[SINGLE], scope=bm.SCOPE_VALUE)
        self.assertEqual(meta["scope"], "single-profile")
        vmp.validate(self.t / "one.zip", True)
        out = self.t / "wrapper.zip"
        r = subprocess.run([sys.executable, "-B", str(ROOT / "tools/release/build_mu1440_modular.py"),
                            "--native-dir", str(self.native), "--hmi-dir", str(self.hmi),
                            "--installer-dir", str(self.inst), "--allow-dirty", "--out", str(out)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(bm.load_zip(out)["package.json"])["profiles"], [SINGLE])
        vmp.validate(out, True)

    def test_subset_without_scope_refused(self):
        with self.assertRaises(bm.AssembleError):
            bm.assemble(self.native, ROOT, self.inst, hmi_dir=self.hmi, profiles=[SINGLE],
                        allow_dirty=True)


if __name__ == "__main__":
    unittest.main()
