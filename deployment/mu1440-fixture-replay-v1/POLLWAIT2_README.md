# MU1440 Pollwait-v2 — bounded diagnostic follow-up (research only)

**NOT INSTALLED / NOT VEHICLE-VALIDATED.** This stacked follow-up to draft PR #31 diagnoses, but does not remove, its safe POLLOUT fallback. The two 2026-10-10 hardware sessions used pollwait-v1: legacy 150s and `poll` 150s. On `/dev/mlb/isoTX2`, opt-in poll produced 3 ready events, 0 measured poll-wait microseconds, 1 fallback and `writer_poll_disabled=1`; the 150s session finished with 0 write errors, clean owner exit, and stock native gate. Neither these results nor the visually smooth map transition establish an improvement from POLLOUT (fallback occurred within the first seconds).

## Scope and preserved safety invariants

The writer now retains at most the first four poll attempts in writer-thread-local memory and emits a bounded `PARITY_POLL_FALLBACK` record plus `PARITY_POLL_SAMPLE` records to stderr/session.log **once, only upon fallback**. Each sample records requested timeout, exact poll return code and errno, revents bitmask, measured poll elapsed microseconds, whether a subsequent write was attempted, requested bytes, write result and errno, delay between poll return and write entry, and write syscall elapsed microseconds. A missing follow-up to the terminal poll is explicitly flagged. Status also includes `writer_poll_diag_samples` and `writer_poll_disable_reason` (none / poll_syscall_error / poll_error_revents / poll_missing_pollout / immediate_ready_3 / ready_then_eagain_3). Zero elapsed times may reflect coarse QNX monotonic resolution; never infer a truly zero-latency operation.

No changes to `MIBR_PARITY_EAGAIN_WAIT` opt-in contract, three-immediate-ready / three-ready-then-EAGAIN fallback thresholds, 2ms maximum poll hint, 1ms legacy sleep request, 500ms complete-block write timeout, 12032-byte block acceptance, source/PCR/PTS, native gate, or boot/autostart. Fixture never enables the experimental poll strategy.

## Independent `pollwait-v2/` artifact (seven files)

`direct-ts-parity`, `parity-session`, `PAIR_SHA256SUMS.txt`, `MU1440_POLL2_SWAP.sh`, `MU1440_POLL2_LIVE.sh`, `MU1440_POLL2_FIXTURE.sh`, and this `POLLWAIT2_README.md`. CI fills new pair hashes into the swap script, validates both binary hashes and script syntax. CI/host results are not vehicle validation.

- SD: `/net/mmx/fs/sda0/esd/carplay-test/omonob-clock-test/pollwait-v2`
- Original installed baseline required **exactly**: pollwait-v1 bridge SHA256 `10350fb7dc715ec9b99c6b2acadb2a1b3e2ac7342c9281ca57e889fd7d3a4e31`, owner SHA256 `232cc5f76feb105230712afd902d0c053339a94051ed8c6910a4e79c388b90ec`.
- Independent immutable rollback storage: `/mnt/app/root/mibr-pollwait-v2-backup`; this contains the v1 pair, never CI314. The existing `pollwait-v1/` folder and `mibr-pollwait-v1-backup` (CI314 pair) are untouched.
- Fail closed on unknown/mixed pair, active owner/bridge/supervisor, enabled autostart, non-stock native gate, mismatched SD hashes, partial or corrupt backup. Installing two executable paths is *not power-loss-atomic*: do not start CarPlay after an interrupted install until both hashes have been verified and an operator has recovered if needed.
- Backout order: v2 restore returns to the verified v1 pair; only after v2 restore and v1 verification may the separate v1 toolkit restore CI314. Do not use v1 restore on an active v2 pair.

## Operator-gated vehicle instructions (only after CI and independent package validation)

With car parked, native gate stock, no owner running, CarPlay source streaming before live preflight, and no concurrent session:

```sh
D=/net/mmx/fs/sda0/esd/carplay-test/omonob-clock-test/pollwait-v2
/bin/ksh -n "$D/MU1440_POLL2_SWAP.sh"
/bin/ksh -n "$D/MU1440_POLL2_LIVE.sh"
/bin/ksh -n "$D/MU1440_POLL2_FIXTURE.sh"
/bin/ksh "$D/MU1440_POLL2_SWAP.sh" status
/bin/ksh "$D/MU1440_POLL2_SWAP.sh" install
/bin/ksh "$D/MU1440_POLL2_SWAP.sh" verify
/bin/ksh "$D/MU1440_POLL2_LIVE.sh" preflight
MIBR_PARITY_EAGAIN_WAIT=poll /bin/ksh "$D/MU1440_POLL2_LIVE.sh" start
```

The last command is a bounded **foreground 150-second** run, not an autostart. Once complete, inspect `pollwait2-live-*/session.log` for `PARITY_POLL_FALLBACK` / `PARITY_POLL_SAMPLE`, alongside `parity-final.status`, `summary.txt`, `gate-final.status`, and `status-snapshots.log`. Never conflate the expected `PARITY_EXIT reason=signal_stop` for a bounded owner stop with a crash. If anything fails or gate/owner are not stock, do not start another test until verified.

This experiment determines **why** the fallback happened, not whether kernel-side MOST queue drain matches accepted writes. It does not by itself solve the persistent ~-0.44% acceptance-clock model discrepancy.
