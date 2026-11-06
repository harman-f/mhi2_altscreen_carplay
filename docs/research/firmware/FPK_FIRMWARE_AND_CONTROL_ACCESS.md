# MIB2-era FPK / Virtual Cockpit firmware and control access

> **Research status · 2026-11-05:** **FIRMWARE RESEARCH REFERENCE.** Static comparison is not a supported vehicle or installer claim. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


**Research status:** 2026-09-28  
**Primary target:** Škoda Octavia III `5E0920790A` / Continental FPK Entry / `EV_DashBoardVDDMQBA0 001026`

This note separates four very different kinds of "Virtual Cockpit modification":

1. normal diagnostic coding/adaptation;
2. datasets / parameterization;
3. official cluster firmware flashing;
4. true custom cluster-firmware reverse engineering / patching.

They should not be treated as equivalent.

## Short conclusion

For the MQB MIB2-era Škoda/VW/SEAT clusters researched so far:

- **coding/adaptation access is broad and well documented;**
- **official cluster firmware flashing is real and publicly evidenced;**
- the later Škoda `...790A` family has known software progression such as **1691 -> 1703** and field reports of **1711**;
- **no mature open-source project was found that already provides a complete patch/flash workflow for Continental FPK Entry firmware** in the way MIB2 High projects patch QNX/Java; however, active public research now exists around extracting and reflashing cluster firmware;
- many visually impressive "cluster mods" are therefore **not cluster-firmware hacks** at all;
- the strongest open CarPlay/cluster projects implement new behavior on the **head unit**, then drive the stock cluster through existing DisplayManager / DSI / BAP / MOST contracts.

That is encouraging for this project: OEM-like view switching may be achievable without modifying the Škoda cluster firmware.

## Access-layer matrix

| Layer | Example | Evidence | Relevance |
| --- | --- | --- | --- |
| Diagnostic coding / adaptations | logos, color themes, sport view, speedometer scale, displayed functions | strong public VCDS/OBDeleven evidence | low-risk way to expose features already present in cluster firmware |
| Dataset / parameterization | model/brand/function configuration | retrofit and VAG coding communities | may explain cross-brand feature differences on common FPK hardware |
| Official firmware SWDL | FPK software 1691 -> 1703 / later 1711 reports | public Škoda/VAG forum evidence | proves a real cluster firmware update path exists |
| Infotainment-side cluster control | DisplayManager contexts, BAP map state, steering-wheel inputs, map visibility | open MHI2/MHI2Q projects | most promising route for our runtime map/view switching |
| Custom cluster firmware patch | replacing/decompiling executable code inside J285/FPK | **not found as a mature open project for the MQB FPK Entry family** | longer-term research target |

## Škoda Octavia III FPK Entry

### Hardware / software family

Public retrofit evidence distinguishes:

- `5E0920790` — earlier software/features;
- `5E0920790A` — later revision with the sporty display and higher software level.

A commonly observed later unit is:

```text
Part number: 5E0 920 790 A
Component:   KOMBI
HW:          508
SW:          1691
ODX:         EV_DashBoardVDDMQBA0
ODX version: 001026
```

The same diagnostic family appears on related later Continental FPK Entry clusters across Škoda, SEAT and VW.

### Existing views are firmware capabilities

Retrofit reports are useful here because they show that the visual modes reside in the cluster platform:

- `5E0920790A` adds the "sporty" display compared with the earlier `5E0920790`;
- factory-like operation requires the steering-wheel **VIEW** control;
- coding/adaptation selects vehicle-specific behavior and available functions.

This is evidence that many apparent "UI modifications" are actually activation or selection of resources already compiled into the FPK software.

### Real firmware update path

Public reports document an update path for the Škoda FPK family:

```text
508 / 1691
  ->
509 / 1703
```

for clusters including:

- `5E0920790A` — Octavia;
- `565920790A` — Kodiaq/Karoq;
- `3V0920790A` — Superb.

The package name reported in the field is:

```text
VW_SK_FPKE_VW_18S1_1703_S_MHI2
```

and reports of `5E0920790A` with software **1711** also exist.

The update flow performs integrity/signature checks; community reports mention SHA1/checksum and signature failures. This is consistent with a signed/validated SWDL mechanism, not a raw writable filesystem comparable to the MIB QNX unit.

### What is *not* currently public

In the sources searched so far, there is no strong public evidence of:

- shell access to `5E0920790A`;
- a browsable cluster filesystem;
- an open custom bootloader;
- a completed public decompiler/patching project for the complete FPK Entry firmware;
- an open project replacing the cluster HMI executable;
- a custom signed firmware chain for these `...790A` units.

Absence from public search is not proof that private commercial/Telegram tooling does not exist.

## Active public FPK firmware RE lead

OneB1t's `VcMOSTRenderMqb` Issue #4, **"Instrument Cluster Graphics"** (opened 2025-10-12), is directly relevant.

The author of that issue is investigating:

- flashing an instrument cluster over UDS/CAN;
- obtaining raw firmware blocks from ODX data inside VAG FRF flash containers;
- changing cluster graphics such as the startup logo;
- the `AUDI-AES-128` encrypted / LZSS-compressed payload format reported by the ODX;
- the cluster security-access path and the UDS RequestDownload mode.

This is **research/proposal evidence, not a proven public FPK flashing solution**. Nevertheless it is the clearest public lead found so far that somebody is actively pursuing custom graphics at the cluster-firmware level on the same MQB VC ecosystem.

Upstream:
https://github.com/OneB1t/VcMOSTRenderMqb/issues/4

### Reusable VAG FRF / ODX tooling already exists

The outer VAG flash-container problem is well understood publicly:

- VAG FRF container decryptors exist;
- FRF commonly unwraps into ODX/ODX-F definitions and binary blocks;
- public tooling exists for parsing address/block metadata;
- AES/LZSS decompression pipelines are implemented for several other VAG ECU families.

Examples:

- `kolyandex/VAG-FRF-Extractor`;
- `bri3d/VW_Flash` and related FRF/SA2 work;
- `dspl1236/vag-tcu-tools` for modern worked examples of FRF -> ODX -> encrypted/compressed binary extraction.

These tools do **not** by themselves supply the correct crypto material, memory map or checksum/signature logic for `EV_DashBoardVDDMQBA0`. They do, however, mean we do not need to reinvent the generic FRF/ODX container layer when a legitimate FPK flash package is available.

## Exact Octavia 5E hardware-access lead

A public programmer/repair thread names the exact Škoda cluster `5E0920790A` and reports the MCU as:

```text
Renesas RH850/D1L1
R7F701401
```

The attempted read used an RH850/V850 programming cable **soldered to the cluster PCB**. This is consistent with the absence of a user-accessible debug connector on the assembled cluster.

Renesas' own documentation identifies `R7F701401` as RH850/D1L1. The D1L1 family supports debugger/programmer access, including E1-based debug and 1-wire / 2-wire UART programming modes. This should be understood as an MCU programming/debug interface, **not evidence of a stock interactive serial shell**.

Commercial VAG RH850/V850 programmer documentation independently shows the same physical-access pattern for MQB clusters: the unit is opened and the programmer cable is soldered to PCB points; the current Abrites software exposes per-part-number wiring diagrams. It also warns that reading these MCUs is a difficult/risky operation.

Implication for this project:

- a hidden external service connector is not required;
- PCB pads / MCU programming pins are the likely bench-access route;
- obtaining a raw MCU read may be possible with suitable supported tooling;
- a raw MCU dump would be far more useful for RH850 disassembly than the encrypted/compressed SWDL `Data_n.bin` blocks;
- do not assume that programming UART == runtime console.

Public evidence:

- exact `5E0920790A` / `R7F701401` soldered-read report:
  https://carmasters.org/topic/60343-multi-prog-xhorse/page/6/
- Renesas RH850/D1L/D1M datasheet:
  https://www.renesas.com/en/document/dst/rh850d1ld1m-data-sheet
- Abrites RH850/V850 programmer manual:
  https://abrites.it/manual/abrites-rh850-v850-programmer-user-manual.pdf

## Coding / adaptation can look like a firmware mod

Examples from the same MQB digital-cluster ecosystem include:

- enabling sport/Cupra-style views;
- changing displayed vehicle derivative/logo;
- changing central-display style;
- enabling multi-color instrument illumination;
- choosing speedometer scale / end value;
- exposing additional pages/functions.

These operations normally change adaptation/coding values. They do **not** prove that executable firmware was modified.

This distinction matters when evaluating screenshots or retrofit-shop claims.

## Audi MHI2Q: why the cluster can look "patched" without cluster firmware changes

The open `luka-dev/mib2q-carplay-rgi` implementation is especially informative.

It patches the **MHI2Q head unit**, including Java/HMI and native components. The Virtual Cockpit keeps its stock firmware.

The head-unit patch:

- declares a new DisplayManager context;
- switches between stock and custom contexts through `DisplayManager.switchContext()`;
- monitors/feeds Navigation BAP state;
- observes cluster map visibility/presentation state;
- repurposes selected steering-wheel input;
- composes a new maneuver displayable over the stock native map.

For example, the active custom context is built around:

```text
dc[80] = {98 maneuver, 101/102 backing, 33 stock native map}
```

while stock context `74` remains the normal resting cluster context.

The project explicitly keeps the cluster's own native map and controls how the head unit feeds the cluster.

### VIEW / size state is also head-unit-visible

The same project documents the stock navigation view-size model:

```text
NAV_VIEW_SIZE_CHOICE
0 = fullscreen
1 = smallscreen
```

and observes that state in its head-unit Java layer.

That is a critical precedent for this project: the instrument-cluster VIEW/layout selection is not necessarily opaque inside the cluster. The MIB/HMI can know about it and react to it.

### Steering-wheel integration

The Audi project also observes raw multifunction-wheel events and selectively repurposes them while preserving stock behavior.

Again, this is implemented in the head-unit Java/HMI stack; it does not require a modified instrument-cluster firmware.

## MMI Mirror / CarPlay mirror projects

The MHI2Q MMI-Mirror projects similarly modify the head unit and use its Green Engineering Menu / QNX render path to drive the Virtual Cockpit.

They should **not** be cited as evidence of an Audi VC firmware patch.

Their value to us is architectural:

- cluster display ownership can be controlled from the HU;
- custom video/displayables can be integrated into existing cluster layouts;
- runtime state can select different crops/layouts;
- custom menu items can be added on the HU side.

## Implication for the Škoda MU1440 project

For the Octavia `5E0920790A`, the priority should remain **head-unit-side control before cluster-firmware modification**.

Promising seams to prove on the exact Škoda MHI2 stack:

1. raw VIEW-button event and stock key tuple;
2. stock cluster current-view / map-size state;
3. exact equivalent of Audi's `NAV_VIEW_SIZE_CHOICE` / `IViewSizeManager`;
4. Navigation-BAP map presentation / visibility state;
5. stock DisplayManager context transitions caused by VIEW;
6. whether a custom context or our Stream-111 ViewArea can follow those transitions;
7. whether the selected state can be surfaced as an OEM-like menu or long-press action without touching FPK firmware.

This is likely a much shorter path to:

```text
OEM map / CarPlay map
full / small
layout A / layout B
```

than reverse-engineering and resigning the cluster firmware.

## Cluster-firmware research track

The firmware path is still valuable as a separate research track.

A safe read-only progression would be:

1. acquire legitimate 1691 / 1703 / 1711 update packages for the exact FPK family;
2. archive package hashes and manifests;
3. identify container/file structure and compression;
4. compare versions to locate display assets, configuration tables and executable regions;
5. inspect update metadata for target part numbers, memory regions and integrity/signature scheme;
6. capture an authorized ODIS/SWDL update trace on a bench or test cluster if available;
7. only then decide whether direct cluster RE adds anything that cannot already be done from MIB/BAP/UDS.

Do not conflate this with immobilizer/component-protection manipulation; those are separate security domains and are unnecessary for the display research goal.

## Public sources

### Škoda / MQB cluster firmware and retrofit

- BRISKODA — Virtual Cockpit retrofit, `5E0920790` vs `5E0920790A`, VIEW button and MOST:
  https://www.briskoda.net/forums/topic/508621-virtual-cockpit-retrofit-5e0920790-vs-5e0920790a/
- BRISKODA — MIB2.5 + VC install:
  https://www.briskoda.net/forums/topic/506503-mib-25-and-vc-install/
- BRISKODA — FPK update discussion, `1691 -> 1703` / same Škoda family:
  https://www.briskoda.net/forums/topic/509689-2068282-digital-instrument-panel-fpk-flickering-indicator/
- Digital Eliteboard — Škoda FPK update using `VW_SK_FPKE_VW_18S1_1703_S_MHI2`, checksum/signature observations:
  https://www.digital-eliteboard.com/threads/skoda-fpk-aid-virtual-cockpit-software-update-failure.522898/
- OneB1t — custom MOST renderer, including `5E0920790A`:
  https://github.com/OneB1t/VcMOSTRenderMqb

### Related FPK coding evidence

- SEAT Leon `5F0920790A` / SW1701 coding and sport-view examples:
  https://dx.dragan.ba/leon5f/
- VW MQB AID coding examples:
  https://vwcoding.ru/en/MQB/AID/

### Head-unit-side cluster control

- Luka MHI2Q CarPlay RGI:
  https://github.com/luka-dev/mib2q-carplay-rgi
- Display-context implementation:
  https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/docs/cluster/display-contexts.md
- Steering-wheel / route-info integration:
  https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/docs/input/steering-wheel.md
- Lanye MHI2Q MMI Mirror:
  https://github.com/Lanye-z/MHI2Q-CarPlay-MMI-Mirror

## Search limitation

No reliable publicly indexed Telegram source for this exact `5E0920790A` firmware family was found in this research pass. Private groups or commercial tooling may contain additional information that normal web indexing cannot see.
