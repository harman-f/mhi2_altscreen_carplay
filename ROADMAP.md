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

The last three milestones are development results, **not** included as finished features in the existing pinned public ZIP. [Current feature and acceptance status](docs/status/FEATURE_STATUS.md) · [Published source coverage](docs/status/PUBLISHED_SOURCE_COVERAGE.md) · [Package stages](docs/packages/README.md).

## Next release milestones

| Goal | Gate before promotion |
| --- | --- |
| **Stable session and recovery behavior** | Separate source-111 session teardown from native writer-gate loss; remove duplicate supervisor; validate reconnect with new session/config/IDR and visible VC result |
| **Modular source integrated** | **Source milestone complete:** MIB Runtime common modules, settings registry, firmware adapters and installer/assembler tooling are on public `main`. Exact external J9 builds, final complete ZIP and vehicle evidence are independent remaining gates |
| **OEM navigation configuration** | UI/store, qualified application and actual owner/session/visible ACTIVE independently evidenced; keep OEM keys and main CarPlay stable |
| **Right-roller zoom and KEY40 STOCK/CARPLAY route selection** | Qualify current-focus input, semantic owner, real visual effect, request-specific ACK and safe handback on the exact fitted target |
| **Vehicle status integration** | Preserve stock GNSS, qualify real DSI units, existing iAP2 owner attachment, feature subscription/stop and iPhone acceptance of actual speed, ambient temperature, range and warnings |
| **Portability** | Exact firmware/J9, OEM widget IDs, DSI source and fitted display routing verified separately for each SEAT/VW/CUPRA/Škoda target |
| **Three-profile beta distribution** | Finish per-profile J9 outputs and one complete validated MU1440/MU1409/MU1447 ZIP; separately verify preflight, install, recovery and vehicle behavior before stronger support claims |

## Additional research directions

Native wireless CarPlay, RGI/native maneuver guidance, additional firmware/cluster families and decoder quality/performance are independent optional research goals. They do not block the current wired reference milestone. Existing alternate implementations are prior art and require separate compatibility and origin checks; they are not silently imported into this release.

[Architecture](docs/architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md) · [HMI and controls](docs/architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md) · [Stream fault isolation](docs/testing/STREAM111_FAULT_ISOLATION_2026-10-21.md) · [Compatibility matrix](docs/testing/COMPATIBILITY_MATRIX.md).
