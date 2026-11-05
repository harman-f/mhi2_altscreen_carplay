# Documentation hub — MIB Runtime

Start with the information you need. **Current source, released packages and vehicle observations are separate evidence levels.** Dated research reports remain available but do not override this index or the status tables.

## Explore the project

- **[Overview and reference-vehicle demonstration](../README.md)** — what the project does, picture and main safety limitations.
- **[Feature and evidence status](status/FEATURE_STATUS.md)** — which features exist in source, which have been seen on a vehicle and which still need acceptance.
- **[Firmware and cluster compatibility](testing/COMPATIBILITY_MATRIX.md)** — exact target identities, not generic brand support.
- **[Current three-profile test matrix](testing/MULTI_PROFILE_TESTING.md)** — Škoda MU1440 and SEAT MU1409/MU1447; evidence and test requests.

## Packages, installers and updates

- **[Packages and release status](packages/README.md)** — legacy MU1440 package versus modular three-profile beta, plus what a PASS means.
- [Developer installation and known target prerequisites](INSTALLATION.md) — **historical MU1440 developer package**, not universal instructions.
- [Frozen reference release](../release/CURRENT.md) — exact historical artifacts and SHA-256.
- [New package structure and manifests](build/PACKAGE_LAYOUT.md) — common modules, firmware profiles, J9 inputs and final ZIP gate.
- [Configuration defaults and application timing](configuration/DEFAULT_CONFIGURATION_MATRIX.md) — 48 CarPlay keys, 13 broker switches, presets versus firmware profiles.

## Technical development

- [Architecture and canonical interfaces](architecture/README.md) · [Module and source ownership](../modules/) · [Repository organization](architecture/REPOSITORY_LAYOUT.md)
- [MIB Runtime: firmware profiles, configuration, migration](architecture/FIRMWARE_PROFILES_AND_CONFIGURATION.md) · [On-unit storage contract](architecture/UNIT_STORAGE_AND_NAMING_CONTRACT.md)
- [CarPlay/video](../modules/carplay/) · [Broker/input](../modules/broker/) · [Java menu](../modules/menu/) · [Navigation/RGI](../modules/navigation/) · [Profiles](../modules/profiles/)
- [Source coverage and external dependencies](status/PUBLISHED_SOURCE_COVERAGE.md)
- [QNX toolchain](build/QNX_TOOLCHAIN_IMAGE.md) · [Menu and RGI build](build/MU1440_MENU_RGI_SOURCE.md) · [SDK entry point](../sdk/)
- [Default-menu editor](../tools/menu-editor/mibr-menu-editor.html) · [Menu format](../tools/menu-editor/MENU_FILE_FORMAT.md)
- [Developer runtime switches](architecture/ADVANCED_RUNTIME_SWITCHES.md) · [Vehicle test protocol](testing/VEHICLE_TEST_PROTOCOL.md)

## Validation and contribution

- [Three-profile tester report and acceptance limits](testing/MULTI_PROFILE_TESTING.md)
- [Stream 111 diagnostics and recovery](testing/STREAM111_FAULT_ISOLATION_2026-10-21.md)
- [Known issues](findings/KNOWN_ISSUES.md) · [Roadmap](../ROADMAP.md) · [Contributing](../CONTRIBUTING.md) · [Security](../SECURITY.md)
- [SEAT port background](porting/SEAT_CUPRA_MU1409_COLLABORATION.md) and [key-input capture](porting/SEAT_CUPRA_KEY_INPUT_CAPTURE_HANDOFF.md)

## Research and historic evidence

- **[Research index](research/README.md)** — dated firmware, video and input investigations, including wireless CarPlay.
- **[October vehicle observations](findings/OCTOBER_2026_VEHICLE_AND_TIMING_EVIDENCE.md)** and [21 October integration snapshot](status/INTEGRATION_STATUS_2026-10-21.md).
- **[Reference visual evidence](media/mu1440-stream111-poc-2026-09-29/README.md)**.
- **[AltScreen Cluster Atlas](index.html)** — independent MIB2/MHI2/MST2 comparison. When GitHub Pages is enabled from `main/docs`, it may also be accessible at `https://harman-f.github.io/mhi2_altscreen_carplay/`.

Historical documents keep their original dates and claims. Do not rewrite an archived test result to imply newer binaries were installed. The latest *source* and the latest *vehicle-tested release* are different things.

[Rights and attribution](../THIRD_PARTY_NOTICES.md) · [Privacy/publication](PUBLICATION_PRIVACY.md)
