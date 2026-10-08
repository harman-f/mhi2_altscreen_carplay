#!/usr/bin/env python3
"""Read MU1440 parity-drive SD status snapshots; compare observed clock rates.

Read-only host tool. Never changes transport/PTS/PCR policy or vehicle state.
Requires diagnostic bridge fields from PR #20 / 12ecd0eb or later.
"""
import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

FIELDS = ("assigned_mono_us", "assigned_source_sec", "assigned_source_frac",
          "assigned_source_present", "accepted_mono_us", "accepted_blocks",
          "transport_pcr90k", "writer_epoch_mono_us")
MARKER = "===== sample="


def parse_snapshots(path):
    samples = []
    current, parity = None, False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith(MARKER):
            if current is not None:
                samples.append(current)
            current = {"sample": line[len(MARKER):].split(" ", 1)[0]}
            parity = False
            continue
        if line.startswith("sample=") and current is None:
            current = {"sample": line.split("=", 1)[1]}
            continue
        if line == "--- parity ---" or line == "=== PARITY TRANSPORT ===":
            parity = True
            if current is None:
                current = {"sample": str(len(samples) + 1)}
            continue
        if line.startswith("--- ") or line.startswith("=== "):
            parity = False
            continue
        if not parity or current is None or "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key in FIELDS or key in ("pts_pcr_lead_ms", "pts_rebases", "source_rebases",
                                   "input_records", "write_eagain", "write_errors",
                                   "state", "clock_snapshot_mono_us"):
            current[key] = val
    if current is not None:
        samples.append(current)
    return samples


def as_int(s, k):
    try:
        return int(s[k], 0)
    except (KeyError, ValueError, TypeError):
        return None


def clock_intervals(samples, max_gap_seconds=20.0):
    rows, skipped = [], {}
    def skip(reason):
        skipped[reason] = skipped.get(reason, 0) + 1

    previous = None
    segment = 0
    for s in samples:
        if any(as_int(s, k) is None for k in FIELDS):
            skip("missing diagnostic fields")
            previous = None
            continue
        if previous is None:
            previous = s
            segment += 1
            continue
        a, b = previous, s
        previous = s
        a_writer, b_writer = as_int(a, "writer_epoch_mono_us"), as_int(b, "writer_epoch_mono_us")
        if a_writer != b_writer:
            segment += 1
            skip("writer restart")
            continue
        if as_int(a, "assigned_source_present") != 1 or as_int(b, "assigned_source_present") != 1:
            skip("missing source timestamp")
            continue
        if any(as_int(b, k) < as_int(a, k) for k in
               ("assigned_mono_us", "accepted_mono_us", "accepted_blocks",
                "transport_pcr90k", "input_records", "pts_rebases", "source_rebases")
               if as_int(a, k) is not None and as_int(b, k) is not None):
            segment += 1
            skip("counter/time regression")
            continue
        if any(as_int(b, k) != as_int(a, k) for k in ("pts_rebases", "source_rebases")
               if as_int(a, k) is not None and as_int(b, k) is not None):
            segment += 1
            skip("PTS/source rebase")
            continue
        sys_src_us = as_int(b, "assigned_mono_us") - as_int(a, "assigned_mono_us")
        sys_ts_us = as_int(b, "accepted_mono_us") - as_int(a, "accepted_mono_us")
        blocks = as_int(b, "accepted_blocks") - as_int(a, "accepted_blocks")
        if min(sys_src_us, sys_ts_us, blocks) <= 0:
            skip("no clock progress")
            continue
        if max(sys_src_us, sys_ts_us) > max_gap_seconds * 1000000:
            skip("sample gap too large")
            continue
        # Exact Apple 32.32 source; modulo handles 32-bit seconds wrap.
        ntp_a = (as_int(a, "assigned_source_sec") << 32) | as_int(a, "assigned_source_frac")
        ntp_b = (as_int(b, "assigned_source_sec") << 32) | as_int(b, "assigned_source_frac")
        source_fixed_delta = (ntp_b - ntp_a) % (1 << 64)
        source_ticks = (source_fixed_delta * 90000 + (1 << 31)) >> 32
        if source_ticks <= 0 or source_ticks > max_gap_seconds * 90000:
            skip("invalid source delta")
            continue
        transport_ticks = blocks * 705  # 64x188 B at 12.288 Mbit/s
        pcr_delta = as_int(b, "transport_pcr90k") - as_int(a, "transport_pcr90k")
        if abs(pcr_delta - transport_ticks) > 1:
            skip("PCR/block disagreement")
            continue
        source_ms = source_ticks / 90.0
        ts_ms = transport_ticks / 90.0
        sys_src_ms = sys_src_us / 1000.0
        sys_ts_ms = sys_ts_us / 1000.0
        rows.append({
            "segment": segment, "sample_a": a.get("sample", "?"), "sample_b": b.get("sample", "?"),
            "source_ms": round(source_ms, 5), "source_system_ms": round(sys_src_ms, 5),
            "source_minus_system_ms": round(source_ms - sys_src_ms, 5),
            "source_vs_system_ppm": round((source_ms / sys_src_ms - 1) * 1e6, 2),
            "transport_ms": round(ts_ms, 5), "transport_system_ms": round(sys_ts_ms, 5),
            "transport_minus_system_ms": round(ts_ms - sys_ts_ms, 5),
            "transport_vs_system_ppm": round((ts_ms / sys_ts_ms - 1) * 1e6, 2),
            "source_minus_transport_ppm": round((source_ms / sys_src_ms - ts_ms / sys_ts_ms) * 1e6, 2),
            "pts_pcr_lead_ms": as_int(b, "pts_pcr_lead_ms"),
            "input_records": as_int(b, "input_records"),
            "eagain": as_int(b, "write_eagain"), "write_errors": as_int(b, "write_errors"),
        })
    return rows, skipped


def summarize(rows, skipped, total):
    def overall(media, system):
        # Weight by system elapsed; never average noisy per-second ppm.
        m = sum(r[media] for r in rows)
        s = sum(r[system] for r in rows)
        return {"media_ms": round(m, 3), "system_ms": round(s, 3),
                "lead_change_ms": round(m - s, 3),
                "rate_offset_ppm": round((m / s - 1) * 1e6, 2)}
    result = {"snapshots": total, "valid_intervals": len(rows), "skipped": skipped,
              "clock_basis": "accepted driver writes; physical MOST/VC drain not measured"}
    if rows:
        result["source_vs_system"] = overall("source_ms", "source_system_ms")
        result["transport_vs_system"] = overall("transport_ms", "transport_system_ms")
        src = result["source_vs_system"]["rate_offset_ppm"]
        ts = result["transport_vs_system"]["rate_offset_ppm"]
        result["source_minus_transport_rate_ppm"] = round(src - ts, 2)
        lead = [r["pts_pcr_lead_ms"] for r in rows if r["pts_pcr_lead_ms"] is not None]
        if lead:
            result["observed_pts_pcr_lead_ms"] = {
                "start": lead[0], "end": lead[-1], "min": min(lead),
                "max": max(lead), "median": statistics.median(lead)}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("status_log", type=Path, help="SD parity-drive status-snapshots.log")
    p.add_argument("--csv", type=Path, help="Write each valid adjacent observation as CSV")
    p.add_argument("--json", type=Path, help="Write aggregate diagnostics JSON")
    p.add_argument("--max-gap-seconds", type=float, default=20.0)
    args = p.parse_args()
    if args.max_gap_seconds <= 0:
        p.error("--max-gap-seconds must be positive")
    if not args.status_log.is_file():
        p.error(f"log not found: {args.status_log}")
    samples = parse_snapshots(args.status_log)
    rows, skipped = clock_intervals(samples, args.max_gap_seconds)
    result = summarize(rows, skipped, len(samples))
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else
                                    ["segment", "sample_a", "sample_b"])
            writer.writeheader()
            writer.writerows(rows)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not rows:
        print("ERROR: no valid clock intervals; PR #20 diagnostic status fields required",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
