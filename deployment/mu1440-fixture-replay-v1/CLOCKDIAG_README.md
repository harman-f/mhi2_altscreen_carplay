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

## Synchronized GEN2 + writer timing (script-only extension, Oct 2026)

The 150-second live helper now enables the **already deployed** opt-in GEN2 source timing instrumentation using temporary QNX shmem markers. There are **no changes to QNX writer, owner, GEN2 video or MPEG-TS/PCR binaries**. Existing Stream111 source instrumentation only publishes a small status record about once per second; the SD sampler reads it every three seconds alongside the existing writer, gate and owner snapshots. No per-frame SD logging or additional background worker is introduced.

- GEN2 source timing: `/tmp/mibr-alt111-source-timing.status`, opt-in marker `/tmp/mibr-alt111-source-timing.enabled`, interval `/tmp/mibr-alt111-source-timing-interval-ms` (1000 ms if unset).
- GEN2 output/producer status: `/tmp/mibr-alt111-gen2.status` (best effort, may not publish every field or exist depending on installed GEN2).
- Per-3s combined `status-snapshots.log` sections: `stream111`, `gen2-source-timing`, `gen2`, `parity`, `owner`, `gate`. Snapshot #1 can precede owner startup; exclude stale pre-owner status from measured comparisons.
- End of run: `gen2-source-final.status` and `gen2-final.status` if present, `summary.txt` reports whether captures exist.
- Source time samples are from **accepted Stream111 video AUs after GEN2 submit**, but before the local TCP 19820 tee. They are **not** iPhone compositor/vsync evidence. Comparing with writer input can localize added delivery jitter, not prove iPhone-side rendering.
- Marker/interval creation occurs only in `start` after the normal source, hash, lock and native gate preflight. `status` and `preflight` do not alter markers. The helper deletes only files it created itself at cleanup; existing operator markers and measurement intervals are preserved.
- Missing optional GEN2 counters are reported as missing rather than interpreted as zero. The writer and native gate safety conditions are unchanged.

For an already successfully installed and verified `clockdiag-v1` pair (as on the CI #310 test), **copy the updated live shell script to SD only**. Reinstalling/replacing the writer and owner is unnecessary. Verify that the installed matched binary hashes remain valid with `MU1440_CLOCKDIAG_SWAP.sh verify`. Do not mix or overwrite the production binaries with another build casually.

### Controlled stationary A/B protocol

Keep the car stationary, an SSH session attached, supervisor disabled and the iPhone connected. Run each trial with `/bin/ksh MU1440_CLOCKDIAG_LIVE.sh preflight` first.

1. **A, steady source:** 150 seconds in the same Maps view; no app or display switching. Repeated comparable manual map rotations/pans during approximately seconds 30–120.
2. **B, switching load:** repeat, but deliberately switch apps around seconds 60–90, then return to Maps. Note visually when stutters occur.

Use `/bin/ksh MU1440_CLOCKDIAG_SWAP.sh live` for each run. Label the resulting two distinct SD log folders A and B when transferring. Capture `status-snapshots.log`, `parity-final.status`, `gen2-source-final.status`, `gen2-final.status` (if present), `gate-final.status`, `summary.txt`, `session.log`. Always check `owner_rc=0`, `owner_state=complete_stock`, native gate `M1GATE1 0`, and no writer errors before repeating.

A/B measurements test *source vs writer cadence correlation*. They do not establish physical VC decoder timestamps. Never change PCR, transport bitrate or gate behavior solely on this basis.

Logs: `/net/mmx/fs/sda0/esd/carplay-test/logs/parity-drive/clockdiag-live-*/` for live and `fixture-*/` for synthetic clip. Copy the complete directory including `status-snapshots.log`, `parity-final.status`, `gate-final.status`, `summary.txt`, `session.log`; correlated source files are now included when available.

**Return to exact previous version** after owner has fully ended and gate is stock:

```sh
/bin/ksh MU1440_CLOCKDIAG_SWAP.sh restore
```

This restores whichever of CI295 or CI305 was present immediately before clockdiag install, with exact stored hash checks, preserving the same existing GEN2 library and all other vehicle components. No reboot, no auto-start.

If you want the long-term CI295 vehicle baseline afterward but your actual pre-clockdiag version was CI305, first restore CI305 with this tool, then follow its *original* tested rollback script; do not mix two pairs by hand.

## Validation acceptance

Green pinned QNX ARMv7 CI, host self-tests for fps/gaps and 1Hz status limiter, matched bridge-owner binary hash and integrity proof, zero owner/gate ownership changes, stable 3600/3600 fixture, no new write errors. Compare real-world CPU load and output before/after; the changes are designed to be extremely light but no on-device CPU benchmark has yet been recorded. No PCR adjustments until vehicle timing observations justify one.

Research decision: https://github.com/CaneTLOTW/M.I.B._Research/blob/main/projects/mhi2-altscreen-thirdparty-audit/analysis/MU1440_ADR_LOW_OVERHEAD_CLOCK_DIAGNOSTICS_2026-10-10.md

## Experimental POLLOUT EAGAIN wait – OFF by default

Research branch `work/mu1440-eagain-poll-proto-v1` carries a **non-qualified** writer experiment, built on the clockdiag-v1 results. **Do not replace the already vehicle-tested writer with this binary yet.** Current vehicle deployment, autostart, owner, gate, PCR/PTS and transport format are unchanged.

- Normal operation: original `usleep(1000)` after EAGAIN; exact same timeout (`WRITE_TIMEOUT_US=500000`), nonblocking 12032-byte physical write and fail-closed handling.
- Test-only environment setting `MIBR_PARITY_EAGAIN_WAIT=poll` selects `poll(POLLOUT)` wakeup hints, with a maximum 2-ms per-wait timeout. There is no permanent settings marker and no SD script enables the mode.
- Poll does **not** prove full-block driver capacity. After each indication the next nonblocking write is authoritative. Three immediately-ready or three misleading ready-but-EAGAIN observations, POLLERR/HUP/NVAL, or a poll syscall error disable the experiment for the rest of the writer session and restore the original EAGAIN sleep.
- Status fields: `eagain_wait`, `writer_poll_calls`, `writer_poll_ready`, `writer_poll_timeouts`, `writer_poll_fallbacks`, `writer_poll_wait_us`, `writer_poll_disabled`. In the default mode the new counters remain zero.
- Host C `--self-test` checks poll decision/fallback branches; Python tests check disabled-by-default behavior and run an *illustrative*, deterministic 1ms-request/2ms-effective-sleep model. It does not prove MU1440 driver readiness notification works.
- `/dev/mlb/isoTX2` QNX `poll`/`_IO_NOTIFY` implementation, actual physical drain, VC decoder clock and A/V smoothness remain unverified. A faster poll response cannot, by itself, prove the observed ~0.44% clock discrepancy is corrected.
- No vehicle A/B runs until QNX ARMv7 builds, host/integration regressions and independent owner/native-gate safety review pass. Keep the known-good installation and matched hashes available for rollback.

The clockdiag-v1 scripts built in this branch remain the same, but the paired bridge binary **is different** from the previously qualified artifact. Never copy its bridge into the old clockdiag-v1 directory while relying on previously installed hashes.
