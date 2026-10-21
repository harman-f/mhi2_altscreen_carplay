# Diagnostic source fixtures: MU1440 AID10 M1AU

This folder is permanent, vehicle-independent host diagnostic source. It is safe to keep on the public `main` branch without merging any experimental native MOST-control code.

## Why this fixture exists

The old `direct-test-1010x376-20fps.ts` bypassed M1AU/PTS/PCR and could not distinguish a faulty source clock from a downstream transport/display problem. The new 120-second, 30fps reference clip uses proper H.264 Annex-B frames, IDR/P GOP20, M1AU framing and 32.32 timestamps. A highly visible moving diagonal and frame counter expose held/repeated pictures and IDR-only presentation. The test must be injected before the normal parity mux, not as a premuxed TS directly into MOST.

## Frozen first test media (not included in Git)

- Filename: `mu1440_motion_1010x376_30fps_gop20.m1au`
- Vehicle SD: `/net/mmx/fs/sda0/esd/carplay-test/fixtures/mu1440-motion-v1/`
- Size: 23,275,739 bytes; SHA256: `e853dbf2d690e534f9020fd3c206550ca44177408d3d2c5d20f2f863645724b9`
- 1010×376, H.264 High L3.1, 3600 AUs, 180 IDR + 3420 P + 0 B, GOP20, nominal 30fps and 1.538 Mbps.
- 56-byte M1AU v1 header: BE magic/version/length/flags/generation IDs/sequence; LE 32.32 time fields at offsets 0x30, 0x34.

## Host regeneration utility

`python3 tools/fixtures/generate_mu1440_motion_m1au.py --output /tmp/mu1440-fixture`

Requires Python3 with numpy and ffmpeg/libx264. Emits `.h264`, `.m1au`, `AUDIT.json`, includes frame count/GOP/header checks and SHA256 fingerprints. **Not a byte-identical reconstruction guarantee** of the frozen first file; do not overwrite the old file or bypass the QNX pinned fixture SHA. Create a new named fixture revision for new bytes.

## Safe QNX playback tool (not merged)

Opt-in replay source, owner, bounded control and rollback remain isolated in [draft PR #24](https://github.com/harman-f/mhi2_altscreen_carplay/pull/24), branch `work/mu1440-fixture-replay-v1`. This ensures the untested iPhone-free native gate takeover is not silently enabled in production/main. Native pair CI #300 built green at SHA `41a472211a1572d0548aaab9f6d6bee4df5cc3e9`; later exact-hash packaging CI [#301](https://github.com/harman-f/mhi2_altscreen_carplay/actions/runs/37852559790) provides both scripts and a binary manifest when completed. Neither CI run is a live in-car AID10 display test.

Research evidence and original live CI295 baseline: a retained offline source comparison.

Preserve this directory, the Research handoff, and the original hashed fixture. New fixture versions can then be generated without reconstructing the protocol, codec or visual test design from old chats.
