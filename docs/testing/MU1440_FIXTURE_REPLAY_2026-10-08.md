# MU1440 AID10: bounded synthetic M1AU replay (2026-10-08)

Status: draft PR #24; **CI #300 SUCCESS** (host selftests, QNX ARMv7 pair build, binary/contracts/immutable package audit); NOT VEHICLE-TESTED, deployment package still being finalized. No automatic installation/reboot/boot hook. Requires stationary vehicle.

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

Exact original, verified vehicle baseline CI #295:
- `direct-ts-parity` SHA256 `a6f9e64d807c8ebb827634eb7b1e0421f8b0961329a76bee3a2ad361bf4fad3b`
- `parity-session` SHA256 `a0422a36f245b3dd5a4dd88a6bc930ba007c8993489a2ee402b6b33e72c820c7`

CI #300 exact build commit `41a472211a1572d0548aaab9f6d6bee4df5cc3e9`:
- QNX `direct-ts-parity` SHA256 `7fa78266b2df3106e1e6372c8873cdfca4d318999262e82b35291bb7ca8a0b8b`
- QNX `parity-session` SHA256 `441cd1436a94e0a7f4f5f76820646c7f3195984ff1036771b909b6af3f2aaca7`
- Full green workflow `https://github.com/harman-f/mhi2_altscreen_carplay/actions/runs/37849991704`; green integrity `https://github.com/harman-f/mhi2_altscreen_carplay/actions/runs/37849991705`; QNX artifact ID `11582002481`.
- This verifies the *compiled binary pair*, **not** presentation on AID10. Later docs/tools commits do not modify that build's binary identity; if native source changes, request new CI and re-hash.

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
- Pinned QNX-6.5 ARMv7 CI rebuilt the paired writer and owner at CI #300; every build, test and audit stage completed SUCCESS. No in-car fixture result yet.
- Install stage has to verify both CI binaries, fixture SHA and exact-head logs.
- All previous PRs remain draft and unmerged. No live iPhone connection required; if gate cannot establish tracked native writes, abort and retain stock display.

## Reusable diagnostic tool and preservation policy

**Keep the fixture support after the one-shot vehicle experiment.** The following complete
open-source contract remains on PR #24 for future troubleshooting:

- `tools/fixtures/generate_mu1440_motion_m1au.py`: host-side pattern generator,
  H.264 AUD/IDR/Annex-B verifier, 56-byte M1AU wrapper and SHA256 manifest.
  It regenerates a visually comparable clip and explicitly marks a mismatch
  with the first frozen fixture; it does *not* claim binary-identical x264 output.
- `src/native/direct-ts-parity/direct_ts_parity.c`: test-only, fixed-path M1AU
  source reader with timestamp-driven absolute 30fps pacing and shared output stages.
- `src/native/parity-session/parity_session.c`: bounded explicit offline fixture
  mode with the normal native gate, watchdog, bound process and restore.
- `deployment/mu1440-fixture-replay-v1/MU1440_REPLAY_RUN.sh`: no-boot, foreground
  operator with preflight, status, stop and SD telemetry.
- `tests/test_mu1440_fixture_replay.py`: negative preflight and CLI safety tests.
- `docs/testing/MU1440_FIXTURE_REPLAY_2026-10-08.md`: data and safety authority.

Archive the **original fixture bytes** separately: they are not committed to
Git, and the current vehicle binary requires SHA256
`e853dbf2d690e534f9020fd3c206550ca44177408d3d2c5d20f2f863645724b9`.
If the clip gets regenerated or altered, do NOT bypass this check. Issue a
new named fixture revision and build/source hash contract.

### Prior measured LIVE baseline, for comparison

CI #295 current real-CarPlay drive:
- 112.948s accepted-write monotonic window, 14,342 accepted 12,032-byte blocks;
- accepted-block count implies 112.345667s nominal TS time or -5,332.84ppm
  against monotonic elapsed (602.333ms *count-model* accumulation);
- source 32.32 progressed 112.950s and source arrival assigned 112.951s;
- 54,207 EAGAIN retry loops; 108.706s aggregate actual `usleep(1000)`
  occupancy, mean 2.00539ms, **not 108s provable avoidable wall delay**;
- 3,574 completed AUs (181 IDR / 3,393 P), zero gaps/write errors and
  typed owner stop `complete_stock`.

These are acceptance-boundary observations, *not* verified MOST physical
drain timing or AID10 presented-frame timing. The source-vs-downstream
diagnosis is the purpose of this fixture. An older 20fps direct-TS test was
not timing-equivalent: it bypassed the M1AU/PTS/PCR logic.

Canonical full research checkpoint, committed directly to Research `main`:
`projects/mhi2-altscreen-thirdparty-audit/analysis/MU1440_CARPLAY_LIVE_CI295_AND_FIXTURE_REPLAY_MASTER_2026-10-08.md`.

**Correction:** a previously exported local JSON erroneously gave 385 for
`accepted_blocks_delta` (last interval only). Read samples #2 and #37:
14,721-379=**14,342**. Do not reuse corresponding erroneous ppm/nominal
duration; the corrected values are above and in Research.
