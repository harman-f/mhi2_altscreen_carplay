# MU1440 AID10: bounded synthetic M1AU replay (2026-10-08)

Status: draft PR #24; **CI / matched QNX binary qualification required**. No automatic installation, no reboot and no run from boot. Requires stationary vehicle.

## Target

MHI2 ER SKG13 P4526 MU1440, AID10, existing GEN2 / exact-candidate writev_gate and the already established 12032-byte direct isoTX2 parity writer.

Fixture is already on vehicle SD:

`/net/mmx/fs/sda0/esd/carplay-test/fixtures/mu1440-motion-v1/mu1440_motion_1010x376_30fps_gop20.m1au`

- file length: 23,275,739 bytes
- fixture SHA256: `e853dbf2d690e534f9020fd3c206550ca44177408d3d2c5d20f2f863645724b9`
- 3600 complete Annex-B H.264 M1AU records, 1010×376 / 30fps / 120sec, 180 IDR + 3420 P, GOP20 and 32.32 timestamps.
- target source average 1.54Mbit/s, no B-frames.
- precisely pinned URI; no path overrides, no arbitrary socket/file reader.

## Implementation

**No second writer or TCP listener.** The installed direct-ts-parity binary accepts only the exact `fixture:/...` URI. It uses a read-only regular SD file, an absolute CLOCK_MONOTONIC 30-fps source pacer with maximum 100ms accumulated lateness (else FAIL), original M1AU headers and original source 32.32 timestamps. From the AU normalization step onward, source PTS/PES, PCR/PAT/PMT, TS, /dev/mlb/isoTX2 and MOST writer are *identical* to the live pathway. Source file EOF must occur after exactly 3600 validated sequential frames.

Session owner command:

`parity-session --fixture /mnt/app/root/altscreen-u2/bin/direct-ts-parity fixture:/net/mmx/fs/sda0/esd/carplay-test/fixtures/mu1440-motion-v1/mu1440_motion_1010x376_30fps_gop20.m1au /dev/mlb/isoTX2 150`

This is **not** an operator command: use the SD script that preflights/collects logs and has a typed stop. The owner bypasses only the normal requirement for an *already streaming CarPlay source*; it instead requires CarPlay disconnected and preserves the exact pinned bridge SHA, watchdog, session lock, tracked native writev gate, monotonic token, drop acknowledgement, process identity, bounded stop and native STOCK restore. Owner runtime immediately stops if a live source becomes active.

**No idle bypass of the native MOST gate:** If stock cannot prove an active tracked write while the bridge waits, gate takeover fails after its existing five-second window, and no custom video is started. Do not weaken this gate to make replay work. If this happens, first bring up a stock native VC navigation display and confirm the gate can observe stock writes.

## SD operator package

New SD-only package path:
`/net/mmx/fs/sda0/esd/carplay-test/omonob-clock-test/fixture-replay-v1/`

Includes same-HEAD CI binaries `direct-ts-parity`, `parity-session`, `MU1440_REPLAY_RUN.sh`, `MU1440_REPLAY_SWAP.sh`, `PAIR_SHA256SUMS.txt`, instructions. Existing video stays in the separate fixtures directory. No copying GEN2 or DisplayManager modules.

The installed CI #295 binary pair is the only authorized starting point for a swap. Never mix bridge and owner build hashes. The installer must backup and verify both CI #295 hashes before altering /mnt/app, install both atomically enough for rollback, and remount /mnt/app read-only; stop and restore require the native gate proof.

Operator after installer verification (QNX, stationary vehicle; iPhone disconnected):
- `/bin/ksh .../fixture-replay-v1/MU1440_REPLAY_RUN.sh preflight`
- `/bin/ksh .../fixture-replay-v1/MU1440_REPLAY_RUN.sh start` (foreground, ~120 sec)
- `/bin/ksh .../fixture-replay-v1/MU1440_REPLAY_RUN.sh status` (optional second SSH)
- `/bin/ksh .../fixture-replay-v1/MU1440_REPLAY_RUN.sh stop` (only when necessary; typed owner stop)

The runner rejects a concurrently enabled parity-drive supervisor, a live CarPlay stream, wrong bridge/owner fingerprints, wrong fixture hash, any stale session lock or non-stock native gate. It mounts SD writable for logs, samples 3-second parity snapshots into a fixture-specific run folder, and finally records parity-final.status, gate-final.status, session.log and summary.txt. It returns SD to read-only after owner lock release; no startup hook is changed.

Failure of the **opt-in fixture** is NOT proof that live CarPlay path is broken. Likewise successful 3600-frame accepted video is not proof that the VC presents every frame. Visually observe the moving diagonal and on-video frame counter. If P frames are decoded only on GOP boundaries, look for visible jumps every 20/30=0.667 s.

## Tests and release gates

- Host semantic suite and `direct-ts-parity --self-test` exercise the exact fixture timing and fail closed on invalid sequence.
- New host tests reject wrong path, arbitrary output, too-short replay and malformed CLI.
- Pinned QNX-6.5 ARMv7 CI rebuilds the paired writer and owner and audits immutable binary identity. Await green status.
- Install stage has to verify both CI binaries, fixture SHA and exact-head logs.
- All previous PRs remain draft and unmerged. No live iPhone connection required; if gate cannot establish tracked native writes, abort and retain stock display.
