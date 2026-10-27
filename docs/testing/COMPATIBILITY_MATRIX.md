# Compatibility and validation matrix

This table separates **project goal** from **actual evidence**.

For the detailed cross-brand cluster/transport matrix, including panel resolution vs. map viewport and MOST vs. LVDS architecture, see [MIB2-era cluster/display transport knowledge base](../research/MIB2_CLUSTER_DISPLAY_TRANSPORT_KNOWLEDGE_BASE.md).

## Platform matrix

| Platform | Firmware / baseline | Status | Evidence |
| --- | --- | --- | --- |
| Škoda MHI2 / MU1440 + AID10-class | `MHI2_ER_SKG13_P4526_MU1440` | primary proven target | vehicle-tested on one 10.x-inch MQB Virtual Cockpit |
| other Škoda MHI2 + AID10-class | unknown | plausible family target, not assumed compatible | needs exact hashes + cluster identity + vehicle test |
| SEAT Leon Cupra 2019 / MU1409 / Continental FPK 790 | `MHI2_ER_SEG11_P4708` (separate contributor also reports `P4708_1`) | **external third-party working-port report; NOT qualified for this project's binary** | Wired Apple Maps/Google Maps/Waze shown by an adapted third-party implementation; cropping/centering and zoom limitations reported; wireless-adapter map output not established. [Community Issue #47](https://github.com/harman-f/mhi2_altscreen_carplay/issues/47). Confirm exact component hashes and target cluster before any project port. |
| CUPRA Ateca / MU1409 / Continental FPK 790-family | `MHI2_ER_SEG11_P4708_1` | **target-adapted project output observed; not a generic supported binary** | Wired maps, menu arrival-time effect and Apple/Google roller zoom observed on one unit. Reduced-layout ETA/directions and scrollbar remain unresolved. [Observations and six photographs](SEAT_CUPRA_MU1409_VEHICLE_OBSERVATIONS.md). |
| SEAT/CUPRA MHI2 + Digital Cockpit | planned | Continental homologation data places several `5F0/5FJ...790` clusters in the same later-FPK lineage as Octavia/T-Roc/Tiguan-D; exact panel/viewport and vehicle behavior remain unvalidated | help wanted |
| Volkswagen MHI2 + AID10-class | planned | unvalidated | help wanted |
| Volkswagen 12.3-inch AID / other large AID revisions | separate target | **not assumed equivalent to AID10-class** | needs hardware/transport/layout audit + vehicle test |
| Audi B9 MHI2 / AUG22 MU1438 + Virtual Cockpit | `MHI2_ER_AUG22_K3346_MU1438`, app50 + stage2/50 audited | **offline comparison complete; not supported / not vehicle-tested by this project** | 13 native pairs / 26 Ghidra inputs, focused Java and firmware JXE hash checks. Lifecycle prologue gates match; session fields and HMI/transport ownership differ. Audi LVDS presentation, productive context/geometry and runtime ABI remain open. See the [verified pair report](../research/MU1438_MU1440_OFFLINE_COMPARISON_2026-09-28.md). |
| MHI2Q / Qualcomm | comparator only | not this runtime target | public prior art exists |

Reference MU1440 stock `libairplay.so` SHA-256:

```text
193a4fd9101ec2aa05e7159cfa307b96500810d379ca74a194f172adc13a46b5
```

A different hash is a **stop condition**, not permission to assume ABI compatibility. A matching/known MU firmware is also **not sufficient by itself**: cluster hardware/revision is a separate compatibility dimension.

## Static firmware-profile corpus

A separate six-baseline offline corpus now maps reusable firmware implementation profiles across
Audi/Škoda/VW/SEAT MHI2 trains.

Completed baselines:

| Firmware | Static corpus result | Vehicle-support status |
| --- | --- | --- |
| `MHI2_ER_AUG22_K3346_MU1438` | canonical Audi AUG22/MU1438 comparator | not vehicle-tested by this project |
| `MHI2_ER_AU37X_P5089_MU1326` | standalone AU37X profile mapped; P5153 source missing | not vehicle-tested by this project |
| `MHI2_ER_SKG11_K3343_MU1433` | profile-mapped; several native layers MU1438-nearest | not vehicle-tested |
| `MHI2_ER_VWG11_K3342_MU1427` | profile-mapped; complete AirPlay file equals Audi MU1438 | not vehicle-tested |
| `MHI2_ER_SEG11_P4709_MU1447` | profile-mapped; several layers MU1440-nearest | not vehicle-tested |
| `MHI2_ER_SKG13_P4526_MU1440` | profile-mapped and vehicle-proven reference | **supported reference target only** |
| `MHI2_ER_VWG13_K4525_MU1367` | profile-mapped; AirPlay/config/JXE strongly MU1440-related | not vehicle-tested |

The main static findings are documented in
[MHI2 cross-firmware implementation profile map](../research/MHI2_FIRMWARE_PROFILE_MAP_2026-09-28.md).

Patch-by-patch engineering estimates are tracked separately in the
[Patch-portability estimate](../research/MHI2_PATCH_PORTABILITY_ESTIMATE_2026-09-28.md), including
GEN2/Stream-111, Direct-TS, the `isoTX2` gate, NavIgnore, Most20FPS and the Java Direct-VC policy.

AU37X P5089/MU1326 has now been processed as a standalone seventh corpus profile. P5153/MU1326
remains `SOURCE_MISSING`, so no same-family equivalence claim exists. P5089 uses a distinct
AirPlay/native profile and Audi `fwhmi` Java ownership; its static boot/config evidence still shows
the familiar `devp-iso-mmx-mib2 -S188 -P64 -Q18 ... -MisoTX2` low-level MOST contract. Productive
cluster-map routing remains a vehicle/runtime question.

Static corpus similarity never bypasses the separate cluster hardware/routing/vehicle-validation
gates below.

## Exact MU1438 versus MU1440 component matrix

Scope is this **one exact pair**, not all Audi, all MU1438 or app70. These are
static comparisons, not additional supported targets. Complete sizes/hashes,
section payload deltas and dynamic-name/dependency differences are in the
[component CSV](MU1438_MU1440_COMPONENT_MATRIX.csv); exact hook-function extents
and hashes are in the [hook CSV](MU1438_MU1440_HOOK_MATRIX.csv). The
[function-difference summary](MU1438_MU1440_FUNCTION_DIFF_SUMMARY.csv) quantifies
the available common bounded ELF function names, not overall ABI compatibility.
Missing/zero-sized symbols and aliases limit that denominator; changed operands
or mnemonic shapes may reflect compiler/layout changes rather than changed logic.

| Component / seam | Verified difference | Porting implication |
| --- | --- | --- |
| `libairplay.so` | lifecycle/control bodies differ; same inline-entry prologues; security fields shifted +8 | separate hash-gated profile, preserve stock delegation; full ABI unproven |
| `dio_manager` | code/interface delta; TearDown dynamic import only on MU1440 | target-specific callback/process review |
| `smartphone_integrator` | code/interface delta; `libusbdi.so.2` only on MU1438 | preserve Audi USB/launch behavior |
| `libdsicarplayproxy.so`, `videoovermost`, `libirc_mmx_adapter.so` | same dynamic name sets, different code | name equality is not callback ABI equality |
| `displaymanager` | different RX load payload; lives in stage2, not app.img | audit native ownership with Audi HMI/config |
| `libiap2client.so.1`, `libnvss_video.so`, `mm-ipod` | identical `.text` and RX payload; QNX/debug metadata differs | no code delta identified for this pair |
| `dmdt`, `libdmdt_core.so` | identical `.text`; version/build strings differ | Audi debug-client silence needs service/config diagnosis, not assumed command-code port |
| `devp-iso-mmx-mib2` | only two ELF program-header physical-address bytes differ | no code/data delta identified; not a proof of Audi map-over-MOST |
| PLT / LD_PRELOAD | lifecycle PLT/JUMP_SLOT present on **both** builds | QNX runtime resolution/coverage still requires proof |
| AES argument observer | same successful decrypt-init path and caller return +0x38 | statically promising; does not use shifted session offsets; runtime unproven |
| NvSS output wrapper | layer 59 shared; handle offset +0x50 vs +4; Audi lacks Skoda NULL guard | explicit output environment; no wrapper-structure reuse |
| Java/KPL display owner | Audi conditional LVDS/HMI contexts vs MQB MOST stream-sink adapters | distinct LVDS presentation/arbitration/restore work, not a MOST writer copy |

### Target-admission gates

| Gate | MU1440 reference | Audited Audi MU1438 |
| --- | --- | --- |
| exact update/native hashes | known | recorded for this app50/stage2-50 pair |
| Java source equals update JXE | known baseline | backup JXE hash verified against stage2/50 |
| five entry prologue patterns | vehicle-used | static match only |
| session/object/CF and descriptor contract | reference implementation tested | partial static comparison; unresolved assumptions |
| QNX loader/interposition coverage | inline strategy vehicle-derived | untested; PLT presence is not admission |
| cluster transport and live ownership | MOST Direct-TS vehicle-proven | LVDS candidate topology; productive mapping/geometry untested here |
| STOCK → project → STOCK recovery | vehicle-proven | no target-specific build/trial yet |

The MU1440 admission/hash gate and runtime binaries are unchanged. Do not load a
MU1440 build on Audi on the strength of this table.

## Cluster-family capability summary

This is the short operational view. See the [full cluster/display transport knowledge base](../research/MIB2_CLUSTER_DISPLAY_TRANSPORT_KNOWLEDGE_BASE.md) for evidence, sources and caveats.

| Family | Example part numbers | Native panel raster | Stock / known map-video surface | Direct-TS test guidance | Transport |
| --- | --- | ---: | ---: | --- | --- |
| MQB AID1 / older Continental FPK | `5G1920791x`, `3G0920791x`, `5NA920791x` | **1440x540** | OneB1t older-family baseline: **800x480** | do not assume full-panel H.264 acceptance; capture exact stock/DMDT geometry first | MOST + H.264 |
| Later Continental FPK Entry / `...790(A)` | `17A920790`, `5NA920790D`, `5E0920790A`, related `3V0/565/5F0...790` | **1280x480-class** | **1010x376** on OneB1t-tested 17A/5NA-D/5E0; exact Octavia stock DMDT also reports 1010x376 | **1010x376 canonical map/video surface**; 1280x480 remains optional decoder research, not a support gate | MOST + H.264 |
| Škoda Octavia III reference | `5E0920790A`, HW 508 / SW 1691, `EV_DashBoardVDDMQBA0 001026` | **1280x480-class** | **1010x376 OEM/QNX `DISPLAYABLE_KOMBI_MAP_VIEW`** | **1010x376 fixed reference canvas**; proceed with SafeArea/ViewArea calibration | MOST150 / DCIVIDEO / `/dev/mlb/isoTX2` |
| SEAT Leon later-FPK example | `5F0920790A`, HW 609 / SW 1701, `EV_DashBoardVDDMQBA0 001026` | **1280x480-class** | exact stock map-plane not yet captured here | likely same family, but require target-specific DMDT/vehicle proof | MOST/H.264 candidate |
| Škoda Kodiaq/Karoq later-FPK example | `565920790A`, SW 1691, `EV_DashBoardVDDMQBA0 001026` | **1280x480 / 10.25-inch-class** | exact stock map-plane not yet captured here | likely same family, but require target-specific DMDT/vehicle proof | MOST/H.264 candidate |
| Audi B9 MIB2 Virtual Cockpit Gen1 | `8W5...790` VC family | early Audi VC: **1440x540** | dedicated LVDS map surface; exact MU1438 geometry still to capture | separate LVDS target, not a MOST Direct-TS geometry assumption | **LVDS J794 -> J285** for large map/intersection map |
| Audi MIB2 Top non-VC cluster | target-specific | analog + center display | target-specific | comparator only | **MOST carries navigation including map** |

## Functional validation matrix

| Function | Status | Notes |
| --- | --- | --- |
| Annex-B H.264 -> MPEG-TS | PASS | public `direct-ts-remux` |
| strict 64 × 188 / 12032-byte write contract | PASS | vehicle-tested |
| direct write to `/dev/mlb/isoTX2` | PASS | vehicle-tested |
| custom video visible in real VC | PASS | vehicle-tested |
| stock DisplayManager remains alive | PASS | vehicle-tested |
| suppress native producer with writev gate | PASS | vehicle-tested |
| restore STOCK producer | PASS | vehicle-tested |
| Type-111 H.264 receive | PASS | experimental GEN2 snapshot |
| live Apple Maps in VC | PASS | vehicle-tested |
| automatic Direct start/stop | PASS in current development line | newer than public GEN2 binary |
| cable-reconnect recovery | PASS | useful fallback on older GEN2 snapshot |
| manual same-session keyframe recovery | PASS | reproduced twice; fresh source IDR restored moving VC video |
| automatic D2 keyframe recovery | PASS / NEEDS TUNING | kept tested lifecycle/provider transitions usable; current watchdog is intentionally aggressive |
| provider switch without reconnect | PASS in tested 2026-09-27 sequence | Apple Maps / Google Maps / Waze transitions exercised; broader soak testing still needed |
| Google Maps end-to-end | PASS in tested sequence | not yet a broad compatibility claim |
| Waze end-to-end | PASS in tested sequence | rich lower trip-summary UI exposed a SafeArea issue |
| `suggestUI` lifecycle interpretation | STRONG RESEARCH EVIDENCE | exact iOS 27.2 + vehicle tracing |
| navigation composition query controls | PASS / VEHICLE-OBSERVED | ETA/compass/maneuver layout alter real provider composition |
| Direct 1280x480 geometry probe | OPTIONAL RESEARCH / NOT A SUPPORT GATE | physical-panel-class probe remains possible, but 1010x376 is the canonical reference coded-frame/map surface |
| SafeArea configuration | BUILD-CONFIRMED / CURRENT VEHICLE WORK | calibrate on the fixed 1010x376 reference canvas; no longer blocked by a 1280x480 probe |
| dynamic ViewArea | RESEARCH / NOT RELEASED | in-session update mechanism identified; runtime preset switching planned |
| navigation arrows / RGI | FUTURE/SEPARATE | not required for map-video proof |
| SD-card installer | INTENTIONALLY NOT PROVIDED | SSH/developer phase |
| cross-brand portability | PARTIAL STATIC EVIDENCE / RUNTIME OPEN | exact Audi AUG22 MU1438 pair audited; public component/hook matrices available; no Audi support or vehicle admission |

## What to include when adding a new target

A useful compatibility report needs:

- brand/model family;
- firmware train + MU;
- stock `libairplay.so` SHA-256;
- DisplayManager binary/config identity if known;
- cluster/AID type, part number and HW/SW identification if available;
- SSH transport used;
- result of stock map -> DIRECT -> STOCK sequence;
- project artifact hashes;
- logs with personal/navigation data removed.

Do not post VINs.


## Cluster-family note

`AID10-class` is a **project shorthand**, not a claim that Volkswagen Group uses one universal official
type name. Public OEM material shows materially different digital-cluster generations/sizes, including
a 12.3-inch 1440x540 Active Info Display and smaller/newer 1280x480 families marketed around
10.25/10.3/11.7 inches depending on brand/model/generation.

For this project, do not infer compatibility from display size alone. Future target admission should gate on:

1. MHI2 firmware/component identity;
2. cluster part number / hardware+software identity;
3. observed display transport contract (MOST/DCIVIDEO, LVDS, IP or other);
4. view geometry / SafeArea behavior;
5. real STOCK -> DIRECT -> STOCK vehicle validation.

TODO: add a read-only `cluster_probe`/preflight report that identifies the cluster family from available
diagnostic/component data. This is intentionally deferred until after the current MU1440/AID10 lifecycle work.


### Public OEM cluster references

These links are background references only; they do **not** establish project compatibility:

- Volkswagen first-generation 12.3-inch AID (1440x540) and newer 11.7-inch AID (1280x480):
  https://www.volkswagen-newsroom.com/en/active-info-display-3950
- Škoda 10.25-inch Virtual Cockpit examples:
  https://www.skoda-storyboard.com/en/press-kits/skoda-scala-press-kit/always-online-thanks-to-the-new-skoda-connect-generation-including-new-infotainment-apps/
- SEAT 10.25-inch Digital Cockpit:
  https://mundoseat.seat.com/mediacenter_netstor/seat-media-center/Img/2018/07/2018-07-31/SEAT-introduces-its-Digital-Cockpit-to-the-Arona-and-Ibiza.pdf
- CUPRA Ateca 10.25-inch Digital Cockpit:
  https://www.cupraofficial.com/content/dam/public/cupra-website/generic/pdf/cupra-ateca-brochure-my25-w38.pdf

The dimensions/marketing names alone must never be used as an installer compatibility gate.
