# Roadmap and help wanted

> [!NOTE]
> The roadmap keeps the vehicle-proven/public baseline as its anchor. The newest **design-only** work — source-timestamp parity transport, frame/time keyframe policies, ownership A/B, HMI WidgetFactory integration and steering-wheel input — is collected in the [current research preview](docs/research/CURRENT_RESEARCH_PREVIEW_2026-10-05.md). Treat that page as research, not as a released implementation.

This is a research roadmap, not a promise of release dates.

> **Current cross-track update (2026-10-21):** The historical strict SafeArea → Java J1/J2 → D2 ordering below describes an earlier phase. Current independent workstreams now include guarded GEN2/parity recovery, OEM HOME/settings UI, a separate MIBR/3 single-authority control API, qualified STOCK/DIRECT owner actions, and optional classic vehicle-data integration. Each has its own source/build/vehicle acceptance; no new binary is promoted by this roadmap. See [current integration status](docs/status/INTEGRATION_STATUS_2026-10-21.md), [module/portability diagram](docs/architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md), [native HMI/controller design](docs/architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md), [recovery tests](docs/testing/STREAM111_FAULT_ISOLATION_2026-10-21.md), [optional vehicle-data overview](docs/architecture/OPTIONAL_VEHICLE_DATA_FEATURE_OVERVIEW.md) and [October findings](docs/findings/OCTOBER_2026_VEHICLE_AND_TIMING_EVIDENCE.md).

The project deliberately separates the **CarPlay AltScreen / Stream-111 video plane** from complementary native cluster interfaces such as **RGI / NavSD / BAP maneuver guidance**.

## At a glance

| | Status | Work item | Current / next gate |
|---|---|---|---|
| ✅ | Proven | Stream 111 -> H.264 -> MPEG-TS -> MOST -> Virtual Cockpit | Vehicle-proven on the MU1440 / AID10-class reference target |
| ✅ | Proven | Same-session keyframe recovery | Manual recovery and the current D2 safety policy are vehicle-proven |
| ✅ | Proven | Most20 native 20 fps | Stock isoTX2 capture proves real 1010x376 H.264 output changes from 10 fps to 20 fps; now reference-default on MU1440 |
| ✅ | Proven | Reversible developer deployment / STOCK fallback | Guarded install, status and restore path exists for the exact reference target |
| ✅ | Resolved baseline | Direct-TS outer geometry | Keep **1010x376** as the canonical coded-frame/map-surface baseline; 1280x480 is the physical panel class, not a proven Direct-TS contract |
| 🟨 | **Current** | SafeArea calibration | Calibrate ViewArea/SafeArea on the fixed 1010x376 reference canvas |
| ⏭️ | Next | Exact-stock Java isolation | J1/J2 single-class tests only after SafeArea is complete |
| ⏭️ | Next | D2 keyframe-policy tuning | Replace the conservative 1 s watchdog with event-scoped / bounded recovery |
| ⬜ | Planned | Steering-wheel VIEW / hardkey mapping | Prove the physical key from stock raw traces before assigning runtime behavior |
| ⬜ | Planned | Multi-ViewArea / automatic VC-layout coupling | Pre-advertise calibrated layouts, switch in-session, later bind to proven cluster state |
| ⬜ | Planned | Native navigation arrows / RGI | Feed CarPlay maneuver metadata into the stock cluster navigation UI (arrow, distance, text) |
| ⬜ | Research | Now Playing / native media metadata | Investigate native cluster media surfaces separately from Stream 111 |
| 🧪 | Research | AID / firmware compatibility matrix | Six-baseline firmware profile corpus closed; AU37X P5089/P5153 same-MU comparison is the next corpus gate |
| 🔬 | Research | Continental FPK firmware RE | Analyze legitimate FRF/ODX updates for the `...790(A)` / `EV_DashBoardVDDMQBA0` family; keep this separate from the preferred HU-side VIEW/layout-control path |
| 🧭 | Lead | Audi B9 / AUG22 MU1438 compatibility | OEM topology says B9 Virtual Cockpit map video is LVDS J794 -> J285; identify the exact MU1438 LVDS display/context/geometry and prove ABI before any runtime port |

The strict current vehicle order is:

```text
SafeArea on fixed 1010x376 baseline -> exact-stock Java J1/J2 -> D2 tuning
```

The earlier 1010x376-vs-1280x480 question is resolved **for current project scope**: 1010x376 is the
OEM/QNX map surface, the OneB1t later-FPK rendering window and the already vehicle-proven Stream-111
canvas. The 1280x480 value describes the later-FPK physical panel class. Direct decoder acceptance of
1280x480 has not been disproved, but it is no longer a prerequisite or blocker.

## P0 — SafeArea / ViewArea calibration on the fixed reference canvas

Use **1010x376** as the outer CarPlay secondary-display canvas and:

- keep the selected outer CarPlay secondary-display canvas fixed;
- calibrate the nested SafeArea against the real AID10-class gauge overlays;
- start from the current first estimate and adjust only geometry;
- keep the already-proven transport and current D2 behavior unchanged during calibration;
- after calibration, pre-advertise **exactly two** initial ViewArea/SafeArea pairs:
  `0 = MAP_FULL` and `1 = GAUGE_REDUCED`;
- advertise symmetric adjacency `0 -> [1]`, `1 -> [0]`, with `initialViewArea=0`;
- switch between those regions in-session through `updateViewArea` rather than recreating Stream 111.

This is the highest-priority vehicle work.

## P1 — exact-stock Java isolation

The earlier passive VC-state listener experiment disturbed the native VC / `isoTX2` path when introduced through Java bootclasspath shadowing.

The next Java work is therefore intentionally narrower:

1. exact-stock baseline;
2. one exact stock class at a time;
3. return to baseline between tests;
4. no new policy or layout behavior during isolation.

The purpose is to identify the minimum Java/HMI seam that can be observed safely before any automatic VC-layout binding is attempted.

## P1 — keyframe recovery policy

Same-stream `forceKeyFrame` recovery is already vehicle-proven. The current periodic D2 watchdog is deliberately conservative and is now enabled persistently by default on the MU1440 reference deployment.

Later tuning should:

- react to relevant lifecycle / composition events;
- debounce and coalesce bursts;
- request recovery only until a fresh IDR is confirmed;
- retain a bounded emergency fallback;
- preserve Apple Maps / Google Maps / Waze provider transitions without synthetic Stream-111 teardown.

## P1 — steering-wheel / hardkey runtime control

The exact MU1440 Java stack exposes the required ASL hardkey substrate, and stock logging already provides raw tuples for physical-key identification.

The rule is evidence-first:

- capture the physical button through stock raw logging;
- do not infer the VIEW button from symbolic names such as JOKER1/JOKER2;
- preserve the OEM VIEW semantics: short press changes the VC display version; long press opens the
  stock pre-selection menu (Auto / Classic / View 1 / View 2 / View 3);
- therefore do **not** use long VIEW as a project-only toggle;
- after the raw tuple and/or resulting VC state is proven, mirror the OEM layout change into the
  two predeclared CarPlay ViewArea/SafeArea presets.

A Green Engineering Menu selector and file/config control remain useful diagnostic fallbacks.

## P1 — navigation composition / provider validation

The project already exposes navigation-composition controls including ETA, compass, speed limit and maneuver-layout options.

Remaining work:

- road-test the combinations with Apple Maps, Google Maps and Waze;
- separate provider behavior from receiver behavior;
- verify which composition options are actually honored by each sender state;
- validate them again after SafeArea calibration.

## P2 — native navigation arrows / RGI / NavSD-BAP integration

This is intentionally a **separate output plane from the AltScreen video**.

Target concept:

```text
CarPlay navigation
 -> iAP2 / RGI maneuver metadata
 -> MHI2
 -> stock NavSD / BAP navigation surfaces
 -> native cluster maneuver UI
```

Desired first result:

- native maneuver arrow/type;
- distance countdown;
- road / street / destination text where supported;
- later lane guidance where the exact target supports it;
- clean takeover and automatic hand-back to OEM navigation.

Public Luka-derived RGI work (for example `luka-dev/mib2q-carplay-rgi`) and the AU37x/HARMAN implementations are important prior art, but the MU1440 path must use the exact Škoda HMI/NavSD/BAP contracts rather than copying a foreign JAR or renderer blindly.

The first implementation should prefer the **stock cluster's own navigation renderer**. Custom MOST/video rendering is not required for the native-arrow milestone.

## P2 — Now Playing / native media metadata

Investigate whether the existing native media/Now Playing cluster path can expose CarPlay metadata and artwork independently of the navigation video plane.

Keep this work separate from Stream 111 unless runtime evidence proves a shared dependency.

## P2 — compatibility / AID-family detection

Cross-brand findings are maintained in the [MIB2-era cluster/display transport knowledge base](docs/research/MIB2_CLUSTER_DISPLAY_TRANSPORT_KNOWLEDGE_BASE.md). Firmware/update/control findings are tracked separately in [FPK / Virtual Cockpit firmware and control access](docs/research/FPK_FIRMWARE_AND_CONTROL_ACCESS.md). Keep that document as the long-lived source for panel geometry, map viewport, transport and part-number evidence.

Cross-firmware corpus status:

- completed and verified: AUG22 K3346 MU1438, SKG13 P4526 MU1440, SKG11 K3343 MU1433,
  VWG11 K3342 MU1427, SEG11 P4709 MU1447 and VWG13 K4525 MU1367;
- current next comparison: AU37X P5089/P5153 MU1326;
- profile mapping is maintained in
  [MHI2 cross-firmware implementation profile map](docs/research/MHI2_FIRMWARE_PROFILE_MAP_2026-09-28.md).

The first vehicle-proven target remains:

- Škoda MHI2 / MU1440;
- AID10-class 10.x-inch MQB Virtual Cockpit.

Before broader support, collect and correlate:

- cluster part number / HW / SW identity;
- reliable read-only identification of AID family;
- native resolution and MOST/DCIVIDEO routing;
- SafeArea / ViewArea behavior;
- firmware/component hashes.

The larger/older 12.3-inch AID family is a separate compatibility target and must not be assumed equivalent.

An Audi B9 / AUG22 MU1438 contributor lead is now tracked separately. Audi OEM training material establishes that the **B9 Virtual Cockpit receives the large navigation map and detailed intersection map over LVDS from J794 to J285**, while MOST remains in use for other cluster content. The supplied MU1438 configuration is consistent with that split. The remaining target gate is therefore the **exact LVDS display/context/geometry plus binary ABI**, not a MOST-vs-LVDS guess.

## P2 — developer deployment / tester expansion

Continue improving:

- compatibility manifest and preflight;
- exact backup/restore manifest;
- reversible enable/disable;
- crash-safe STOCK fallback;
- bounded log collection;
- target-specific profiles;
- cross-brand vehicle traces.

The current repository remains a developer/research project, not a one-click SD-card consumer package.

## Good first contributions

Useful contributions include:

- one clean provider-transition trace;
- one new firmware hash + ABI check;
- one VC layout mapping;
- one physical hardkey tuple from stock logs;
- one QNX / IBM-J9 finding;
- one RGI / NavSD / BAP compatibility finding;
- one documentation correction backed by evidence;
- build portability improvements.

See `CONTRIBUTING.md` and use Discussions for exploratory findings before opening a hard bug.
