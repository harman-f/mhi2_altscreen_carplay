# Documentation index

[Full current-tree documentation audit (22 October 2026)](maintainer/DOCUMENTATION_AUDIT_2026-10-22.md). The historic Final Drive evidence is linked from the current integration status; the experimental source and original operator ZIP were not automatically released.

**Detailed new guides:** [Native HMI / control plane](architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md) · [Stream-111 fault isolation](testing/STREAM111_FAULT_ISOLATION_2026-10-21.md) · [optional vehicle-data scope](architecture/OPTIONAL_VEHICLE_DATA_FEATURE_OVERVIEW.md).

**October 2026 starting points:** [current integration status](status/INTEGRATION_STATUS_2026-10-21.md) · [module responsibilities and SEAT/VW HMI portability](architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md) · [sanitized vehicle/timing evidence](findings/OCTOBER_2026_VEHICLE_AND_TIMING_EVIDENCE.md) · [public issue/publication policy](maintainer/ISSUE_AND_PUBLICATION_POLICY.md). The older 2026-10-05 research preview is a historical, mixed-evidence snapshot, not an installable current build.

## New contributor path

1. [System overview](architecture/SYSTEM_OVERVIEW.md)
2. [Direct VC video path](architecture/DIRECT_VC_VIDEO_PATH.md)
3. [Current October integration status](status/INTEGRATION_STATUS_2026-10-21.md) — latest cross-module evidence and separately qualified build/vehicle milestones
4. [Research topic index](research/README.md)
5. [ScreenAlt control plane](architecture/SCREENALT_CONTROL_PLANE.md)
6. [Historical implementation snapshot (2026-10-02)](status/CURRENT_DEVELOPMENT_STATUS.md)
7. [Known issues](findings/KNOWN_ISSUES.md)
8. [Roadmap](../ROADMAP.md)

## Architecture

- [System overview](architecture/SYSTEM_OVERVIEW.md)
- [Direct VC video path](architecture/DIRECT_VC_VIDEO_PATH.md)
- [ScreenAlt control plane](architecture/SCREENALT_CONTROL_PLANE.md)
- [Auto-Direct runtime](architecture/AUTO_DIRECT_RUNTIME.md)
- [Runtime contract](architecture/RUNTIME_CONTRACT.md)
- [NavIgnore / navigation arbitration](architecture/NAVIGNORE.md)

## Reverse engineering / research

- [Research topic index](research/README.md)
- **[MU1440 Tegra T30 CPU/clock/power/timebase and Stream-111 load (2026-10-11)](research/MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md)** — detailed read-only hardware research; no overclocking payload.

- [Current research preview — 2026-10-05](research/CURRENT_RESEARCH_PREVIEW_2026-10-05.md)
- [MU1440 stock component fingerprints](research/MU1440_STOCK_REFERENCE.md)
- [MU1440 GEN2 AirPlay hook / ABI map](research/MU1440_GEN2_HOOK_MAP.md)
- [Exact Audi MU1438 vs Skoda MU1440 offline comparison](research/MU1438_MU1440_OFFLINE_COMPARISON_2026-09-28.md)
- [MHI2 cross-firmware implementation profile map](research/MHI2_FIRMWARE_PROFILE_MAP_2026-09-28.md)
- [MHI2 patch portability estimate](research/MHI2_PATCH_PORTABILITY_ESTIMATE_2026-09-28.md) — per-firmware estimates for GEN2, Direct-TS, gate, NavIgnore and Java policy reuse
- [Audi B9 MU1438 compatibility lead and remaining gates](research/AUDI_B9_MU1438_COMPATIBILITY_LEAD_2026-09-28.md)
- [ScreenStream / Type-111 protocol](research/STREAM111_PROTOCOL.md)
- [CarPlay cluster / AltScreen configuration index (iOS 26.7.1)](research/CARPLAY_CLUSTER_CONFIGURATION_INDEX_IOS26_7_1_2026-10-01.md)
- [CarPlay cluster function / frontend-effect matrix (iOS 26.7.1)](research/CARPLAY_CLUSTER_FUNCTION_FRONTEND_MATRIX_IOS26_7_1_2026-10-01.md)
- [VC view-state / ViewArea research](research/VC_VIEWAREA_STATE.md)
- [iOS 27.2 sender lifecycle](research/IOS27_SENDER_LIFECYCLE.md)
- [PlatformControl flight recorder](research/PLATFORMCONTROL_FLIGHT_RECORDER.md)
- [Java / IBM J9 build notes](research/JAVA_J9_BUILD_NOTES.md)
- [Public prior art](research/PUBLIC_REFERENCES.md)
- [Comparator findings / non-portable traps](research/COMPARATOR_FINDINGS.md)
- [Research method](RESEARCH_METHOD.md)

## Testing

- [Compatibility matrix](testing/COMPATIBILITY_MATRIX.md)
- [Vehicle test protocol](testing/VEHICLE_TEST_PROTOCOL.md)
- [GEN2 experimental SSH workflow](testing/GEN2_EXPERIMENTAL_SSH.md)
- [direct-ts-remux SSH quickstart](testing/DIRECT_TS_REMUX_SSH_QUICKSTART.md)

## Current status

- [Current development status](status/CURRENT_DEVELOPMENT_STATUS.md)
- [Current research status](findings/CURRENT_RESEARCH_STATUS.md)
- [Known issues](findings/KNOWN_ISSUES.md)

## Publication / maintainers

- [Publication privacy](PUBLICATION_PRIVACY.md)
- [Repository setup](maintainer/REPOSITORY_SETUP.md)
- [Publication checklist](maintainer/PUBLICATION_CHECKLIST.md)

## Source / runtime entry points

- current GEN2 source: `../src/native/altscreen111-gen2/`
- direct remux source: `../src/native/direct-ts-remux/`
- DisplayManager write gate: `../src/native/isotx2-gate/`
- MOST test writer: `../src/native/most-ts-writer/`
- Auto-Direct reference runtime: `../runtime/auto-direct/`
- diagnostic helpers: `../runtime/diagnostics/`

Advanced readers who inspect the repository tree may find additional notes that are intentionally not
part of the beginner path.
