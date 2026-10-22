# MHI2 AltScreen CarPlay

**Real CarPlay secondary navigation in the original Volkswagen Group MHI2 Virtual Cockpit — direct video, guarded native-navigation fallback and an OEM-style control architecture.**

The project has advanced beyond the first moving-map proof of concept. On the exact Škoda MU1440/AID10 reference unit, **Apple Maps, Google Maps and Waze** have appeared as moving auxiliary video. Subsequent development sessions exercised long-running protected direct/parity transport, navigation composition, SafeArea/ViewArea, an OEM-native menu, zoom and an experimental stock/CarPlay route controller. This is a working vehicle-reference engineering project, **not** a universal product or a claim that all the newer features are already in the downloadable public ZIP.

[Feature status](#features-and-status) · [Module architecture](docs/architecture/README.md) · [Published source coverage](docs/status/PUBLISHED_SOURCE_COVERAGE.md) · [Developer release](release/CURRENT.md) · [Compatibility](docs/testing/COMPATIBILITY_MATRIX.md) · [Measured steering-wheel/head-unit key map](docs/testing/MU1440_MFW_RAW_KEY_MAPPING.md) · [Acknowledgements](ACKNOWLEDGEMENTS.md) · [Documentation](docs/README.md)

## Features and status

✅ = demonstrated reference-vehicle or existing reference-release milestone; ◐ = advanced development/partial field evidence with integration or release gates; ◻ = still research/planned. The evidence refers to **different pinned test configurations**, not an assertion that one current public download includes every item.

| | Capability | Current evidence and limit |
| --- | --- | --- |
| ✅ | Real CarPlay map in the VC | Apple Maps, Google Maps, Waze via ScreenAlt/type 111; not screenshot mirroring |
| ✅ | H.264 to MPEG-TS/MOST150 | Direct compressed video path, one protected writer and reversible native STOCK handback observed |
| ✅ | Extended transport sessions | Multiple longer development sessions; one ~56-minute run processed 83,919 input AUs with no reported sequence or writer errors. Separate USB/source-111 disconnects are **not resolved** by this metric |
| ✅ | Native-map Most20 | Exact reference-unit 1010×376 OEM native-video rate measured at 20 fps, separate from CarPlay negotiated sender FPS |
| ◐ | ViewArea, SafeArea, navigation composition | Two-area and visible presentation observations; individual settings still require current-session APPLY/ACTIVE proof |
| ◐ | OEM-style HOME / VC settings | Built and reference-unit-tested menu candidates plus single-authority MIBR/3 design; value persistence is not itself a visibly applied CarPlay setting |
| ◐ | Map zoom via steering-wheel roller | Semantic zoom and source/input research; Apple Maps visual zoom observed in a development configuration, with focus and cross-provider validation outstanding |
| ◐ | Native ↔ CarPlay cluster selection | Guarded physical-input/KEY40 and action-control development; current route owner, physical visual result and ACK need complete qualification; not bundled as a general public toggle |
| ◻ | Vehicle data to CarPlay | Actual speed, ambient temperature, range and warning integration being developed; existing-session phone acceptance not yet proven |
| ◻ | Further platforms and optional features | SEAT/VW/CUPRA, native wireless, RGI/native maneuvers need independent hardware/software qualification |

**Remaining milestones:** distinguish phone/source TEARDOWN from loss of native writer gate proof; eliminate duplicate supervisor start; finish same-session reconnection/visible VC recovery; qualify HMI STORE → APPLY → ACTIVE; qualify Zoom/KEY40 while preserving OEM behavior; connect optional truthful vehicle data; publish one coherent current source/build/release package. [Current detailed status](docs/status/INTEGRATION_STATUS_2026-10-21.md) · [Known issues](docs/findings/KNOWN_ISSUES.md) · [Roadmap](ROADMAP.md).

## Vehicle demonstration

![Waze on the reference Virtual Cockpit](docs/media/mu1440-stream111-poc-2026-09-29/waze_vc_stream111_photo_public_minblur.jpg)

[Waze, Google Maps and Apple Maps photos/videos](docs/media/mu1440-stream111-poc-2026-09-29/README.md) · [Aggregated October vehicle findings](docs/findings/OCTOBER_2026_VEHICLE_AND_TIMING_EVIDENCE.md). Photographic evidence demonstrates a working physical output, not independently measured panel frame rate.

## Project goals

1. Implement reproducible, independently developed CarPlay auxiliary/instrument-cluster navigation on qualified MHI2 targets while preserving main CarPlay and original navigation.
2. Keep a single bounded H.264/MPEG-TS/MOST video owner, source-generation control, recovery and predictable STOCK handback.
3. Provide intuitive OEM-style HMI, navigation configuration and steering-wheel operation without compromising stock keys, Java/HMI or original runtime services.
4. Support calibrated ViewArea/SafeArea and optional real vehicle data through the existing authenticated CarPlay session, where demonstrated.
5. Publish **actual project source**, build recipes, tests, architecture and pinned artifacts after provenance and consistency review, not only screenshots or binary files.
6. Adapt the portable architecture to selected Škoda, SEAT, CUPRA and VW firmware/cluster families; never treat the MU1440 J9/widget/MOST layout as universally interchangeable.

## Target and compatibility

| Target | Classification |
| --- | --- |
| Škoda MHI2_ER_SKG13_P4526_MU1440 with fitted AID10-class 10.x-inch MQB Virtual Cockpit and MOST route | Original exact-component vehicle reference |
| Other Škoda/SEAT/CUPRA/VW MHI2 | Candidate ports requiring exact firmware, J9/HMI, DSI, cluster geometry and video-route review |
| MU1409 / Continental FPK 790 | External user demonstrated an adapted **third-party** solution in [Issue #47](https://github.com/harman-f/mhi2_altscreen_carplay/issues/47), not compatibility proof for our current binary |
| Older/larger 12.3-inch AID and Audi LVDS/MHI2Q | Different hardware/transport; not a drop-in implementation |

Before attempting changes on an unknown unit, use [read-only compatibility guidance](docs/testing/COMPATIBILITY_MATRIX.md) and maintain an independent rollback.

## System architecture

- **Media:** iPhone authenticated CarPlay → existing MHI2 receiver/GEN2 → auxiliary type-111 H.264 AUs → direct TS remux or source-time parity development → one guarded STOCK/DIRECT writer → /dev/mlb/isoTX2 → MOST150 → Virtual Cockpit.
- **Control:** OEM HOME/settings view → bounded J9 client → single native settings/action owner → qualified media/route owner with request-specific receipts and actual VC effect verification.
- **Optional vehicle telemetry:** original DSI vehicle inputs → bounded adapter → existing authenticated session. No competing CarPlay/iAP2 login, independent second video writer or invented sensor values.

Stock primary CarPlay type 110 stays separate from private auxiliary 111. An accepted write, current source stream, stored UI selection and actually displayed navigation are distinct test outcomes. [Module boundaries/SEAT–VW adaptation](docs/architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md) · [HMI/controller](docs/architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md) · [Vehicle-data concept](docs/architecture/OPTIONAL_VEHICLE_DATA_FEATURE_OVERVIEW.md).

## Published source and developer release

The public repository already includes project-owned **GEN2 receiver C**, **Direct-TS remux C**, **MOST writer and exclusive gate C**, runtime/deployment and diagnostic code; start at [src/native](src/native/), [runtime](runtime/) and [full coverage table](docs/status/PUBLISHED_SOURCE_COVERAGE.md).

**The latest integrated source for newer parity/supervisor, Java HMI, MIBR/3 controller and optional vehicle-data modules is not yet distributed here as a cohesive source or release.** Closing historical experimental PRs did not import them into main. Each new public source package needs dependency, license, build and appropriate vehicle-evidence review.

The existing [hash-pinned MU1440 developer prerelease](release/CURRENT.md) assumes existing SSH, exact-compatible components, backup and tested recovery. It does not contain a finished public menu/zoom/KEY40/vehicle-data installer and is not a universal one-click SD-card solution. [Installation guidance](docs/INSTALLATION.md) · [Build notes](docs/build/DIRECT_TS_REMUX_BUILD.md) · [Advanced runtime reference](docs/architecture/ADVANCED_RUNTIME_SWITCHES.md).

## Open-source acknowledgements

This implementation builds on independently published MIB2/MHI2 research and tools. Special thanks to [Luka](https://github.com/luka-dev), [OneB1t](https://github.com/OneB1t/VcMOSTRenderMqb), [jilleb/MIB Toolbox](https://github.com/jilleb/mib2-toolbox), [omonob](https://github.com/omonob/MHI2-Carplay-Maps) and other credited public project maintainers. See [full acknowledgements](ACKNOWLEDGEMENTS.md), [exact upstream/source and license notices](THIRD_PARTY_NOTICES.md), and [public reference projects](docs/research/PUBLIC_REFERENCES.md). Prior art, separately licensed incorporated material and independently authored project code are distinguished there; attribution is not a claim that the upstream maintainers endorse this project.

## Independence and trademarks

**Unofficial, independent community project.** This project is not affiliated with, authorized, sponsored, endorsed, supported or maintained by Volkswagen AG, Volkswagen, Škoda Auto, SEAT, CUPRA, Audi, Harman International or Apple. Product, company and trademark names are used solely to identify the original hardware/software, describe compatibility and credit third-party work; all respective marks remain with their owners. The project does not provide official OEM updates, support or warranties. Modifications are experimental; check the exact target, retain backups and an independent recovery path, and do not operate or test modified controls while driving. See [third-party and rights notices](THIRD_PARTY_NOTICES.md), [compatibility](docs/testing/COMPATIBILITY_MATRIX.md) and [safety guidance](SECURITY.md).

## Contributing and safety

External reproducible bugs, firmware/cluster compatibility reports and independently authored code contributions are welcome; questions can use Discussions. [Contributing](CONTRIBUTING.md) · [Support](SUPPORT.md) · [Security/privacy](SECURITY.md) · [Vehicle test protocol](docs/testing/VEHICLE_TEST_PROTOCOL.md).

**Experimental; use at your own risk.** Do not upload original OEM/iOS packages, personal navigation content or credentials, or try an unqualified cross-firmware installation.
