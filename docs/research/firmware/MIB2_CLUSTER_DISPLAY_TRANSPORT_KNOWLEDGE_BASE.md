# MIB2-era Virtual Cockpit / AID display transport knowledge base

> **Research status · 2026-11-05:** **FIRMWARE RESEARCH REFERENCE.** Static comparison is not a supported vehicle or installer claim. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


**Scope:** Volkswagen Group digital instrument clusters relevant to the MIB2 / MHI2 development period, roughly 2015-2021.  
**Last research pass:** 2026-09-28.

Related: [FPK / Virtual Cockpit firmware and control access](FPK_FIRMWARE_AND_CONTROL_ACCESS.md).

This document intentionally separates four things that are often mixed together:

1. the **physical panel resolution** of the instrument cluster;
2. the **navigation/video surface** supplied by the infotainment unit;
3. the **transport** used between infotainment and cluster;
4. the **software/API path** used to control ownership, layout and metadata.

A panel being 1440x540 or 1280x480 does **not** imply that the infotainment unit sends a full-panel framebuffer at that geometry.

## Evidence labels

| Label | Meaning |
| --- | --- |
| **OEM-confirmed** | Audi/VW/Škoda service or official technical material |
| **Vehicle-proven** | reproduced on a real vehicle in this project |
| **Community-proven** | demonstrated by an open implementation / repeatable retrofit evidence |
| **Config-confirmed** | present in an original target configuration, but not yet proven active on the exact vehicle |
| **Hypothesis** | useful working model that still needs target-specific evidence |

## Capability matrix

| Cluster family / examples | Approx. MIB2 era | Physical panel | Navigation/video input from 5F/J794 | Map codec / transport | External map/renderer geometry | Evidence / notes |
| --- | --- | --- | --- | --- | --- | --- |
| **Audi Virtual Cockpit Gen1 — A4 B9/8W, A5 F5 and related MIB2 vehicles** | ~2015-2019 pre-MIB3 | 12.3", early VC family commonly 1440x540 | **LVDS from J794 to J285 for the large navigation map and detailed intersection map** | LVDS for map; MOST for list menus/covers and J285 software update; Infotainment CAN for other content | full external map geometry not frozen here | **OEM-confirmed.** This is architecturally different from the MQB MOST-map path. |
| **Audi "Top" non-VC cluster with navigation** | same generation | analog instruments + center display | J794 -> J285 | **MOST carries navigation data including map**; CAN carries other content | target-specific | **OEM-confirmed.** Important counterexample: Audi MIB2 can use MOST for maps when the fitted cluster is not Virtual Cockpit. |
| **Audi "Medium" non-VC cluster** | same generation | analog / smaller center display | no external map interface | no LVDS and no MOST interface for map | n/a | **OEM-confirmed.** |
| **VW AID Gen1 / AD1 — Golf 7, Passat B8, Tiguan, Arteon family** | ~2016-2020 | **12.3", 1440x540** | infotainment navigation map into cluster | **MOST streaming + H.264** on MIB2 coding/retrofit path | **800x480** community renderer/window baseline for the older `...791` family | **OEM panel resolution + community-proven MOST/H.264.** Diagnostic family commonly `EV_DashBoardVDDMQBAB`; OneB1t supports e.g. 3G0920791, 5NA920791, 5G1920791/794/795/798, 3CG920791. |
| **Later Continental FPK Entry / `...790(A)` family — T-Roc, Octavia 5E, Superb 3V, Kodiaq/Karoq 565, Leon 5F, later Tiguan variants** | ~2017-2021 | **1280x480 panel class** is strongly supported across this family; marketed diagonal varies by brand/model | infotainment navigation map into cluster | MOST-map capable variants use the same MQB MOST path | **1010x376** on OneB1t-tested `17A920790`, `5NA920790D`, `5E0920790A`; exact Octavia stock DMDT map plane is also **1010x376** | **Shared Continental FPK Entry lineage.** Diagnostic fingerprint repeatedly `EV_DashBoardVDDMQBA0 001026`, with SW around 1691/1701 on several variants. |
| **Škoda Octavia III 5E Virtual Cockpit — 5E0920790 / 5E0920790A** | late Octavia III / MIB2.5 era | later-FPK **1280x480-class** panel; exact 5E LCD module identification remains open | infotainment navigation map into cluster | **MOST streaming + H.264**; retrofit requires MOST optical link to 5F | **1010x376 OEM/QNX map plane** on the reference vehicle (`DISPLAYABLE_KOMBI_MAP_VIEW`) | **Vehicle-proven transport and map-plane geometry.** `5E0920790A` HW 508 / SW 1691 / `EV_DashBoardVDDMQBA0 001026` is independently documented. |
| **Škoda Superb III / Kodiaq / Karoq MIB2-era VC** | ~2018-2021 | later-FPK **1280x480 / 10.25-inch-class** panel family | infotainment navigation map into cluster | retrofit/coding evidence shows **MOST_streaming + H.264** | likely later-FPK map-plane family; exact per-PN geometry still needs direct DMDT/stock capture | `565920790A` is documented as SW 1691 / `EV_DashBoardVDDMQBA0 001026`; Continental homologation groups it with Octavia/T-Roc/Leon/Superb. |
| **SEAT/CUPRA MIB2-era Digital Cockpit — Leon 5F and related** | similar MQB period | **10.25-inch / 1280x480-class** | MQB later-FPK display family | MOST/H.264 on compatible MIB2 High targets | later-FPK geometry; exact stock map-plane per PN not yet frozen | `5F0920790A` is documented as HW 609 / SW 1701 / `EV_DashBoardVDDMQBA0 001026`; Continental homologation places it in the same later-FPK bundle. |
| **MIB3 / newer Ethernet/IP cluster generations** | 2019+ depending model | multiple later panels, including Full HD generations | architecture may use IP streaming / MOST_High / other later paths | not the MIB2 baseline | target-specific | **Out of scope for this matrix unless explicitly used as a comparator.** Do not mix Golf 8 / later Audi VC-plus evidence into MHI2 decisions. |

## The two major MIB2 architectures

### A. MQB VW / Škoda: map video over MOST150

For the MQB MIB2 High family relevant to this project, several independent evidence streams converge:

```text
MIB2 High / 5F
    |
    | navigation map
    | H.264
    v
DisplayManager / DCIVIDEO
    |
    | /dev/mlb/isoTX2
    v
MOST150 optical bus
    |
    v
AID / Virtual Cockpit map surface
```

Vehicle retrofit coding repeatedly uses:

```text
Dashboard_Graphic_Variant = MOST
navigation_map_transmission_mode = MOST_streaming
navigation_map_compression_mode = H264
```

The OneB1t `VcMOSTRenderMqb` implementation independently demonstrates arbitrary/custom video reaching multiple MQB Continental/VDO clusters through the MOST map path and explicitly identifies the **DCIVIDEO Kombi Map** channel as `isoTX2`.

This matches the MU1440 path already proven by this project.

### B. Audi B9 MIB2 Virtual Cockpit: map video over LVDS

Audi service-training material explicitly distinguishes the Virtual Cockpit from the non-VC cluster:

```text
Audi B9 MIB2 / J794
    |
    | large navigation map
    | detailed intersection map
    v
LVDS
    |
    v
J285 Audi Virtual Cockpit
```

For the Audi Virtual Cockpit:

- **LVDS** carries the large navigation map and detailed intersection maps.
- **MOST** carries other content such as list menus/covers and is used for J285 software updates.
- **Infotainment CAN** carries other non-image/content communication.

For Audi's non-VC **Top** cluster, however, the same OEM material says navigation including the map is carried over **MOST** and that cluster has no LVDS interface.

This explains why an Audi stock DisplayManager configuration may contain both MOST-video and LVDS/HDMI-related capabilities without both being the active map path for the same fitted cluster.

## Audi B9 / AUG22 MU1438 implication

Contributor-supplied stock configs for the current Audi B9 lead contain:

- a MOST encoder targeting `/dev/mlb/isoTX2`;
- a `video_over_most` routing block;
- an extended `2_lvds` display mode with `Tegra:HDMI0` / display ID 4;
- HBAS profiles that select `kombi_type = lvds`.

The OEM Audi topology now gives this configuration a much stronger interpretation:

> For an actual B9 **Virtual Cockpit**, the primary large navigation-map image path should be treated as **LVDS until vehicle evidence proves otherwise**. The mere presence of `isoTX2` in the same configuration is not evidence that the VC map itself uses MOST.

The next target-specific probes should therefore identify:

1. exact J285 / Virtual Cockpit part number and HW/SW;
2. whether the vehicle is pre-facelift MIB2 rather than later MIB3;
3. the active DisplayManager display/context corresponding to the LVDS secondary output;
4. the exact geometry expected by that output;
5. how CarPlay AltScreen video can be bound to that existing display path without disturbing stock ownership.

## Panel resolution vs. map viewport

### Exact MU1438/MU1440 offline refinement (2026-09-28)

The [verified firmware-pair comparison](MU1438_MU1440_OFFLINE_COMPARISON_2026-09-28.md)
now includes both stage2 DisplayManagers, the MOST driver, NvSS/DMDT companions,
and firmware-hash-verified Java display owners. The MOST driver has identical
non-header bytes in the pair, and the low-level NvSS library has identical code.
Those facts do not collapse the two productive presentation architectures.

Audi's static Java controller selects terminal0/LVDS for KombiType4;
otherwise terminal1/LVDS for SysConst541==2; otherwise terminal1/H264-MOST on
the remaining activated path. Its 72–78 context table is condition-specific.
Shared layer59, display ID4 and map displayable33 do not prove common ownership,
physical transport or a usable AltScreen sink. Camera dimensions in production
configs are not native panel/CarPlay viewport measurements.

The productive live branch, output geometry and STOCK restore remain separate
Audi admission gates. The [routing CSV](../../testing/MU1438_MU1440_ROUTING_MATRIX.csv)
records the exact static/config seams without upgrading vehicle support.

This distinction is critical.

### VW first-generation AID

Volkswagen publishes:

```text
12.3-inch panel
1440 x 540 pixels
```

for the first-generation Golf/Tiguan/Passat/Arteon AID family.

### VW second-generation AID

Volkswagen publishes:

```text
11.7-inch panel
1280 x 480 pixels
```

for the newer Polo/T-Roc AID generation.

### Later MQB MOST-map renderer window

OneB1t separately documents:

```text
windowWidth  = 1010
windowHeight = 376
```

for these later MOST clusters:

- `5NA920790D` — Tiguan
- `17A920790` — T-Roc
- `5E0920790A` — Octavia

That **1010x376 value is an external map/rendering surface**, not proof that the LCD panel itself is 1010x376.

The same 1010x376 geometry being produced by the current CarPlay Stream-111 path on the MU1440/Octavia reference vehicle is therefore a strong architectural correlation, not merely a convenient arbitrary resolution.

## Direct-TS geometry question: 1010x376 vs 1280x480

The reference Octavia gives us two different but simultaneously valid geometries:

| Layer | Geometry | Evidence |
| --- | ---: | --- |
| Later-FPK physical panel class | **1280x480** | cross-brand OEM/community/diagnostic evidence |
| Stock MU1440 QNX map displayable | **1010x376** | vehicle `dmdt gd`: `DISPLAYABLE_KOMBI_MAP_VIEW` |
| OneB1t Gen2 VC window | **1010x376** | upstream README/config for 17A/5NA-D/5E0 targets |
| Current CarPlay Stream-111 baseline | **1010x376** | project vehicle-proven |

The reason the OEM map plane is smaller than the physical panel is **not yet frozen**.

Plausible explanations include:

- the stock compositor deliberately defines a map surface that fits the instrument-cluster layout rather than the complete LCD raster;
- gauge / warning / branding planes are composited separately over a larger panel;
- the cluster may internally scale the 1010x376 map plane;
- bandwidth/encoder constraints may have influenced the chosen map-plane size.

Do **not** currently state that 1010x376 merely omits pixels hidden under the gauges. On the reference vehicle, map content can still be perceived beneath partially transparent gauge overlays, so the composition is more complex than a simple opaque central cut-out.

### Current project decision

The physical-panel question and the Direct-TS coded-frame question are now deliberately separated.

For the reference target the project fixes:

```text
Direct-TS / Stream-111 outer canvas = 1010x376
```

because three independent layers converge on that geometry:

- the live MU1440 `DISPLAYABLE_KOMBI_MAP_VIEW`;
- the OneB1t later-FPK external rendering window for the matching cluster family;
- the already vehicle-proven CarPlay Stream-111 baseline.

The **1280x480** value remains useful as the physical later-FPK panel class. It does not, by itself,
establish a 1280x480 H.264/MOST decoder contract.

The project has **not** proven that the cluster decoder rejects 1280x480. Rather, the engineering
question is considered resolved for the current runtime because there is no evidence that the larger
coded frame is required to obtain the OEM map surface, while 1010x376 is independently grounded at
the stock QNX surface and the proven direct path.

Accordingly, a future 1280x480 decoder-acceptance experiment is optional research and no longer
blocks SafeArea/ViewArea calibration. If revisited, it should remain a separate bounded experiment
with no implication that physical LCD raster and external map-video contract are the same thing.

## Known MQB cluster part-number anchors

From the open `VcMOSTRenderMqb` compatibility list:

### Earlier / larger AID family

- `3G0920791` — Passat B8 / Arteon
- `5NA920791` — Tiguan
- `5G1920791` — Golf Mk7
- `5G1920794` — Golf Mk7 GTE
- `5G1920795` — e-Golf Mk7
- `5G1920798` — Golf Mk7
- `3CG920791` — VW Atlas

### Later MOST clusters explicitly using 1010x376 in that project

- `5NA920790D` — Tiguan
- `17A920790` — T-Roc
- `5E0920790A` — Škoda Octavia III

These part numbers are useful **family anchors**, not a universal compatibility whitelist.

## Continental FPK platform-family evidence

A VAG/SEAT regulatory marking document from Continental is unusually useful because it groups customer part numbers by Continental FPK homologation bundles.

One bundle (`17101001`) contains, among others:

- VW T-Roc: `17A 920 790` / `17A 920 790 A`;
- Škoda Superb: `3V0 920 790` / `3V0 920 790 A`;
- Škoda Kodiaq/Karoq: `565 920 790 A`;
- Škoda Octavia: `5E0 920 790` / `5E0 920 790 A` / `5E0 920 790 B`;
- SEAT Leon / A-SUV: `5F0 920 790` / `5F0 920 790 A`;
- VW Tiguan: `5NA 920 790 D`.

This is strong evidence that the later VW/Škoda/SEAT `...790` instruments belong to a **shared Continental FPK hardware/platform lineage**.

A separate Continental **FPK Standard / WFS 5a** group contains the older Golf/Passat/Tiguan `...791` families such as:

- Golf `5G1 920 791/A/B`;
- Passat `3G0 920 791/A/B/C/D`;
- Tiguan `5NA 920 791/A/B/C`.

That regulatory split independently aligns with the renderer evidence:

```text
older ...791 family
  -> OneB1t default "old cluster" renderer window: 800x480

later ...790 family
  -> selected OneB1t targets require: 1010x376
```

This does **not** prove that all units inside one homologation bundle use an identical LCD module, PCB revision or housing. It does make the working hypothesis of shared electronics/display architecture substantially stronger and gives us a concrete family boundary to test.

## Physical interchangeability / "same cluster, different housing"

There is substantial evidence for a **shared Continental/VDO MQB software/transport family** across VW and Škoda:

- the same MOST/H.264 map concepts;
- the same MIB2 `Dashboard_Display_Configuration` vocabulary;
- common renderer techniques;
- a single open renderer supports multiple VW and Škoda part-number families.

That is strong evidence for **software/display-path portability**.

It is **not yet sufficient evidence** that a VW AID and a Škoda VC can literally be cross-plugged as complete assemblies. Housing, bezel, immobilizer/component-protection data, coding, warning-lamp arrangement, fuel inputs and vehicle-specific software remain separate compatibility dimensions.

Current status of the "same LCD/electronics, different housing" idea: **shared Continental FPK platform lineage is now well supported; identical LCD/PCB and literal cross-brand plug compatibility remain hypotheses requiring teardown/label evidence**.

If someone can supply rear-label photos, PCB/LCD module numbers or teardown images from e.g. `5G1920791x`, `17A920790` and `5E0920790A`, this can be tightened substantially.

## Open-source implementation evidence

### OneB1t — VcMOSTRenderMqb

Repository: https://github.com/OneB1t/VcMOSTRenderMqb

Key facts:

- custom/VNC video to MQB Virtual Cockpit;
- supported Continental/VDO cluster list across VW and Škoda;
- `1010x376` config for the later cluster group;
- MIB2 Toolbox MOST patch can raise the legacy renderer path from roughly 10 to 20 fps;
- project works with the cluster's MOST map path.

Pinned revision already used by this project:

`27ea74abfcd77c16b5a5bdad3a0bfee24f707ab9`

### chopinwong01 — mhi2-android-auto-video-vc

Repository: https://github.com/chopinwong01/mhi2-android-auto-video-vc

This independently describes a VW MIB2.5 High pipeline:

```text
Android Auto secondary video
 -> stock GAL hook
 -> stream-player
 -> Displayable 3 / Context 70
 -> MOST150
 -> Virtual Cockpit
```

It explicitly identifies `/dev/mlb/isoTX2` as the VW-group VC navigation-video feed on its tested MHI2 VW target.

### adi961 — mib2-android-auto-vc

Repository: https://github.com/adi961/mib2-android-auto-vc

This is primarily a **metadata / native cluster UI** project rather than a full map-video renderer. It is useful because it confirms that the higher-level HMI/cluster integration layer is portable across selected VW MHI2 trains while Audi AU trains are not automatically compatible.

### chefranov — mhi2-au37x-carplay

Repository: https://github.com/chefranov/mhi2-au37x-carplay

Audi A3 8V / AU37x reference for **native route guidance and media metadata**, not proof of the B9 LVDS map-video topology. Keep the metadata plane separate from projected map video.

### Luka / MHI2Q and Lanye MMI Mirror

These remain important Audi comparator projects, especially for:

- native route-guidance metadata;
- cluster layout state;
- MMI-to-cluster mirroring;
- later Qualcomm/MHI2Q display handling.

They must not be used to overwrite exact MHI2 Harman transport evidence.

## Retrofit evidence

### Škoda Octavia III

Community retrofit documentation for `5E0920790A` repeatedly requires an added **MOST optical link from the VC to 5F** for navigation and related visual content.

### Škoda Superb III

Retrofit reports likewise use:

- `MOST_streaming`;
- `H264`;
- map-resolution adaptations;
- an actual MOST optical connection.

### VW Golf 7 AID

Community coding repeatedly uses:

- `Dashboard_Graphic_Variant = MOST`;
- `navigation_map_transmission_mode = MOST_streaming`;
- `navigation_map_compression_mode = H264`;
- MOST enabled in 5F.

Some early AID variants do not support navigation-map display despite looking otherwise similar, reinforcing the need to gate by exact part number/revision.

## Important boundary: do not mix MIB3 evidence

Later platforms may expose adaptation values such as:

- `IP_streaming`;
- `MOST_High`;
- Ethernet-oriented display architectures;
- Full-HD Audi VC-plus panels.

These are useful future comparators, but they are **not evidence for the MIB2/MHI2 transport contract**.

For example, the 2019+ Audi A4 facelift moved to MIB3 and offered a 12.3" Full-HD 1920x720 VC-plus. That is a different generation from the pre-facelift MIB2 B9 target discussed here.

## Capability admission fields for this project

Every new cluster target should eventually have these fields:

| Field | Why it matters |
| --- | --- |
| Brand / model / model year | prevents cross-generation mixing |
| Cluster part number | primary family anchor |
| HW / SW revision | catches same-PN generation changes |
| Cluster manufacturer | useful for family grouping |
| Physical panel diagonal | descriptive only |
| Physical panel raster | must not be confused with video viewport |
| External map/video viewport | direct relevance to Stream-111 / renderer |
| Map transport | MOST / LVDS / IP / other |
| Codec | H.264 / RLE / raw / unknown |
| MIB adaptation mode | e.g. MOST_streaming |
| MIB output device | e.g. `/dev/mlb/isoTX2`, display/context ID |
| Native metadata plane | BAP/NavSD/RGI capabilities |
| Layouts | classic/sport/full/small etc. |
| Vehicle proof | exact test status |
| Recovery path | required before write-side experimentation |

## Current project conclusions

1. **Our Škoda MU1440 + AID10 path belongs to the MQB MOST/H.264 family.**
2. **1010x376 is best treated as a map/video surface geometry, not the LCD raster.**
3. **The Audi B9 MIB2 Virtual Cockpit belongs to a different map-video transport family: LVDS for the large map.**
4. **Audi B9 still uses MOST for other cluster content, so seeing MOST support in its configuration is expected and not contradictory.**
5. **Cross-brand VW/Škoda reuse is strong at the protocol/software level; literal complete-cluster interchangeability is not yet proven.**
6. **Cluster identity must become a first-class compatibility gate alongside MHI2 firmware and `libairplay.so` ABI.**

## Sources

### OEM / service-training

- Audi eSelf Study / Networking — J794/J285 image transfer: https://audi-us.erwin-store.com/erwin/download.sealed?articleId=188823
- Audi SSP 646 — A4 (8W) vehicle electrics/electronics: https://esperformance.net/ssp/audi/SSP_646_DE.pdf
- Audi Technology Portal — early 12.3" / 1440x540 Virtual Cockpit: https://www.audi-technology-portal.de/en/electrics-electronics/controls/new-control-and-display-concepts
- Volkswagen Newsroom — AID Gen1 1440x540 and Gen2 1280x480: https://www.volkswagen-newsroom.com/en/active-info-display-3950
- Volkswagen Newsroom — T-Roc second-generation AID detail: https://www.volkswagen-newsroom.com/en/the-t-roc-2692/active-info-display-in-detail-2726
- Škoda Storyboard — MIB2-era 10.25" Virtual Cockpit examples: https://www.skoda-storyboard.com/de/pressemappe/der-neue-skoda-karoq-weltpremiere-pressemappe/konnektivitaet-modernes-infotainment-und-digitale-instrumente/
- SEAT/Continental cross-brand FPK homologation list (VW/Škoda/SEAT part-number families): https://www.seat.com/datamanual-manual/directiva_RED/ua-ua/All_platforms.pdf

### Open implementations

- OneB1t/VcMOSTRenderMqb: https://github.com/OneB1t/VcMOSTRenderMqb
- chopinwong01/mhi2-android-auto-video-vc: https://github.com/chopinwong01/mhi2-android-auto-video-vc
- adi961/mib2-android-auto-vc: https://github.com/adi961/mib2-android-auto-vc
- chefranov/mhi2-au37x-carplay: https://github.com/chefranov/mhi2-au37x-carplay
- luka-dev/mib2q-carplay-rgi: https://github.com/luka-dev/mib2q-carplay-rgi
- Lanye-z/MHI2Q-CarPlay-MMI-Mirror: https://github.com/Lanye-z/MHI2Q-CarPlay-MMI-Mirror

### Retrofit / community corroboration

- Škoda Superb VC retrofit / MOST + H.264 coding: https://www.briskoda.net/forums/topic/491347-how-to-retrofit-virtual-cockpit/
- Škoda Octavia III VC retrofit / MOST cable: https://www.briskoda.net/forums/topic/538864-retrofit-virtual-cockpit-lhd/
- VW Golf 7 AID coding / MOST_streaming + H.264: https://www.golf7freunde.de/index.php/Thread/11816-Fehlerhafte-Codierung-nach-AID-Umbau/
- Audi B9 VC retrofit discussion (use cautiously; OEM SSP is authoritative for transport): https://www.audiworld.com/forums/a4-b9-platform-discussion-212/succesful-virtual-cockpit-retrofit-guide-3014249/

## Research TODO

- [ ] collect exact panel/LCD module identifiers for `5G1920791x`, `17A920790`, `5NA920790D`, `5E0920790A`;
- [ ] compare rear labels / PCB / LCD module numbers inside the Continental `17101001` later-FPK family to determine exactly what is shared beneath the brand-specific housings;
- [ ] map `resolution_1/2/3` adaptation values to exact encoded pixel dimensions for each family;
- [x] fix 1010x376 as the current Direct-TS reference geometry from OEM/QNX + upstream + vehicle evidence; keep any 1280x480 decoder probe optional and separate;
- [ ] capture stock DisplayManager context/display IDs for MQB AID1 vs AID2;
- [ ] capture Audi B9 MU1438 LVDS display/context and native geometry;
- [ ] add SEAT/CUPRA exact cluster part numbers;
- [ ] build a read-only `cluster_probe` that reports the admission fields above.
