#!/usr/bin/env python3
"""Repeatable private reference + dual-build regression. No network, no Unit."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
from public_paths import NATIVE, ROOT
REFERENCE = ROOT / "evidence/unit/2026-10-27-gps-stock-capture/iap2-location-stock-60s.log"
REFERENCE_SHA = "702273f68ffbe0e374f282da1cac02d13945f7a163aa13ad92a7c3a23ef49d9d"


def nmea_checksum_ok(line):
    if not line.startswith("$") or "*" not in line:
        return False
    body, suffix = line[1:].split("*", 1)
    checksum = 0
    for char in body.encode("ascii"):
        checksum ^= char
    return len(suffix) >= 2 and checksum == int(suffix[:2], 16)


class LocalGPSExperiment(unittest.TestCase):
    def test_pinned_off_mode_reference(self):
        if not REFERENCE.is_file():
            self.skipTest("Research-only unit capture is not part of the public source repository")
        data = REFERENCE.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), REFERENCE_SHA)
        self.assertEqual(len(data), 39671)
        text = data.decode("utf-8")
        gga = re.findall(r"NMEASentence:\s*(\$GPGGA[^\r\n]*)", text)
        rmc = re.findall(r"NMEASentence:\s*(\$GPRMC[^\r\n]*)", text)
        pascd = re.findall(r"NMEASentence:\s*(\$PASCD[^\r\n]*)", text)
        self.assertEqual((len(gga), len(rmc), len(pascd)), (61, 61, 10))
        self.assertTrue(all(nmea_checksum_ok(line) for line in gga + rmc))
        coords_gga = {tuple(line.split(",")[2:6]) for line in gga}
        coords_rmc = {tuple(line.split(",")[3:7]) for line in rmc}
        self.assertEqual(len(coords_gga), 1)
        self.assertEqual(len(coords_rmc), 1)
        self.assertEqual(next(iter(coords_gga)), next(iter(coords_rmc)))
        self.assertEqual({line.split(",")[6] for line in gga}, {"6"})
        self.assertEqual({line.split(",")[2] for line in rmc}, {"A"})
        self.assertEqual({line.split(",")[7] for line in rmc}, {"0.0"})

    def test_stock_iap2_frames_are_already_one_nmea_per_location_message(self):
        if not REFERENCE.is_file():
            self.skipTest("Research-only unit capture is not part of the public source repository")
        data = REFERENCE.read_text(encoding="utf-8")
        packets = [p for p in data.split("TID05 SEND") if "[FFFB] LocationInformation:" in p]
        self.assertEqual(len(packets), 132)
        self.assertTrue(all(p.count("NMEASentence:") == 1 for p in packets))
        self.assertTrue(all("[    0] NMEASentence:" in p for p in packets))
        self.assertGreaterEqual(data.count(" ACK)"), 132)  # includes other control ACKs
        # This rules out the known ChairPlay joined-string failure mode
        # in the ORIGINAL HARMAN sender. Do not change frame packaging.
 
    def test_default_berlin_hamburg_build_is_unchanged(self):
        self._compile_run("gps_demo_host_test.c")

    def test_explicit_two_town_menu_values(self):
        self._compile_run("gps_two_town_host_test.c")

    def _compile_run(self, fixture):
        cc = shutil.which(os.environ.get("CC", "cc"))
        self.assertIsNotNone(cc, "Host C compiler required")
        with tempfile.TemporaryDirectory(prefix="gps-two-town-") as d:
            exe = Path(d) / "test"
            argv = [cc, "-std=gnu99", "-O2", "-Wall", "-Wextra", "-Werror", "-I", str(NATIVE)]
            argv += [str(NATIVE / "mibr_gps_demo.c"), str(HERE / fixture), "-o", str(exe)]
            result = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("PASS", run.stdout)


if __name__ == "__main__":
    unittest.main()
