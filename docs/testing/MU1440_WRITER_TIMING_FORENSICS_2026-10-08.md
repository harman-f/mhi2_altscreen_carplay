# MU1440 writer time-budget forensics — 2026-10-08

Scope: follow-up to draft PR #20 and the vehicle 12ecd0eb clock-domain run.
Status: passive instrumentation candidate for offline validation, NOT a clock fix
and NOT an approved vehicle payload. QNX build and vehicle qualification pending.

## Evidence from the supplied SD run

- 39 snapshots; 35 valid adjacent comparisons, 3 missing-data pairs excluded.
- Apple source 32.32: 110.300 s during 110.302 s QNX (-18 ppm).
- Accepted 12032-byte blocks: 14,003 × 705/90,000 s = 109.690167 s
  during 110.301 s QNX acceptance time (-5,538 ppm).
- Accumulated time inside write_full(): 109.572 s; outside: 0.729 s.
- EAGAIN delta 52,462 (3.75 EAGAIN per accepted block).
- PTS-PCR lead rises from 266 ms to 875 ms across this comparison window.
- Final 3,234 AUs (163 IDR, 3,071 non-IDR), zero sequence gaps,
  zero writer errors, owner stop returns 130; bridge SIGTERM returns 143.
- Neither physical MOST drain rate nor AID10 presentation timing is observed.

Interpretation: the Apple clock is nearly aligned with QNX. The logical
accepted-block clock advances ~0.55% slower. Although the 729 ms outside
write_full() exceeds the nominal 611 ms transport lag, this does NOT prove
729 ms wasted CPU work: writer and driver backpressure adapt together.
The EAGAIN 1-ms polling and scheduler wakeup contribution is not isolated
by the old instrumentation.

## New passive writer time-budget counters

When the existing status diagnostic switch is on, the writer aggregates:

- writer_prepare_us_total: loop-start through packet preparation/pacing up
  to initiating the block write
- writer_post_write_us_total: completed previous write to beginning of
  next block loop, including bookkeeping/status-publisher work
- writer_success_syscall_us_total: time within successful write syscalls
- writer_eagain_syscall_us_total: time within EAGAIN write syscalls
- writer_eagain_sleep_us_total: elapsed CLOCK_MONOTONIC across usleep(1000)
  following EAGAIN, including wake-up latency
- writer_success_syscalls, writer_max_prepare_us,
  writer_max_post_write_us

The preexisting accepted_write_us_total, accepted_mono_us,
accepted_blocks and write_eagain counters remain unchanged.
No new configuration scalar, transport pacing, source clock, PCR or PTS
policy, device-write chunking, gate, recovery, or component boundary changes.
The probe adds monotonic reads on the writer hot path when status is enabled;
it can perturb the tested timing, so compare run-to-run variation.

## Offline analysis

On a workstation:

    python3 tools/analyze_mu1440_clock_domains.py status-snapshots.log --json clocks.json
    python3 tools/analyze_mu1440_writer_timing.py status-snapshots.log --csv writer.csv --json writer.json

Older 12ecd0eb logs must fail the new analyzer with exit code 2, not
produce fabricated zeros. The analyzer rejects restarts, missing counters,
disabled probes, counter regressions and excessive gaps.

The residual cycle/unclassified and write_full/unclassified terms are
diagnostic consistency checks across asynchronous status snapshots, NOT
measurements of CPU consumption.

## Reporting-only stop semantics

The parity owner previously labeled an intentional stop rc=130 as
failed_stock even after successful stock route restoration. The proposed
patch maps only rc=130 with restore_ok to complete_stock. The bridge
reports a signal-induced stop with no writer errors as state=stopped
instead of state=error; it still returns rc=143 for SIGTERM.
Exit codes, process identity, watchdog behavior, lock and gate ownership
are not modified.

## Vehicle and release restrictions

- Keep draft PR #19 and PR #20 intact and unmerged.
- New branch stays draft, unmerged; require green host and QNX CI.
- Future matched bridge/owner binaries need paired SHA-256 verification;
  the previously installed 12ecd0eb pair is NOT this new build.
- No automatic SD installation, vehicle restart, GEN2/DisplayManager
  mutation or guessed timing scalar.
- Verify no owner/bridge PID or session lock and native gate before next run.
- Use the existing supervisor for controlled SD-RW and typed stop.
- A new bounded same-map recording must discriminate writer preparation,
  successful syscalls, EAGAIN syscall time, actual sleep duration,
  and between-block bookkeeping from the older 0.55% clock observation.
