#!/usr/bin/env python3
"""Writer diagnostic analyzer: aligned samples and fail-closed legacy handling."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "analyze_mu1440_writer_timing.py"
spec = importlib.util.spec_from_file_location("writer_budget", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sample(i, epoch=10, *, probe=1, with_new=True):
    t = (i - 1) * 1_000_000
    fields = {
        "writer_epoch_mono_us": epoch,
        "accepted_mono_us": 5_000_000 + t,
        "accepted_blocks": 100 + 128 * (i - 1),
        "accepted_write_us_total": 900_000 * (i - 1),
        "writer_timing_probe": probe,
        "writer_prepare_us_total": 20_000 * (i - 1),
        "writer_post_write_us_total": 80_000 * (i - 1),
        "writer_success_syscall_us_total": 100_000 * (i - 1),
        "writer_eagain_syscall_us_total": 50_000 * (i - 1),
        "writer_eagain_sleep_us_total": 700_000 * (i - 1),
        "writer_success_syscalls": 128 * (i - 1),
        "write_eagain": 256 * (i - 1),
        "write_errors": 0,
    }
    if not with_new:
        fields = {k: v for k, v in fields.items()
                  if not k.startswith("writer_")}
    return ("===== sample={} =====\n--- parity ---\n".format(i) +
            "".join("{}={}\n".format(k, v) for k, v in fields.items()) +
            "--- source timing ---\naccepted_blocks=99999\n")


class WriterBudgetTests(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "status.log"
            p.write_text(text, encoding="utf-8")
            return mod.parse(p)

    def test_budget_adds_and_attributes(self):
        samples = self.parse(sample(1) + sample(2) + sample(3))
        rows, skipped = mod.intervals(samples)
        self.assertEqual(len(rows), 2, skipped)
        row = rows[0]
        self.assertEqual(row["write_full_us"], 900_000)
        self.assertEqual(row["prepare_us"], 20_000)
        self.assertEqual(row["post_write_us"], 80_000)
        self.assertEqual(row["write_full_unclassified_us"], 50_000)
        self.assertEqual(row["cycle_unclassified_us"], 0)
        report = mod.summarize(rows, skipped, len(samples))
        self.assertEqual(report["totals"]["write_eagain"], 512)
        self.assertEqual(report["totals"]["accepted_blocks"], 256)

    def test_generation_and_probe_gates(self):
        samples = self.parse(sample(1) + sample(2, epoch=11) +
                             sample(3, epoch=11, probe=0))
        rows, skipped = mod.intervals(samples)
        self.assertFalse(rows)
        self.assertEqual(skipped.get("writer restart"), 1)
        self.assertEqual(skipped.get("timing probe disabled"), 1)

    def test_legacy_rejected(self):
        rows, skipped = mod.intervals(self.parse(sample(1, with_new=False) +
                                                 sample(2, with_new=False)))
        self.assertFalse(rows)
        self.assertEqual(skipped.get("missing writer timing fields"), 1)


if __name__ == "__main__":
    unittest.main()
