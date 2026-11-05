# Media transport, MOST and implementation comparisons

[Research library](../README.md) · [Current CarPlay module](../../../modules/carplay/) · [Current evidence](../../status/FEATURE_STATUS.md)

This area studies the auxiliary H.264 media path, MPEG-TS/MOST output and external reference implementations. **Comparator behavior is not proof that a different MIB2 firmware or cockpit will run the same binary.**

## Reference and comparator studies

- **[Comparator findings](COMPARATOR_FINDINGS.md)** — architecture and portability traps across public alternatives.
- **[Omonob 790/791 artifacts](OMONOB_790_791_ARTIFACT_AUDIT_2026-10-03.md)** — producer, frame/IDR handling and bridge behavior observed by static review.
- **[MU1440 GEN2 hook map](MU1440_GEN2_HOOK_MAP.md)** — historical receiver/hook chain, ABI and interception points.

## Open experiments and proposed optimizations

- **[Omonob 791 30-fps / 1-s IDR plan](OMONOB_791_30FPS_1S_IDR_TEST_PLAN_2026-10-03.md)** — **proposal/test plan**, not a measured installation or endorsed patch.

Current authoritative material: [direct VC video architecture](../../architecture/DIRECT_VC_VIDEO_PATH.md), [stream fault isolation](../../testing/STREAM111_FAULT_ISOLATION_2026-10-21.md), [keyframe recovery finding](../../findings/KEYFRAME_RECOVERY_2026-09-27.md) and [source coverage](../../status/PUBLISHED_SOURCE_COVERAGE.md).

[CarPlay protocol research](../carplay/README.md) · [Research/archival rules](../AGENTS.md).
