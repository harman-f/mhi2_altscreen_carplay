# MU1440 clock-domain comparison (read-only)

This is a host-side inspection of **existing** parity-drive SD samples, not a
new in-vehicle clock source or a transport-parameter setting. It uses the
telemetry introduced by draft PR #20; no change to runtime clock decisions.

## Input and operation

The existing parity-drive supervisor emits:

```text
/net/mmx/fs/sda0/esd/carplay-test/logs/parity-drive/<run>/status-snapshots.log
```

It must be running with its existing STATUS/STATS collection enabled. It
validates SD writability before starting the owned session and handles SD
remounting. Do not run an additional SD remounting logger in parallel.

On a computer with Python 3 (standard library only), copy this log and run:

```sh
python3 tools/analyze_mu1440_clock_domains.py status-snapshots.log \
  --csv clock-intervals.csv --json clock-summary.json
```

Outputs:
- console + JSON: aggregate elapsed **source vs monotonic** and **accepted
  transport vs monotonic**, effective rate ppm and observed PTS/PCR lead range.
- CSV: per-adjacent-snapshot samples with source, transport, and system elapsed
  milliseconds; drift ppm, session segment and status counters.
- **Return code 2** when there are no valid diagnostic pairs (including legacy
  status files without PR #20 fields); no fabricated zero drift.

## Clock basis and limitations

| Source | Definition |
| --- | --- |
| Source | Apple M1AU 32.32 `assigned_source_sec/frac` converted to 90 kHz |
| System | MMX CLOCK_MONOTONIC at assignment and completed write |
| Transport | accepted 12032-byte blocks × 705 ticks at 90 kHz |
| PCR | `transport_pcr90k` validates accepted block increments |

`assigned_mono_us` pairs with the last assigned source timestamp;
`accepted_mono_us` pairs with `accepted_blocks`. Compare **rates**, not
instantaneous phase between these asynchronous events.

```text
source_ppm = 1e6 × (Δsource90k / 90kHz / Δassigned_mono_s - 1)
transport_ppm = 1e6 × (Δaccepted_blocks × 705 / 90kHz / Δaccepted_mono_s - 1)
source_minus_transport_ppm ≈ source_ppm - transport_ppm
```

Only compatible samples within the same writer generation are analyzed.
Rebases, counter regressions, source timestamp absence, gaps >20 s and
PCR/block inconsistency are excluded. Driver acceptance is **not proof of
physical MOST drain or actual VC presentation cadence**. Interpret changes
in PTS/PCR lead alongside EAGAIN, write latency, queued AUs and visible motion.

## Tests / boundaries

```sh
python3 tests/test_mu1440_clock_domains.py
```

Tests cover synchronized rates, deliberately slow transport, rebases,
writer restarts, missing source timestamps and legacy-log rejection.

No new governed setting was added. The four frozen core-component roles and
`writev_gate` ownership are unchanged. Do not merge draft PR #20 without
explicit approval; replace a vehicle bridge only as the cryptographically
matched `direct-ts-parity` + `parity-session` pair after complete stock return.
