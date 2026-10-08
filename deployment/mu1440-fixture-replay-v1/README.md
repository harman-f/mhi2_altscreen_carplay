# MU1440 M1AU Offline Replay — permanent diagnostic toolkit

**Status:** PR #24 remains draft. CI #300 compiled both QNX native binaries successfully; no offline vehicle result yet.

## Source to retain for future diagnoses

- `tools/fixtures/generate_mu1440_motion_m1au.py` — deterministic-structure generator: moving diagonal, frame index, H.264 Annex-B AUD / IDR, 56-byte M1AU wrapper, source 32.32 timestamps, sha256 audit. Newly generated media may have a different file hash; never substitute silently.
- `src/native/direct-ts-parity/direct_ts_parity.c` — fixed fixture input, 30fps absolute monotonic pacing, shared live PTS/PCR and MOST writer.
- `src/native/parity-session/parity_session.c` — opt-in bounded fixture mode; same identity-checked bridge, watchdog, exclusive native gate and stock restore.
- `deployment/mu1440-fixture-replay-v1/MU1440_REPLAY_RUN.sh` — QNX preflight / foreground start / status / stop + SD logging.
- `deployment/mu1440-fixture-replay-v1/MU1440_REPLAY_SWAP.sh` — reversible exact paired swap CI295 <-> CI300.
- `tests/test_mu1440_fixture_replay.py` — negative host safety regression tests.
- `docs/testing/MU1440_FIXTURE_REPLAY_2026-10-08.md` — detailed contract, source/measurement comparisons.

## Fixed original reference video (already on vehicle SD)

`/net/mmx/fs/sda0/esd/carplay-test/fixtures/mu1440-motion-v1/mu1440_motion_1010x376_30fps_gop20.m1au`

Size 23,275,739 bytes, 1010×376, 30fps for 120 seconds, 3,600 AU, 180 IDR, 3,420 P, no B. GOP20. SHA256: `e853dbf2d690e534f9020fd3c206550ca44177408d3d2c5d20f2f863645724b9`.

This binary media is **not committed in Git**. Keep the original file on SD plus a copy outside the car. Source generation scripts are future-proofing, not a byte-identical reproduction guarantee.

## QNX CI paired identities

- Live baseline CI295 `direct-ts-parity`: `a6f9e64d807c8ebb827634eb7b1e0421f8b0961329a76bee3a2ad361bf4fad3b`.
- Live baseline CI295 `parity-session`: `a0422a36f245b3dd5a4dd88a6bc930ba007c8993489a2ee402b6b33e72c820c7`.
- Fixture CI300 `direct-ts-parity`: `7fa78266b2df3106e1e6372c8873cdfca4d318999262e82b35291bb7ca8a0b8b`.
- Fixture CI300 `parity-session`: `441cd1436a94e0a7f4f5f76820646c7f3195984ff1036771b909b6af3f2aaca7`.

CI #300: https://github.com/harman-f/mhi2_altscreen_carplay/actions/runs/37849991704 ; integrity https://github.com/harman-f/mhi2_altscreen_carplay/actions/runs/37849991705 . New packaging commits require checking their own release artifact.

## Small SD overlay (video remains separate)

Place both exactly matching QNX native files, SHA manifest and two scripts in:

`/net/mmx/fs/sda0/esd/carplay-test/omonob-clock-test/fixture-replay-v1/`

Run from a parked vehicle, iPhone disconnected, after hash/stock/owner preflight; never run two MOST writers. No reboot, no stock process restart. Commands are the complete path to `MU1440_REPLAY_SWAP.sh` followed by `install`, `verify`, `preflight`, `start`, `status`, `stop`, or `restore` (one command per SSH paste). The owner requires native stock gate write/drop acknowledgement; do not bypass it to make an offline video appear.

Replay starts in foreground for ~120 seconds and stops automatically. Owner has a 150-second maximum. Logs to `/net/mmx/fs/sda0/esd/carplay-test/logs/parity-drive/fixture-*/` with session, snapshots, final parity and gate status. Restore the original CI295 pair when stock is confirmed.

## The A/B diagnosis

- Fixture fluid but Apple map stutters: suspect Apple/GEN2 source jitter, encoding, timestamp irregularity, lifecycle.
- Both stutter: suspect common M1AU PTS/PCR, TS pacing, MOST or AID display.
- ~0.667-second picture jumps: potentially IDR-only presentation despite accepted P-frame counts.
- Initial-only jerks followed by smooth output: prioritize startup priming / decoder buffer / mode switching.

Accepted 12,032-byte blocks are NOT direct evidence of physical MOST bit clock or decoded AID10 presentation.

Full CI295 vehicle experiment and evidence: https://github.com/CaneTLOTW/M.I.B._Research/blob/main/projects/mhi2-altscreen-thirdparty-audit/analysis/MU1440_CARPLAY_LIVE_CI295_AND_FIXTURE_REPLAY_MASTER_2026-10-08.md
