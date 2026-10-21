# Documentation

The pages here describe the **current public product/source, exact reference-target evidence and implementation interfaces**. Old dated experiments are retained only where they still explain a verified finding or an important limitation; they are not competing “current” plans.

## Start here

1. [Features and goals](../README.md)
2. [Current integration and evidence status](status/INTEGRATION_STATUS_2026-10-21.md)
3. [Exact public source coverage](status/PUBLISHED_SOURCE_COVERAGE.md)
4. [System architecture and SEAT/VW portability](architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md)
5. [OEM-native HMI and controller](architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md)
6. [Reference developer release](../release/CURRENT.md), [installation](INSTALLATION.md) and [compatibility matrix](testing/COMPATIBILITY_MATRIX.md)
7. [Current roadmap](../ROADMAP.md) and [known issues](findings/KNOWN_ISSUES.md)

## System interfaces

- **[Architecture module index and ownership guide](architecture/README.md)** — current authoritative page per subsystem, supporting historical references and release/source boundaries

- [Direct VC video](architecture/DIRECT_VC_VIDEO_PATH.md) · [ScreenAlt control](architecture/SCREENALT_CONTROL_PLANE.md) · [Source/owner runtime](architecture/RUNTIME_CONTRACT.md)
- [Auto-Direct reference runtime](architecture/AUTO_DIRECT_RUNTIME.md) · [Advanced developer switches](architecture/ADVANCED_RUNTIME_SWITCHES.md)
- [Navigation and SafeArea](architecture/NAVIGATION_COMPOSITION_AND_SAFEAREA.md) · [View-state overview](research/VC_VIEWAREA_STATE.md)
- [Optional real vehicle-data feature](architecture/OPTIONAL_VEHICLE_DATA_FEATURE_OVERVIEW.md)
- [Public MIBR/3 source-only protocol and owner mailbox](../src/experimental/mibr3/README.md)

## Vehicle evidence and testing

- [October reference observations: timing, video quality and disconnect classes](findings/OCTOBER_2026_VEHICLE_AND_TIMING_EVIDENCE.md)
- [Reference vehicle demonstration](media/mu1440-stream111-poc-2026-09-29/README.md)
- [Dated Final Drive checkpoint](status/MU1440_FINAL_DRIVE_LIVE_STATUS_2026-10-11.md) and [visual cadence limitations](findings/MU1440_ZOOM_CADENCE_OBSERVATION_2026-10-11.md)
- [Stream-111 fault isolation and recovery acceptance](testing/STREAM111_FAULT_ISOLATION_2026-10-21.md)
- [Measured physical wheel and head-unit input map; unknown IDs and contribution request](testing/MU1440_MFW_RAW_KEY_MAPPING.md) · [Safe vehicle test protocol](testing/VEHICLE_TEST_PROTOCOL.md) · [QNX shell compatibility](testing/MU1440_QNX_SHELL_COMPATIBILITY.md)

## Platform and advanced background

- [Firmware/cluster compatibility](testing/COMPATIBILITY_MATRIX.md) · [platform profile map](research/MHI2_FIRMWARE_PROFILE_MAP_2026-09-28.md)
- [GEN2 hook and reference ABI](research/MU1440_GEN2_HOOK_MAP.md) · [source-111 framing](research/STREAM111_PROTOCOL.md)
- [Research background index](research/README.md) · [native wireless prototype status](research/mhi2-native-wireless-2026-10/README.md)
- [Public technical references](research/PUBLIC_REFERENCES.md)

[Official-repository acknowledgements](../ACKNOWLEDGEMENTS.md) · [Third-party license notices](../THIRD_PARTY_NOTICES.md) · [Contributor instructions](../CONTRIBUTING.md) · [Privacy and security](../SECURITY.md). Internal audits, working handoffs and experiment tracking are not part of this public documentation index.
