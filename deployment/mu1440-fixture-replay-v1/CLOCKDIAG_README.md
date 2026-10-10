# MU1440 low-overhead clock diagnostics v1 — VEHICLE TEST CANDIDATE

Status: unmerged development source. Requires successful paired QNX CI build, verified zip and exact vehicle preflight before install. This is a **measurement build**, not PCR correction.

## Provenance and constraints

Starts from the already vehicle-tried CI305 fixture code. All transport constants remain unchanged:
12.288Mbit/s MPEG-TS, 705 ticks per 64 packets, 327-packet (~40ms) PCR spacing, 12032 bytes per device write, H.264 AU and source 32.32 semantics. No new thread, TS-packet instrumentation, per-packet log, watchdog change, ownership change or stock-process kill. A single monotonic timestamp and integer counters are added per received AU. The expensive QNX /tmp status-file publication is limited to **at most once per second during continuous 'running' state**, with immediate final and state-change status. All telemetry is observation; accepted writes are **not** physical MOST drain timestamps.

New status fields:
- `diag_clock_accepted_elapsed_us`, `diag_clock_nominal_transport_us`, `diag_clock_accepted_model_ppm`
- `diag_source_elapsed_us`, `diag_arrival_elapsed_us`, `diag_last_arrival_age_us`
- `diag_max_arrival_gap_us`, `diag_arrival_gaps_ge50ms`, `diag_arrival_gaps_ge100ms`, `diag_arrival_gaps_ge250ms`
- `diag_max_source_gap_us`, `diag_source_rewinds`, `diag_source_samples`
- `diag_input_fps_x100`, `diag_fps_window_elapsed_us`, `diag_fps_window_count`

The FPS gauge is computed from samples in the last completed >=1s window and is not an imposed constant frame rate. There is also a 'no new video AU' age gauge. The value `pts_pcr_lead_ms` is an internal sparse measurement and must not be used as a wall-clock feedback loop during low FPS.

## SD overlay

Unzip the small *clockdiag-v1* folder to:

`/net/mmx/fs/sda0/esd/carplay-test/omonob-clock-test/clockdiag-v1/`

Expected folder files: `direct-ts-parity`, `parity-session`, `PAIR_SHA256SUMS.txt`, `MU1440_CLOCKDIAG_SWAP.sh`, `MU1440_CLOCKDIAG_LIVE.sh`, `MU1440_CLOCKDIAG_FIXTURE.sh`, `CLOCKDIAG_README.md`.

The exact 23,275,739-byte reference media remains under `/net/mmx/fs/sda0/esd/carplay-test/fixtures/mu1440-motion-v1/mu1440_motion_1010x376_30fps_gop20.m1au`.

**The swap script accepts either of two exact existing matched binaries (CI295 or CI305)** and independently backs up the actual current pair to `/mnt/app/root/mibr-clockdiag-v1-backup/`. It refuses unknown pairs, live processes, enabled supervisor, unconfirmed stock native gate or mismatched downloaded binaries. If an earlier fixture run returned `failed_stock`, verify that it has ended and native gate and routing are stock before swap. Do not confuse that state label with proof of a still-owned gate; the native gate must be 0 and there must be no owner PID/lock.

## Commands (one SSH line at a time)

Park vehicle. No installation without full artifact hash verification.

```sh
cd /net/mmx/fs/sda0/esd/carplay-test/omonob-clock-test/clockdiag-v1
/bin/ksh MU1440_CLOCKDIAG_SWAP.sh install
/bin/ksh MU1440_CLOCKDIAG_SWAP.sh verify
```

**Live CarPlay diagnostic**: Connect phone first, make sure source Stream 111 is `streaming`, normal VC source visible before gate takeover and persistent parity-drive supervisor disabled; run foreground with logs for 150 seconds:

```sh
/bin/ksh MU1440_CLOCKDIAG_LIVE.sh preflight
/bin/ksh MU1440_CLOCKDIAG_SWAP.sh live
```

Status and stop (from a second SSH shell if required):

```sh
/bin/ksh MU1440_CLOCKDIAG_SWAP.sh status
/bin/ksh MU1440_CLOCKDIAG_SWAP.sh stop
```

**Reference fixture instead**: Disconnect iPhone, stock native VC navigation active, run first preflight and then the original 120s synthetic clip through the same owner/gate/writer:

```sh
/bin/ksh MU1440_CLOCKDIAG_FIXTURE.sh preflight
/bin/ksh MU1440_CLOCKDIAG_SWAP.sh fixture
```

The fixture replay owner in this version is retained for compatibility and may still return `rc=15` despite `fixture_complete rc=0` after clean EOF due to a QNX procfs child-reap classification defect; always inspect `session.log` and confirm gate 0, not infer automatic success from return code. **No blanket override of rc=15** or stock gate bypass is introduced. A separate safe fix remains tracked for that issue.

Logs: `/net/mmx/fs/sda0/esd/carplay-test/logs/parity-drive/clockdiag-live-*/` for live and `fixture-*/` for synthetic clip. Copy the entire latest folder with `session.log`, `status-snapshots.log`, `parity-final.status`, `gate-final.status`, `summary.txt`.

**Return to exact previous version** after owner has fully ended and gate is stock:

```sh
/bin/ksh MU1440_CLOCKDIAG_SWAP.sh restore
```

This restores whichever of CI295 or CI305 was present immediately before clockdiag install, with exact stored hash checks, preserving the same existing GEN2 library and all other vehicle components. No reboot, no auto-start.

If you want the long-term CI295 vehicle baseline afterward but your actual pre-clockdiag version was CI305, first restore CI305 with this tool, then follow its *original* tested rollback script; do not mix two pairs by hand.

## Validation acceptance

Green pinned QNX ARMv7 CI, host self-tests for fps/gaps and 1Hz status limiter, matched bridge-owner binary hash and integrity proof, zero owner/gate ownership changes, stable 3600/3600 fixture, no new write errors. Compare real-world CPU load and output before/after; the changes are designed to be extremely light but no on-device CPU benchmark has yet been recorded. No PCR adjustments until vehicle timing observations justify one.

Research decision: https://github.com/CaneTLOTW/M.I.B._Research/blob/main/projects/mhi2-altscreen-thirdparty-audit/analysis/MU1440_ADR_LOW_OVERHEAD_CLOCK_DIAGNOSTICS_2026-10-10.md
