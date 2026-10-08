#!/usr/bin/env python3
"""Deterministic passive clock-domain review, including invalid-generation gates."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "analyze_mu1440_clock_domains.py"
spec = importlib.util.spec_from_file_location("clock_compare", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def block(sample, sec, assigned_us, accepted_us, blocks, epoch=100, *,
          rebase=0, source_present=1, source_frac=0):
    return f"""===== sample={sample} =====
--- parity ---
state=running
assigned_mono_us={assigned_us}
assigned_source_sec=0x{sec:08x}
assigned_source_frac=0x{source_frac:08x}
assigned_source_present={source_present}
accepted_mono_us={accepted_us}
accepted_blocks={blocks}
transport_pcr90k={45000+blocks*705}
writer_epoch_mono_us={epoch}
pts_rebases={rebase}
source_rebases=0
input_records={sample*32}
pts_pcr_lead_ms={100+sample}
write_eagain=1
--- gen2 ---
assigned_mono_us=999999999
"""


class ClockCompareTests(unittest.TestCase):
    def read(self, data):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "status-snapshots.log"
            path.write_text(data, encoding="utf-8")
            return mod.parse_snapshots(path)

    def test_stable_source_and_backpressured_transport(self):
        # 128 blocks * 705/90 = 1002.6667 ms per 1 s source interval.
        data = (block(1, 100, 1_000_000, 1_000_000, 100)
                + block(2, 101, 2_000_000, 2_002_666, 228)
                + block(3, 102, 3_000_000, 3_005_333, 356))
        samples = self.read(data)
        self.assertEqual(len(samples), 3)
        self.assertEqual(samples[0]["assigned_mono_us"], "1000000")
        rows, skipped = mod.clock_intervals(samples)
        self.assertEqual(len(rows), 2, skipped)
        report = mod.summarize(rows, skipped, len(samples))
        self.assertEqual(report["source_vs_system"]["rate_offset_ppm"], 0)
        self.assertAlmostEqual(report["transport_vs_system"]["rate_offset_ppm"], 0, delta=1)

    def test_transport_slower_than_system(self):
        data = (block(1, 100, 1_000_000, 1_000_000, 100)
                + block(2, 101, 2_000_000, 2_100_000, 228))
        rows, skipped = mod.clock_intervals(self.read(data))
        self.assertEqual(len(rows), 1, skipped)
        report = mod.summarize(rows, skipped, 2)
        self.assertLess(report["transport_vs_system"]["rate_offset_ppm"], -80000)
        self.assertEqual(report["source_vs_system"]["rate_offset_ppm"], 0)

    def test_restarts_rebases_source_absence_and_legacy(self):
        data = (block(1, 100, 1_000_000, 1_000_000, 100)
                + block(2, 101, 2_000_000, 2_002_666, 228, rebase=1)
                + block(3, 102, 3_000_000, 3_005_333, 356, rebase=1, source_present=0)
                + block(4, 103, 4_000_000, 4_008_000, 484, rebase=1, epoch=200)
                + block(5, 104, 5_000_000, 5_010_666, 612, rebase=1, epoch=200))
        rows, skipped = mod.clock_intervals(self.read(data))
        self.assertEqual(len(rows), 1, skipped)
        self.assertEqual(rows[0]["sample_a"], "4")
        self.assertEqual(skipped.get("PTS/source rebase"), 1)
        self.assertEqual(skipped.get("missing source timestamp"), 1)
        self.assertEqual(skipped.get("writer restart"), 1)
        legacy = self.read("===== sample=1 =====\n--- parity ---\ntransport_pcr90k=50000\n")
        rows, skipped = mod.clock_intervals(legacy)
        self.assertFalse(rows)
        self.assertEqual(skipped.get("missing diagnostic fields"), 1)


if __name__ == "__main__":
    unittest.main()
