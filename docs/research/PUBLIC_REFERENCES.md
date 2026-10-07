# Public prior art and external research sources

This project deliberately documents the public work that materially informed the research.

The goal is not only attribution. These are the places a new contributor should inspect before
duplicating months of work.

## Core references

### Luka — MHI2Q CarPlay / RGI

https://github.com/luka-dev/mib2q-carplay-rgi

Relevant for:

- CarPlay/RGI architecture;
- HMI/JXE patch lineage;
- native integration patterns;
- route-guidance semantics;
- historical MHI2/MHI2Q issue discussion.

### Luka — QNX 6.5 ARMv7 toolchain

https://github.com/luka-dev/qnx65-armv7-toolchain

Pinned project revision:

```text
56a66557245af14077678cd28a83ce3a337d9e2d
```

Used to make project-owned QNX components publicly rebuildable.

### Luka — JXE reconstruction

https://github.com/luka-dev/jxe2jar

Pinned revision used in related MHI2 Java work:

```text
3bae6e82177c7084a008c42373042e6eebf5653e
```

For this project's internal Java/JXE comparisons, **this is the preferred reconstruction reference**. It remains external rather than bundled/redistributed; the public-tooling boundary does not change its role as the internal comparison baseline.

### OneB1t — VC MOST renderer

https://github.com/OneB1t/VcMOSTRenderMqb

Pinned reference revision:

```text
27ea74abfcd77c16b5a5bdad3a0bfee24f707ab9
```

Important for understanding the MQB Virtual Cockpit rendering/MOST path.


External community link published by that project:

https://t.me/+MCIqkmX6bjY3NTE0

The upstream README also documents the useful performance comparator for its VNC renderer path:
approximately 10 fps for the C++ renderer and an optional 20 fps MOST patch. This is not an
apples-to-apples benchmark against direct CarPlay Stream 111, but it is a useful architectural
contrast because the VNC approach involves screen capture/rendering rather than carrying the native
CarPlay auxiliary H.264 stream.

### Lanye — MHI2Q CarPlay / MMI Mirror

https://github.com/Lanye-z/MHI2Q-CarPlay-MMI-Mirror

Useful comparator for MHI2Q native hooks, cluster presentation, watchdog/recovery and Luka-derived
RGI/HMI structure.

### Yuedi — public MHI2Q CarPlay AltScreen

https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen

Particularly useful as a public, inspectable AltScreen comparator.

The native `libcarplay_altscreen.so` is useful for studying:

- PlatformControl command classification;
- Type-111 attach/config lifecycle;
- ScreenStream creation;
- `suggestUI`;
- lifecycle/recovery structure.

It is treated as comparator evidence, not as MU1440 source authority.

## Additional useful projects

### chefranov/mhi2-au37x-carplay

Public Harman-MHI2 CarPlay work derived from adjacent Luka concepts. Useful when comparing what must
be rewritten for classic MHI2 rather than MHI2Q.

### JeniCzech92/lsdtool

Useful MIB2 LSD/JXE extraction/rebuild tooling and a clearly licensed known-working cross-check. Historical baselines may reference it, but new internal comparisons should use `luka-dev/jxe2jar` as the primary reconstruction baseline.

### grajen3/mib2-lsd-patching

Historical MIB2 LSD Java/HMI patching lineage.

### adi961/mib2-android-auto-vc

Useful adjacent MHI2/Virtual-Cockpit Java/HMI evidence.

## Naming boundary for comparator evidence

Comparator and upstream names are intentionally retained here and in provenance/evidence documents
because precise attribution matters. They should not become project-owned runtime, profile, branch,
artifact or UI identifiers. Implementation-facing names describe behavior (for example, a classic
single-view profile or a parity-drive runtime), while this catalog records whose prior work informed
the research.

## How third-party/commercial comparators are handled

The project may study lawfully obtained binaries/packages to understand architecture or behavior.

The public repository does **not** mirror proprietary/commercial payloads.

What can be published instead:

- hashes;
- high-level component roles;
- symbol names;
- protocol vocabulary;
- independently derived state-machine findings;
- comparisons against public implementations;
- project-owned clean implementation.

## Why this catalog exists

If a future contributor discovers an old branch, issue, fork or binary that closes one of the
remaining gaps, please add it.

A high-quality source contribution should record:

- repository/project;
- exact commit/tag where possible;
- platform generation;
- what fact it supports;
- whether the evidence is source, binary behavior or secondary commentary.

For more of the intentionally less-polished notes, there is one more file in the repository tree.


## Apple official CarPlay material

### WWDC19 — Advances in CarPlay Systems

https://developer.apple.com/videos/play/wwdc2019/252/

High-value public facts:

- multiple independent H.264 streams for instrument-cluster use;
- map and maneuver/instruction-card presentation;
- ViewArea / SafeArea;
- multiple declared ViewAreas;
- runtime resizing/transition concepts;
- route-guidance metadata remains a separate plane from projected video.

This is official evidence for the broad secondary-display architecture. It does not publicly name
the numeric stream type 111.

### WWDC22 — navigation apps and instrument-cluster scenes

https://developer.apple.com/videos/play/wwdc2022/10016/

Useful for understanding the app-side instrument-cluster scene lifecycle and why head-unit support
alone does not guarantee identical Apple Maps / Google Maps / Waze behavior.

Relevant public API family includes:

- `CPSupportsInstrumentClusterNavigationScene`;
- instrument-cluster CarPlay scene/session roles;
- `CPInstrumentClusterControllerDelegate`.

### WWDC25 — multi-screen navigation evolution

https://developer.apple.com/videos/play/wwdc2025/216/

Useful chronology/background for app-provided navigation across multiple vehicle screens.

## Independent CarPlay receiver reverse engineering

### CPC200 / Carlinkit resources

Repository:

https://github.com/lvalen91/CPC200-CCPA_resources

Pinned reference used during the research:

```text
951780eb856b879b60c02a7d2c3112229eba1eac
```

Especially useful:

- protocol/runtime timelines;
- independent observation of AirPlay screen stream **type 111**;
- `_AltScreenSetup`, `_AltScreenStart`, `_AltScreenTearDown`;
- `featureAltScreen`;
- `featureViewAreas`;
- instrument-cluster URL family;
- NaviScreen/ViewArea/SafeArea concepts.

Relevant documentation:

https://github.com/lvalen91/CPC200-CCPA_resources/blob/main/documentation/02_Protocol_Reference/audio_protocol.md

https://github.com/lvalen91/CPC200-CCPA_resources/blob/main/documentation/06_Reference/firmware_internals.md

This is important independent evidence because it is neither the MU1440 implementation nor the
commercial MHI2Q comparator.

### carlink_linux capabilities research

Repository:

https://github.com/lvalen91/carlink_linux

Pinned reference used during the research:

```text
fbbfa59400dac4704f34a5d76e745080ce7d6338
```

Capability reference:

https://github.com/lvalen91/carlink_linux/blob/main/docs/CARPLAY_CAPABILITIES.md

Useful for modern capability/feature-key cross-correlation. Treat modern wire-level conclusions as
reverse-engineered evidence unless independently confirmed on the exact target.

## Historical CarPlay Communication Plug-in / AccessorySDK mirrors

These repositories expose historical source concepts that are useful for stable semantic names and
receiver behavior.

They are **reference material only**. Do not wholesale copy Apple-origin source into this project.

### maaiika/Carplay

https://github.com/maaiika/Carplay

Pinned reference:

```text
482d3d7ea289317cc827f9df29734daad49a8e17
```

Useful historical concepts include:

- `requestUI`;
- `forceKeyFrame`;
- `setUpStreams`;
- `tearDownStreams`;
- display UUIDs;
- display-bound HID devices;
- primary input device semantics;
- ScreenStream receiver behavior.

### 45clouds/WirelessCarPlay

https://github.com/45clouds/WirelessCarPlay

Pinned reference:

```text
51145ef55f8dd9f1cbadd58353cacb5e0ca215e9
```

Contains older AccessorySDK / CarPlay Communication Plug-in-derived material and protocol
documentation. Use it to understand stable historical concepts, not as a specification for modern
AltScreen behavior.

## Evidence rule for external protocol sources

Prefer triangulation:

```text
official Apple architecture
      +
independent receiver RE
      +
historical receiver semantics
      +
exact iOS build RE
      +
exact MU1440 vehicle/binary evidence
```

No single public mirror or third-party implementation overrides contradictory exact-target evidence.
