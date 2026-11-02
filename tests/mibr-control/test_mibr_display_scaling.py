"""Portable MIBR display-scaling file format and guarded CAS store, host-only."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from public_paths import DISPLAY_SCALING as NATIVE, TESTS
CC = shutil.which(os.environ.get("CC", "cc")) or shutil.which("gcc")
DOWNGRADE_SOURCE = NATIVE / "mibr_display_scaling_downgrade.c"


@unittest.skipUnless(CC, "requires a C99 host compiler")
class DisplayScalingStore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="mibr-scaling-probe-")
        cls.bin = Path(cls.tmp.name) / "probe"
        subprocess.run([CC, "-std=c99", "-Wall", "-Wextra", "-Werror",
                        "-I", str(NATIVE), str(NATIVE / "mibr_display_scaling.c"),
                        str(TESTS / "native_display_scaling_probe.c"),
                        "-o", str(cls.bin)], check=True, capture_output=True, text=True)
        cls.downgrade = Path(cls.tmp.name) / "downgrade"
        if DOWNGRADE_SOURCE.is_file():
            subprocess.run([CC, "-std=c99", "-Wall", "-Wextra", "-Werror",
                            "-I", str(NATIVE), str(NATIVE / "mibr_display_scaling.c"),
                            str(DOWNGRADE_SOURCE), "-o", str(cls.downgrade)],
                           check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mibr-scaling-case-")
        self.root = Path(self.temp.name)
        self.path = self.root / "display-scaling.conf"

    def tearDown(self):
        self.temp.cleanup()

    def run_probe(self, *args, ok=True):
        result = subprocess.run([str(self.bin), *map(str, args)], capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_compiled_auto_distinct_from_explicit_100_and_per_display_cas(self):
        self.assertEqual(self.run_probe("read", self.path).stdout.strip(), "0|AUTO|AUTO|BASE|BASE|0")
        first = self.run_probe("set", self.path, "scaling.main.zoomFactor", "100", 0)
        self.assertEqual(first.stdout.strip(), "0|1|100|AUTO|BASE|BASE|1")
        self.assertEqual(self.path.read_text(),
                         "MIBR_SCALING/3\nrevision=1\nmain=100\ncluster=AUTO\nphysical=BASE\nmain_physical=BASE\n")
        second = self.run_probe("set", self.path, "scaling.cluster.zoomFactor", "150", 1)
        self.assertEqual(second.stdout.strip(), "0|2|100|150|BASE|BASE|1")
        self.assertEqual(Path(str(self.path) + ".lastgood").read_text(),
                         "MIBR_SCALING/3\nrevision=1\nmain=100\ncluster=AUTO\nphysical=BASE\nmain_physical=BASE\n")
        no_op = self.run_probe("set", self.path, "scaling.cluster.zoomFactor", "150", 2)
        self.assertEqual(no_op.stdout.strip(), "1|2|100|150|BASE|BASE|1")
        stale = self.run_probe("set", self.path, "scaling.main.zoomFactor", "70", 1, ok=False)
        self.assertEqual(stale.returncode, 3)
        self.assertIn("STALE_REVISION", stale.stderr)

    def test_every_contract_value_and_exact_format_validation(self):
        for value in ("70", "85", "100", "125", "150", "AUTO"):
            path = self.root / (value + ".conf")
            self.run_probe("set", path, "scaling.main.zoomFactor", "70", 0)
            result = self.run_probe("set", path, "scaling.cluster.zoomFactor", value, 1)
            revision = 1 if value == "AUTO" else 2
            expected = "MIBR_SCALING/3\nrevision=%d\nmain=70\ncluster=%s\nphysical=BASE\nmain_physical=BASE\n" % (revision, value)
            self.assertEqual(path.read_text(), expected)
            self.assertIn("|%d|70|%s|BASE|BASE|1" % (revision, value), result.stdout)
        malformed = self.root / "malformed.conf"
        malformed.write_text("MIBR_SCALING/1\nrevision=01\nmain=AUTO\ncluster=100\n")
        invalid = self.run_probe("read", malformed, ok=False)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("INVALID_SCALING_FILE", invalid.stderr)

    def test_advertisement_receipt_requires_matching_revision_and_values(self):
        self.run_probe("set", self.path, "scaling.main.zoomFactor", "125", 0)
        status = self.root / "scaling.status"
        status.write_text("MIBR_SCALING_ADVERTISED/3\nrevision=1\nmain=125\ncluster=AUTO\nphysical=BASE\nmain_physical=BASE\n")
        match = self.run_probe("advertised", self.path, status)
        self.assertEqual(match.stdout.strip(), "1|125|AUTO|BASE|BASE")
        status.write_text("MIBR_SCALING_ADVERTISED/3\nrevision=0\nmain=125\ncluster=AUTO\nphysical=BASE\nmain_physical=BASE\n")
        stale = self.run_probe("advertised", self.path, status)
        self.assertEqual(stale.stdout.strip(), "0|UNKNOWN|UNKNOWN|UNKNOWN|UNKNOWN")

    def test_physical_presets_persist_and_keep_zoom_values(self):
        self.run_probe("set", self.path, "scaling.main.zoomFactor", "85", 0)
        self.run_probe("set", self.path, "scaling.cluster.zoomFactor", "125", 1)
        choices = (("P20", 240, 89), ("P30", 260, 96), ("P50", 300, 111), ("BASE", 200, 74))
        for revision, (preset, w, h) in enumerate(choices, start=2):
            result = self.run_probe("set", self.path, "scaling.cluster.physicalSize", preset, revision)
            self.assertEqual(result.stdout.strip(),
                             "0|%d|85|125|%s|BASE|1" % (revision + 1, preset))
            self.assertIn("physical=%s\n" % preset, self.path.read_text())
            self.assertEqual((w, h)[0] > 0 and (w, h)[1] > 0, True)
        self.assertEqual(self.run_probe("read", self.path).stdout.strip(), "6|85|125|BASE|BASE|1")
        for invalid in ("", "BASE2", "P10", "P21", "P100", "AUTO", "260", "P-30"):
            if not invalid:
                continue
            result = self.run_probe("set", self.path, "scaling.cluster.physicalSize", invalid, 6, ok=False)
            self.assertEqual(result.returncode, 3)
        self.assertEqual(self.run_probe("read", self.path).stdout.strip(), "6|85|125|BASE|BASE|1")

    @unittest.skipUnless(DOWNGRADE_SOURCE.is_file(), "Research-only scaling downgrade helper is omitted from the public source tree")
    def test_legacy_rollback_stage_restores_two_key_format(self):
        self.run_probe("set", self.path, "scaling.main.zoomFactor", "125", 0)
        self.run_probe("set", self.path, "scaling.cluster.physicalSize", "P50", 1)
        before = self.path.read_text()
        stage_v2 = self.root / "rollback-v2.stage"
        result_v2 = subprocess.run([str(self.downgrade), "--to-v2", str(self.path), str(stage_v2)],
                                   capture_output=True, text=True)
        self.assertEqual(result_v2.returncode, 0, result_v2.stderr)
        self.assertEqual(stage_v2.read_text(),
            "MIBR_SCALING/2\nrevision=2\nmain=125\ncluster=AUTO\nphysical=P50\n")
        self.assertEqual(self.run_probe("read", stage_v2).stdout.strip(), "2|125|AUTO|P50|BASE|1")
        self.assertEqual(self.path.read_text(), before)
        stage = self.root / "rollback-v1.stage"
        result = subprocess.run([str(self.downgrade), str(self.path), str(stage)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stage.read_text(),
            "MIBR_SCALING/1\nrevision=2\nmain=125\ncluster=AUTO\n")
        self.assertEqual(self.path.read_text(), before)
        second = subprocess.run([str(self.downgrade), str(self.path), str(stage)],
                                capture_output=True, text=True)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(stage.read_text(),
            "MIBR_SCALING/1\nrevision=2\nmain=125\ncluster=AUTO\n")

    def test_legacy_v1_loaded_and_upgraded_atomically(self):
        self.path.write_text("MIBR_SCALING/1\nrevision=17\nmain=70\ncluster=85\n")
        self.assertEqual(self.run_probe("read", self.path).stdout.strip(), "17|70|85|BASE|BASE|1")
        self.run_probe("set", self.path, "scaling.cluster.physicalSize", "P30", 17)
        self.assertEqual(self.path.read_text(),
                         "MIBR_SCALING/3\nrevision=18\nmain=70\ncluster=85\nphysical=P30\nmain_physical=BASE\n")
        self.assertEqual(Path(str(self.path) + ".lastgood").read_text(),
                         "MIBR_SCALING/1\nrevision=17\nmain=70\ncluster=85\n")
        malformed = self.root / "invalid2"
        malformed.write_text("MIBR_SCALING/2\nrevision=1\nmain=AUTO\ncluster=AUTO\nphysical=P25\n")
        self.assertEqual(self.run_probe("read", malformed, ok=False).returncode, 2)

    def test_legacy_v2_physical_value_survives_upgrade_to_v3(self):
        self.path.write_text("MIBR_SCALING/2\nrevision=9\nmain=125\ncluster=85\nphysical=P50\n")
        self.assertEqual(self.run_probe("read", self.path).stdout.strip(), "9|125|85|P50|BASE|1")
        self.run_probe("set", self.path, "scaling.main.physicalSize", "P20", 9)
        self.assertEqual(self.path.read_text(),
            "MIBR_SCALING/3\nrevision=10\nmain=125\ncluster=85\nphysical=P50\nmain_physical=P20\n")
        self.assertEqual(Path(str(self.path) + ".lastgood").read_text(),
            "MIBR_SCALING/2\nrevision=9\nmain=125\ncluster=85\nphysical=P50\n")

    def test_main_physical_presets_scale_arbitrary_oem_dimensions_with_nearest_rounding(self):
        self.assertEqual(self.run_probe("dimensions", "BASE", 153, 77).stdout.strip(), "153|77")
        self.assertEqual(self.run_probe("dimensions", "P20", 153, 77).stdout.strip(), "184|92")
        self.assertEqual(self.run_probe("dimensions", "P30", 153, 77).stdout.strip(), "199|100")
        self.assertEqual(self.run_probe("dimensions", "P50", 153, 77).stdout.strip(), "230|116")
        self.assertEqual(self.run_probe("dimensions", "BASE", 206, 104).stdout.strip(), "206|104")
        self.assertEqual(self.run_probe("dimensions", "P20", 206, 104).stdout.strip(), "247|125")
        self.assertEqual(self.run_probe("dimensions", "P30", 206, 104).stdout.strip(), "268|135")
        self.assertEqual(self.run_probe("dimensions", "P50", 206, 104).stdout.strip(), "309|156")
        for value in ("BASE", "P50"):
            self.assertEqual(self.run_probe("dimensions", value, 0, 77, ok=False).returncode, 5)
        self.assertEqual(self.run_probe("dimensions", "P50", 2147483647, 77, ok=False).returncode, 5)
        self.run_probe("set", self.path, "scaling.main.physicalSize", "P30", 0)
        self.assertEqual(self.path.read_text(),
            "MIBR_SCALING/3\nrevision=1\nmain=AUTO\ncluster=AUTO\nphysical=BASE\nmain_physical=P30\n")


if __name__ == "__main__":
    unittest.main()
