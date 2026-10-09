# Research index

This directory collects research that is useful to contributors before it becomes a vehicle-approved implementation.

> [!NOTE]
> Start with the [current research preview](CURRENT_RESEARCH_PREVIEW_2026-10-05.md). It summarizes the newest
> media/timing, HMI/menu and steering-wheel findings and clearly labels what is vehicle-proven vs static/design-only.

## Current cross-topic preview

- [Current research preview — 2026-10-05](CURRENT_RESEARCH_PREVIEW_2026-10-05.md)
  - source-timestamp / AU / MPEG-TS design;
  - configurable frame/time keyframe policy;
  - DMDT vs vehicle-proven writev ownership;
  - dual ViewArea/SafeArea direction;
  - HMI settings registry;
  - menu/ViewHandler and steering-wheel findings.

## Native Wireless CarPlay (separate, experimental project)

- [Wireless research handoff](mhi2-native-wireless-2026-10/README.md) — one starting point for the October 2026 study.
- **[Firmware and iOS binary findings ↔ actual prototype source](mhi2-native-wireless-2026-10/FIRMWARE_SOURCE_CROSS_REFERENCE.md)** — module-by-module links to research and project-authored C/H/INC/tests.
- [Prototype source and publication review](mhi2-native-wireless-2026-10/prototype/README.md) · [source hash manifest](mhi2-native-wireless-2026-10/prototype/SOURCE_MANIFEST.tsv).

**Scope warning:** this Wireless bootstrap/session prototype is not vehicle-validated; it is independent of the vehicle-tested Stream-111 / Virtual Cockpit path below. Proprietary firmware binaries are not included.

## CarPlay / Stream-111 / control plane

- [Stream-111 protocol](STREAM111_PROTOCOL.md)
- [CarPlay cluster configuration index](CARPLAY_CLUSTER_CONFIGURATION_INDEX_IOS26_7_1_2026-10-01.md)
- [CarPlay cluster function / frontend-effect matrix](CARPLAY_CLUSTER_FUNCTION_FRONTEND_MATRIX_IOS26_7_1_2026-10-01.md)
- [iOS sender lifecycle](IOS27_SENDER_LIFECYCLE.md)
- [PlatformControl flight recorder](PLATFORMCONTROL_FLIGHT_RECORDER.md)
- [VC ViewArea state](VC_VIEWAREA_STATE.md)

## HMI / settings / input

- [MU1440 HMI menu and ViewHandler architecture](../architecture/MU1440_HMI_MENU_AND_VIEWHANDLER_ARCHITECTURE.md)
- [MU1440 steering-wheel / hardkey API](MU1440_BUTTON_INPUT_API.md)
- [Java / IBM J9 build notes](JAVA_J9_BUILD_NOTES.md)

Current status:

```text
menu/ViewHandler architecture        exact-target static + compile-only PoC
WidgetFactory injection              offline/build-proven, not vehicle-proven
steering-wheel ASL APIs              exact-target static
final physical button binding        open / requires vehicle trace
```

## Media / transport / comparator research

- [Comparator findings / non-portable traps](COMPARATOR_FINDINGS.md)
- [Omonob 790/791 artifact audit](OMONOB_790_791_ARTIFACT_AUDIT_2026-10-03.md)
- [Omonob 791 30-fps / 1-s IDR test plan](OMONOB_791_30FPS_1S_IDR_TEST_PLAN_2026-10-03.md)
- [Direct VC video path](../architecture/DIRECT_VC_VIDEO_PATH.md)
- [Keyframe recovery vehicle finding](../findings/KEYFRAME_RECOVERY_2026-09-27.md)

The newest parity/keyframe/ownership design is summarized in the
[current research preview](CURRENT_RESEARCH_PREVIEW_2026-10-05.md) and is intentionally marked unvalidated
until the next vehicle run.

## Firmware / platform portability

- [MU1440 stock reference](MU1440_STOCK_REFERENCE.md)
- [MU1440 GEN2 hook map](MU1440_GEN2_HOOK_MAP.md)
- [MHI2 firmware profile map](MHI2_FIRMWARE_PROFILE_MAP_2026-09-28.md)
- [MHI2 patch portability estimate](MHI2_PATCH_PORTABILITY_ESTIMATE_2026-09-28.md)
- [MU1438 vs MU1440 comparison](MU1438_MU1440_OFFLINE_COMPARISON_2026-09-28.md)
- [Audi B9 compatibility lead](AUDI_B9_MU1438_COMPATIBILITY_LEAD_2026-09-28.md)
- [Cluster/display transport knowledge base](MIB2_CLUSTER_DISPLAY_TRANSPORT_KNOWLEDGE_BASE.md)
- [FPK firmware/control access](FPK_FIRMWARE_AND_CONTROL_ACCESS.md)

## Prior art and methodology

- [Public references](PUBLIC_REFERENCES.md)
- [Research method](../RESEARCH_METHOD.md)
- [Acknowledgements](../../ACKNOWLEDGEMENTS.md)

## Evidence rule

Please preserve this distinction when contributing:

```text
vehicle-proven
  !=
exact-target static
  !=
offline/build-proven
  !=
design/inference
```

A useful research result can be published before vehicle validation as long as its evidence class is explicit.
