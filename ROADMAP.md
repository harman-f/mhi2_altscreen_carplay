# Roadmap

**Goal:** deliver a reproducible CarPlay secondary-screen implementation for qualified VW Group MHI2 head units and their fitted instrument clusters, preserving original navigation, input and a reversible STOCK fallback. The milestones below describe **features and release gates**, not a promise of dates or a public development-task log.

## Delivered reference-platform milestones

- [x] Moving Apple Maps, Google Maps and Waze auxiliary video on the exact MU1440/AID10 reference cluster
- [x] Project-authored GEN2/type-111 receiver and direct H.264→MPEG-TS/MOST source available for the published reference version
- [x] One protected media writer with observed STOP/STOCK restoration
- [x] Native original-map Most20FPS reference capability
- [x] Extended vehicle transport tests with preserved frame/TS accounting
- [x] Two-area ViewArea/SafeArea and navigation presentation development observations
- [x] Project-owned OEM-style HOME/Settings and bounded controller prototypes; still awaiting full per-setting APPLY/ACTIVE acceptance
- [x] Demonstrated Apple Maps zoom in an independently tested development combination; input/visible focus integration remains gated

The last three milestones are development results, **not** included as finished features in the existing pinned public ZIP. [Current evidence](docs/status/INTEGRATION_STATUS_2026-10-21.md) · [Released and experimental source coverage](docs/status/PUBLISHED_SOURCE_COVERAGE.md).

## Next release milestones

| Goal | Gate before promotion |
| --- | --- |
| **Stable session and recovery behavior** | Separate source-111 session teardown from native writer-gate loss; remove duplicate supervisor; validate reconnect with new session/config/IDR and visible VC result |
| **Coherent source release** | Publish a reviewed source/build/test tree for newer parity/supervisor, MIBR/3 controller, project-owned Java HMI and physical input modules with provenance and real dependency manifest |
| **OEM navigation configuration** | UI/store, qualified application and actual owner/session/visible ACTIVE independently evidenced; keep OEM keys and main CarPlay stable |
| **Right-roller zoom and KEY40 STOCK/CARPLAY route selection** | Qualify current-focus input, semantic owner, real visual effect, request-specific ACK and safe handback on the exact fitted target |
| **Vehicle status integration** | Preserve stock GNSS, qualify real DSI units, existing iAP2 owner attachment, feature subscription/stop and iPhone acceptance of actual speed, ambient temperature, range and warnings |
| **Portability** | Exact firmware/J9, OEM widget IDs, DSI source and fitted display routing verified separately for each SEAT/VW/CUPRA/Škoda target |
| **Distribution** | Build reproducibility, independent test evidence, exact installer preflight and rollback, manifest and separate vehicle acceptance |

## Planned v1.4 optional features (acceptance-gated)

| Candidate | Gate before enabling in a vehicle build |
| --- | --- |
| **Parked-only GPS demo location for private CarPlay screenshots** ([design](docs/architecture/CARPLAY_GPS_PRIVACY_DEMO_V1_4.md), [#76](https://github.com/harman-f/mhi2_altscreen_carplay/issues/76)) | Prove exact iAP2 NMEA sender and complete position-bearing sentence coverage; qualify independent parking/brake and fresh speed proof; pass deterministic host transformation, live parked iPhone/map adoption and unmodified stock recovery tests. Explicit opt-in, short TTL, OFF by default. If the phone does not honor accessory GNSS, retain disabled/shadow mode and use privacy-safe static/demo imagery instead. |
| **Version/target identity, HMI Version page and reproducible distribution** | Integrate reviewable source and target provenance/host tests first; any release claim requires exact binaries, authorized OEM inputs and separate installer qualification. |

These are **v1.4 feature targets, not evidence of a qualified implementation or a promise that all optional toggles will be released**. The historic 1.3.2 kit and normal vehicle navigation are not modified.

## Additional research directions

Native wireless CarPlay, RGI/native maneuver guidance, additional firmware/cluster families and decoder quality/performance are independent optional research goals. They do not block the current wired reference milestone. Existing alternate implementations are prior art and require separate compatibility and origin checks; they are not silently imported into this release.

[Architecture](docs/architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md) · [HMI and controls](docs/architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md) · [Stream fault isolation](docs/testing/STREAM111_FAULT_ISOLATION_2026-10-21.md) · [Compatibility matrix](docs/testing/COMPATIBILITY_MATRIX.md).
