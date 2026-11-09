# MHI2 AltScreen CarPlay — MIB Runtime

**Experimental CarPlay navigation and integration for selected Volkswagen Group MHI2 infotainment units and instrument clusters.** The project provides a secondary CarPlay video path (type/stream 111), guarded output to the Virtual Cockpit, an OEM-style menu, a native broker, navigation controls, and exact firmware-specific adapters.

> [!WARNING]
> **Research and developer software, not a production-ready vehicle product.** The software can disrupt the infotainment system, original navigation or cluster output. Use exact firmware/component checks, verified backups and an independent recovery route. Perform installation and interactive tests only while safely parked. **Do not rely on experimental cluster output for driving or safety-critical information.**
>
> No universal compatibility, manufacturer endorsement, warranty or vehicle safety qualification is claimed. The [GPL-3.0-or-later license](LICENSE) does not grant rights to OEM firmware or other third-party assets. See [security and test guidance](SECURITY.md) and [third-party notices](THIRD_PARTY_NOTICES.md).

## What it does

On the **Škoda MU1440/AID10 reference vehicle**, live auxiliary CarPlay maps from **Apple Maps, Google Maps and Waze** have been displayed in the Virtual Cockpit. Additional development has produced a native menu and controller, ViewArea/SafeArea configuration, input and zoom experiments, and navigation/route-guidance components. **These observations come from different tested configurations; they are not a claim that one current download contains every feature.**

![Waze displayed on the reference Virtual Cockpit](docs/media/mu1440-stream111-poc-2026-09-29/waze_vc_stream111_photo_public_minblur.jpg)

| Capability | Public implementation | Physical-vehicle / release evidence |
| --- | --- | --- |
| Live CarPlay map in the Virtual Cockpit | Auxiliary type-111 receiver, H.264/MPEG-TS/MOST path and guarded STOCK handback | Demonstrated on the exact Škoda reference; later integrated source and other targets need separate acceptance |
| OEM-native HOME / settings and physical controls | Shared Java menu, MIBR broker, firmware-specific adapters, settings registry | Reference development tests; latest Java/profile integration not fully vehicle-qualified |
| Three presentation layouts, SafeArea and zoom | Shared settings and display/input controls | Partial vehicle observations; per-option APPLY/ACTIVE and focus/reconnect behavior still need proof |
| Navigation arrows and route guidance | Menu options, broker navigation switches and Route Guidance (RGI) source | **Phone-sourced turn arrows are OFF by default**; stored options or source code do not prove live visible arrows |
| Vehicle data, diagnostics and optional extensions | Experimental source and bounded integration interfaces | Phone/vehicle acceptance pending; not a qualified release feature |

[Detailed feature/evidence matrix](docs/status/FEATURE_STATUS.md) · [Reference photos and video](docs/media/mu1440-stream111-poc-2026-09-29/README.md) · [Current source coverage](docs/status/PUBLISHED_SOURCE_COVERAGE.md)

## Firmware profiles: source availability is not vehicle support

| Firmware profile | Current status |
| --- | --- |
| **Škoda MU1440 P4526** | Exact AID10-class reference vehicle has demonstrated the auxiliary CarPlay video path. The newer unified runtime/installer still requires its own end-to-end acceptance. |
| **SEAT MU1409 P4708** | Exact firmware hash, profile, Java adapter source and shared runtime integration exist; OEM-menu rendering, arrows and CarPlay output have **not** been qualified in a project vehicle test. |
| **SEAT MU1447 P4709** | Exact firmware hash, profile and separate Java adapter lineage exist; independent J9/vehicle acceptance remains outstanding. |

The **installer selector** recognizes all three listed original `/ifs/lsd.jxe` SHA-256 fingerprints and checks the firmware train. This is source-level eligibility, **not** proof of compatibility with an arbitrary vehicle or dashboard. `P4708_1` is **not** equivalent to `P4708` without independent evidence.

[Exact firmware/cluster compatibility](docs/testing/COMPATIBILITY_MATRIX.md) · [Three-profile testing and evidence](docs/testing/MULTI_PROFILE_TESTING.md) · [Firmware profiles](modules/profiles/)

## Packages and installation

The public source now contains the **MIB Runtime** (`/mnt/app/root/mibr/`), transactional installer, firmware-specific adapters and a three-profile ZIP assembler. A successful source build or host test is **not** a completed, downloadable, vehicle-tested installer.

- **Historical MU1440 developer package:** frozen seven-payload reference with its own exact hashes and recovery instructions. It does **not** include every recent menu, navigation or profile feature.
- **New shared three-profile package:** one common runtime plus Škoda MU1440 and SEAT MU1409/MU1447 profiles. Assembly/validation tooling exists; a complete, qualified combined beta artifact must be checked separately.
- **Installation:** read the correct package's instructions and run an exact-target, read-only preflight before any target write. Do not use legacy MU1440 instructions for the new multi-profile installer.

[Packages and release status](docs/packages/README.md) · [Beta pipeline and pinned-JAR policy](docs/build/MULTIPROFILE_RELEASE.md) · [Developer installation / legacy scope](docs/INSTALLATION.md) · [Package contract](docs/build/PACKAGE_LAYOUT.md) · [Current frozen release](release/CURRENT.md)

## Architecture and development

**MIBR = MIB Runtime.** Shared CarPlay/video, broker, menu, navigation and settings definitions have one canonical owner each; firmware-specific HMI, display, input, icons and integrations belong to exact profiles. The broker controls native state and actions; the receiver/video chain carries the secondary CarPlay stream. Firmware identification and build-input hashes are distinct.

```text
iPhone CarPlay ── auxiliary stream 111 ── receiver / TS / MOST ── Virtual Cockpit
                        ↑
          OEM menu / input ── MIBR broker ── settings / navigation
                        ↑
          exact Škoda / SEAT firmware profile
```

The public tree contains current shared source, toolchain and build tooling, but some exact J9, OEM and firmware inputs must be supplied externally and cannot be redistributed. Current code is not necessarily identical to the binaries of an older vehicle test.

[Documentation hub](docs/README.md) · [Architecture and ownership](docs/architecture/README.md) · [Repository modules](modules/) · [QNX/J9 build guides](docs/build/) · [Configuration defaults](docs/configuration/DEFAULT_CONFIGURATION_MATRIX.md) · [Developer runtime switches](docs/architecture/ADVANCED_RUNTIME_SWITCHES.md) · [Roadmap](ROADMAP.md)

## Research, contributions and attribution

We welcome reproducible vehicle reports, firmware/cluster fingerprints, independently authored improvements and safely collected evidence. Distinguish *source exists*, *build passed*, *package validated*, *unit tested* and *vehicle effect observed* in reports. The [Cluster Atlas](docs/index.html) and [public research index](docs/research/README.md) preserve broader context; historical dated studies are not the current installation instructions.

[Contributing](CONTRIBUTING.md) · [Support](SUPPORT.md) · [Vehicle test protocol](docs/testing/VEHICLE_TEST_PROTOCOL.md) · [Acknowledgements](ACKNOWLEDGEMENTS.md) · [License and third-party notices](THIRD_PARTY_NOTICES.md)

**Independent, unofficial project.** Not affiliated with, authorized or supported by Volkswagen AG, Škoda, SEAT, CUPRA, Audi, Harman or Apple. Names identify target products and credited research only.
