#!/usr/bin/env python3
"""Passive MU1440 writer budget analyzer for PR #20 follow-up diagnostic fields.

This script runs on a computer, never on the QNX unit. It measures accepted
block timing, not physical MOST drain nor VC display presentation.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

REQUIRED = (
    "writer_epoch_mono_us", "accepted_mono_us", "accepted_blocks",
    "accepted_write_us_total", "writer_timing_probe",
    "writer_prepare_us_total", "writer_post_write_us_total",
    "writer_success_syscall_us_total", "writer_eagain_syscall_us_total",
    "writer_eagain_sleep_us_total", "writer_success_syscalls", "write_eagain",
    "write_errors",
)
COUNTERS = tuple(k for k in REQUIRED if k not in (
    "writer_epoch_mono_us", "writer_timing_probe"))


def parse(path):
    samples, sample, section = [], None, False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("===== sample="):
            if sample is not None:
                samples.append(sample)
            sample = {"sample": line.split("sample=", 1)[1].split()[0]}
            section = False
            continue
        if line == "--- parity ---":
            section = True
            continue
        if line.startswith("--- "):
            section = False
            continue
        if section and sample is not None and "=" in line:
            k, v = line.split("=", 1)
            if k in REQUIRED:
                try:
                    sample[k] = int(v, 0)
                except ValueError:
                    pass
    if sample is not None:
        samples.append(sample)
    return samples


def intervals(samples, max_gap_s=20):
    rows, skipped = [], {}
    def skip(reason):
        skipped[reason] = skipped.get(reason, 0) + 1
    for a, b in zip(samples, samples[1:]):
        if any(k not in a or k not in b for k in REQUIRED):
            skip("missing writer timing fields")
            continue
        if a["writer_epoch_mono_us"] != b["writer_epoch_mono_us"]:
            skip("writer restart")
            continue
        if a["writer_timing_probe"] != 1 or b["writer_timing_probe"] != 1:
            skip("timing probe disabled")
            continue
        if any(b[k] < a[k] for k in COUNTERS):
            skip("counter regression")
            continue
        wall = b["accepted_mono_us"] - a["accepted_mono_us"]
        blocks = b["accepted_blocks"] - a["accepted_blocks"]
        if not blocks or not 0 < wall <= max_gap_s * 1000000:
            skip("no progress or excessive sample gap")
            continue
        delta = {k: b[k] - a[k] for k in COUNTERS}
        prep = delta["writer_prepare_us_total"]
        post = delta["writer_post_write_us_total"]
        write = delta["accepted_write_us_total"]
        accepted_nominal = blocks * 705 * 1000000 / 90000
        inside_unclassified = write - sum(
            delta[k] for k in (
                "writer_success_syscall_us_total",
                "writer_eagain_syscall_us_total",
                "writer_eagain_sleep_us_total"))
        unclassified = wall - write - prep - post
        rows.append({
            "sample_a": a["sample"], "sample_b": b["sample"],
            "accepted_blocks": blocks,
            "wall_us": wall, "nominal_transport_us": round(accepted_nominal, 3),
            "transport_lag_us": round(wall - accepted_nominal, 3),
            "write_full_us": write, "prepare_us": prep, "post_write_us": post,
            "success_syscall_us": delta["writer_success_syscall_us_total"],
            "eagain_syscall_us": delta["writer_eagain_syscall_us_total"],
            "eagain_sleep_us": delta["writer_eagain_sleep_us_total"],
            "write_full_unclassified_us": inside_unclassified,
            "cycle_unclassified_us": unclassified,
            "success_syscalls": delta["writer_success_syscalls"],
            "write_eagain": delta["write_eagain"],
            "write_errors": delta["write_errors"],
        })
    return rows, skipped


def summarize(rows, skipped, count):
    result = {"snapshots": count, "valid_intervals": len(rows),
              "skipped": skipped, "basis": "accepted driver writes, not physical MOST drain"}
    if not rows:
        return result
    totals = {k: sum(row[k] for row in rows) for k in rows[0]
              if k not in ("sample_a", "sample_b")}
    wall = totals["wall_us"]
    result["totals"] = totals
    result["transport_rate_offset_ppm"] = round(
        (totals["nominal_transport_us"] / wall - 1) * 1000000, 2)
    result["ms"] = {k: round(v / 1000, 3) for k, v in totals.items()
                    if k.endswith("_us")}
    result["fraction_of_wall"] = {
        k: round(totals[k] / wall, 6)
        for k in ("write_full_us", "prepare_us", "post_write_us",
                  "cycle_unclassified_us")}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("status_log", type=Path)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    if not args.status_log.is_file():
        parser.error("missing status log")
    samples = parse(args.status_log)
    rows, skipped = intervals(samples)
    report = summarize(rows, skipped, len(samples))
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else
                                    ["sample_a", "sample_b"])
            writer.writeheader()
            writer.writerows(rows)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    if not rows:
        print("ERROR: no valid writer timing intervals (new binary required)",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
