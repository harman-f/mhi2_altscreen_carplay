# CarPlay cluster / AltScreen configuration and control index

> **Research status · 2026-11-05:** **CARPLAY RESEARCH REFERENCE.** Preserve the original date and evidence level; newer source and actual installed behavior must be checked separately. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


Date: 2026-10-01  
Current public target: **iOS 26.7.1 (23H30)**  
Primary legacy target: Harman MHI2 / Stream 111 / instrument-cluster AltScreen

This document indexes the CarPlay configuration and control surfaces that are relevant to
instrument-cluster / auxiliary-screen work. It deliberately separates:

- receiver-advertised display configuration;
- URL-driven cluster presentation;
- AirPlay `/command` controls;
- Apple-internal scene settings/actions;
- next-generation hosted/gauge-cluster presentation;
- functionality that is practical to test on a legacy MHI2 Stream-111 receiver.

It records **derived findings only**. Apple binaries are not redistributed.

---

## 1. Current iOS 26.7.1 status

iOS 26.7.1 is build `23H30`, released 2026-09-28.

The public `blacktop/ipsw-diffs` comparison:

```text
iOS 26.7 (23H24) -> iOS 26.7.1 (23H30)
```

shows exactly one updated shared-cache dylib:

```text
/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics
```

No change is listed for:

- DashBoard;
- CarPlay.framework;
- CarPlayUIServices;
- CarKit;
- AirPlaySender;
- AVRouting.

Therefore **26.7.1 is not a new CarPlay feature revision relative to 26.7** in the public diff.
For CarPlay work, use 26.7/26.7.1 as one functional checkpoint unless contrary device evidence appears.

Evidence:

- Apple security release: https://support.apple.com/149226
- diff: https://github.com/blacktop/ipsw-diffs/tree/main/iOS/26_7_23H24_vs_26_7_1_23H30

Important limitation: the current matrix uses a full public 26.1 restore/decompile plus public
version-to-version diffs through 26.7.1. A complete public 26.7.1 decompile is not required to establish
the 26.7 -> 26.7.1 no-CarPlay-delta result, but rows marked **APPLE_INTERNAL** remain reverse-engineering
findings rather than a public API contract.

---

## 2. Version chronology

| Version | Established cluster/control state |
| --- | --- |
| iOS 17.6.1 | Classic `maps:/car/instrumentcluster...` URL model; classic cluster scene settings; `CRSUIClusterPressAction`; instrument-cluster `frameRateLimit`; ViewArea request infrastructure. |
| iOS 18.2 | Adds hosted presentation state through `hostedAltScreenPresentationType`; private URL scheme `nextGenInstrumentCluster:`; values `dcaCarousel`, `mapsMediaCarousel`, `popover`, `passengerDisplay`. |
| iOS 18.3/18.4 era | Public IPSW diffs show transition to `nextGenHostedContent:` and richer hosted Maps URL forms. |
| iOS 26.1 | Full public restore tree confirms `nextGenHostedContent:`, `mapsPresentation`, `maneuverLayout`, `displayLocation`, maps/media hosted behavior, classic cluster controls, ViewArea and frame-rate paths. |
| iOS 26.2 | Public diff adds `nextGenHostedContent:/?altScreenPresentation=deck`. Numeric enum semantics are not yet pinned here. |
| iOS 26.7.1 | No CarPlay dylib delta from 26.7 in the public 23H24 -> 23H30 diff. |

Two corrections are important:

1. `CRSUIClusterPressAction` is **not new in iOS 26**; it exists in 17.6.1.
2. instrument-cluster `frameRateLimit` is **not new in iOS 26**; it also exists in 17.6.1.

---

## 3. Classification used below

| Class | Meaning |
| --- | --- |
| `CLASSIC_E2E` | Legacy CarPlay cluster behavior with an established end-to-end path. |
| `CLASSIC_WIRE` | Accessory-visible AirPlay command/configuration, wire shape established. |
| `APPLE_INTERNAL` | Apple scene/action/settings behavior; existence does not imply an accessory command. |
| `NEXTGEN_HOSTED` | Hosted/gauge-cluster composition associated with newer multi-display architecture. |
| `CAPABILITY_GATED` | Requires a negotiated feature/advertisement before iOS uses it. |
| `MU1440_TESTABLE_NOW` | Can be tested without changing the H.264/MOST transport architecture. |
| `LEGACY_COMPAT_UNKNOWN` | Present in Apple current architecture but not proven on legacy Stream 111. |

---

## 4. Stream-111 display advertisement

The legacy auxiliary cluster is a separate screen stream, conventionally observed as type 111.

### Core display keys

| Key | Meaning | Status / notes |
| --- | --- | --- |
| `type` | AirPlay screen type; cluster AltScreen observed as 111 | `CLASSIC_E2E` |
| `uuid` | display/stream identifier used by UI and control commands | `CLASSIC_WIRE` |
| `widthPixels` | coded/display width | `CLASSIC_WIRE` |
| `heightPixels` | coded/display height | `CLASSIC_WIRE` |
| `widthPhysical` | physical width in mm | `CLASSIC_WIRE`; 0 can mean unknown |
| `heightPhysical` | physical height in mm | `CLASSIC_WIRE`; 0 can mean unknown |
| `maxFPS` | maximum accepted/rendered frame-rate ceiling | `CLASSIC_WIRE`; not a guarantee of actual source cadence |
| `features` | display-input feature bitmask | `CAPABILITY_GATED` |
| `primaryInputDevice` | preferred navigation/input device | `CAPABILITY_GATED` |
| `initialURL` | initial UI role/content URL | `CLASSIC_WIRE` |
| `initialViewArea` | initial declared ViewArea index | `CLASSIC_WIRE` |
| `adjacentViewAreas` | indices reachable from current ViewArea | `CLASSIC_WIRE` |
| `viewAreas[]` | declared geometric presentation areas | `CLASSIC_WIRE` |
| `safeArea` | safe content rectangle within a ViewArea | `CLASSIC_WIRE` |

Known MHI2 public implementation comparator:

```text
type=111
widthPixels=1010
heightPixels=376
maxFPS=40
features=0x0a
primaryInputDevice=3
initialViewArea=0
initialURL=maps:/car/instrumentcluster/map
```

For the 790/AID profile, omonob additionally advertises:

```text
ViewArea 1010x376 @ 0,0
SafeArea 606x344 @ 202,16
```

### Input feature interpretation

Historical AirPlay source resolves:

```text
features 0x02 = Knobs
features 0x08 = HighFidelityTouch
0x0a = Knobs | HighFidelityTouch

primaryInputDevice 3 = Knob
```

These are advertisement/capability values, not video-transport settings.

---

## 5. Cluster URL surface

### 5.1 Classic cluster URLs

Proven classic family:

```text
maps:/car/instrumentcluster
maps:/car/instrumentcluster/map
maps:/car/instrumentcluster/instructioncard
```

Apple item types:

| Presentation | Value |
| --- | ---: |
| Map | 1 |
| InstructionCard | 2 |
| AnyContent / base | 3 |

Classic URL query controls:

```text
showETA=yes|no|user
showSpeedLimit=yes|no|user
showCompass=yes|no|user
maneuverLayout=topAligned|leftAligned|rightAligned
```

Scene-setting values recovered from Apple code:

| Setting | Value |
| --- | ---: |
| yes | 1 |
| no | 2 |
| user | 3 |
| topAligned | 1 |
| leftAligned | 2 |
| rightAligned | 3 |

These are **real Apple cluster scene settings**, not VAG-specific parameters.

Classification:

```text
CLASSIC_E2E
MU1440_TESTABLE_NOW
```

They are the first presentation knobs to test on MU1440 because they do not require a new transport.

### 5.2 Hosted / gauge-cluster URL evolution

iOS 18.2 already contains:

```text
nextGenInstrumentCluster:
```

with:

```text
altScreenPresentation=dcaCarousel
altScreenPresentation=mapsMediaCarousel
altScreenPresentation=popover
altScreenPresentation=passengerDisplay
showETA=...
```

iOS 26.1 uses the newer private scheme:

```text
nextGenHostedContent:
```

and parses:

```text
altScreenPresentation=...
mapsPresentation=...
showETA=...
maneuverLayout=...
```

Recovered hosted presentation mapping in 26.1:

| `altScreenPresentation` | Internal value |
| --- | ---: |
| `dcaCarousel` | 1 |
| `mapsMediaCarousel` | 2 |
| `popover` | 3 |
| `passengerDisplay` | 4 |
| none / unknown | 0 |

Recovered Maps presentation mapping:

| `mapsPresentation` | Internal value |
| --- | ---: |
| `map` | 1 |
| `instructionCard` | 2 |
| `anyContent` | 3 |
| unknown/default | 3 |

Public IPSW diffs additionally show, beginning after 26.1:

```text
nextGenHostedContent:/?altScreenPresentation=deck
```

The numeric/behavioral meaning of `deck` is not yet pinned in this document.

### Critical gate

In both the 18.2 and 26.1 decompiled `DBInstrumentClusterURLHandler`:

- `applySettingsForClusterURL:` can parse the private next-generation URL family;
- `isURLSupported:` still delegates to a classic Maps-cluster URL validator that accepts
  `maps:/car/instrumentcluster...`.

That means the private hosted URL family must **not** be treated as proof that a legacy accessory can
simply send it through ordinary classic `showUI`.

Current classification:

```text
NEXTGEN_HOSTED
APPLE_INTERNAL
LEGACY_COMPAT_UNKNOWN
```

---

## 6. Apple instrument-cluster scene settings

Current Apple scene settings include:

| Setting | First checkpoint in this research | Accessory wire control? |
| --- | --- | --- |
| `itemType` | 17.6.1 | indirectly via classic URL |
| `layoutJustification` | 17.6.1 | indirectly via `maneuverLayout` |
| `showsCompass` | 17.6.1 | indirectly via classic URL |
| `showsSpeedLimit` | 17.6.1 | indirectly via classic URL |
| `showsETA` | 17.6.1 | indirectly via classic URL |
| `mapStyle` | 17.6.1 | separate appearance machinery |
| `frameRateLimit` | 17.6.1 | no legacy accessory setter proven |
| `hostedAltScreenPresentationType` | 18.2 | private/hosted URL path |
| `displayLocation` | 26.1 tree | Apple scene/display topology |

26.1 `displayLocation` logging resolves locations including:

- Center Console;
- Passenger Display;
- Secondary Cluster.

This is strong evidence that hosted content is part of a richer scene/display topology, not merely
one more query parameter bolted onto a single legacy Stream-111 surface.

---

## 7. Frame-rate controls: keep four layers separate

There are four distinct frame-rate/timing layers:

1. **receiver display ceiling**
   - `maxFPS` in the display advertisement;

2. **Apple scene render scheduling**
   - `CRSUIInstrumentClusterSceneSettings.frameRateLimit`;
   - DashBoard thermal policy;
   - CarPlay scene diff/update machinery;

3. **actual H.264 AU cadence**
   - what iOS really renders and sends at runtime;

4. **receiver transport presentation**
   - source timestamp -> MPEG-TS PTS/PCR -> physical cluster refresh.

A lower source cadence must not be repaired by assigning CFR timestamps.

The public omonob bridge is useful evidence because it keeps source timing and maps it into a
continuous PCR/PTS transport rather than assuming `PTS = frame_number / 30`.

### frameRateLimit conclusion

`frameRateLimit` existed in iOS 17.6.1. It is therefore **not an iOS-26 feature**.

Known writers include Apple/DashBoard thermal-policy and scene-host paths. No classic accessory wire
command analogous to `changeMapZoomLevel` has been established for directly setting the cluster
scene `frameRateLimit`.

Current classification:

```text
APPLE_INTERNAL
LEGACY_COMPAT_UNKNOWN
```

For MU1440, vary `maxFPS` independently and measure actual AU timestamps; do not infer that the
private scene `frameRateLimit` changed.

---

## 8. AirPlay command/control index

AirPlay control uses a binary-plist `/command` envelope conceptually of the form:

```text
{
  type: "<command>",
  params: { ... }
}
```

Direction can depend on the concrete sender/caller path. The table below is written from the
**legacy accessory/receiver integration perspective** where possible.

### High-confidence cluster controls

| Command | Known wire shape / meaning | Classification | MU1440 |
| --- | --- | --- | --- |
| `changeMapZoomLevel` | `{uuid, zoomDirection}`; 0=in, 1=out | `CLASSIC_WIRE` | test now |
| `showUI` | `{uuid, url?}`; foreground content on named display | `CLASSIC_WIRE` | test now |
| `stopUI` | `{uuid}`; URL is not part of the established stop shape | `CLASSIC_WIRE` | test now |
| `requestUI` | UI/application request; omonob uses URL-addressed calls for provider switching | `CLASSIC_WIRE` | test now, separate from showUI |
| `suggestUI` | candidate/suggestion transaction; commonly URL-list based | `CLASSIC_WIRE` | log first |
| `forceKeyFrame` | request fresh screen bitstream/keyframe | `CLASSIC_WIRE` | test now |
| `requestViewArea` | requests a declared ViewArea index for a screen UUID | `CLASSIC_WIRE` | log/answer |
| `updateViewArea` | `{uuid, viewAreaIndex, animationDurationMillis, adjacentViewAreas}` | `CLASSIC_WIRE` | high-value test |
| `updateDisplayPanels` | live display-panel renegotiation family | `CLASSIC_WIRE` / modern | later A/B |
| `uiAppearanceUpdate` | per-display UI appearance | `CAPABILITY_GATED` | later |
| `mapAppearanceUpdate` | per-display map appearance | `CAPABILITY_GATED` | later |
| `hidSendReport` | display/device-bound HID report | `CLASSIC_WIRE` | available if HID declared |
| `hidSetInputMode` | set HID mode by device UUID | `CLASSIC_WIRE` | later |
| `setNightMode` | global/advisory night-mode control | `CLASSIC_WIRE` | available |
| `setLimitedUI` | limited-UI state/elements | `CLASSIC_WIRE` | not cluster priority |
| `requestSiri` | Siri action request | `CLASSIC_WIRE` | not cluster priority |
| `accessoryAcquireFocus` / `accessoryGiveFocus` | focus-transfer family | `CAPABILITY_GATED` | later |
| `deviceOfferFocus` | controller offers focus to display region | `CAPABILITY_GATED` | later |
| `changeUIContext` | UI-context handoff | `CAPABILITY_GATED` | unresolved on MU1440 |

### Exact zoom command

```text
type = changeMapZoomLevel
params.uuid = <cluster display UUID>
params.zoomDirection = 0 | 1
```

This is a semantic cluster operation, not synthetic touch.

### Exact classic show/stop form

```text
showUI:
  params.uuid = <cluster display UUID>
  params.url  = maps:/car/instrumentcluster/map   # optional URL argument

stopUI:
  params.uuid = <cluster display UUID>
```

A URL used through `showUI` still needs to be accepted by the negotiated/approved cluster URL
surface. Private Apple scene URLs are not automatically classic `showUI` URLs.

### ViewArea transition

Established update shape:

```text
type = updateViewArea
params.uuid = <display UUID>
params.viewAreaIndex = <declared index>
params.animationDurationMillis = <duration>
params.adjacentViewAreas = [...]
```

The transition uses a **declared ViewArea index**, not a new H.264 stream and not a raw rectangle in
the runtime command.

This is one of the highest-value legacy-compatible experiments because it can alter presentation on
an existing screen/session.

### updateDisplayPanels

Modern SDK-ground-truth material exposes a live display-panel update family with fields including:

```text
displayPanels[]:
  name
  originX / originY
  pixelWidth / pixelHeight
  physicalWidth / physicalHeight
  fullScreen
  extendedMode
  zIndex
  displayUUID
  primaryInputDevice
  maxFPS
  initialURL
  initialViewArea
  videoStreams
  viewAreaTransitionControl
  viewAreaStatusBarEdge
  drawUIOutsideSafeArea
  uiAppearanceMode
  mapAppearanceMode
  zoomFactor
  properties
```

This is materially more powerful than classic static `displays[]`, but should not be enabled on
MU1440 before the legacy ViewArea path is isolated and understood.

---

## 9. Capability/config gates relevant to cluster behavior

Modern receiver configuration research exposes capability flags including:

```text
enablesUIAppearance
enablesMapAppearance
enablesViewAreas
enablesFocusTransfer
enablesUIContext
enablesUISync
enablesCornerMasks
enablesEnhancedSiri
enablesVideoPlayback
enablesHEVC
```

For this project the important ones are:

| Gate | Effect |
| --- | --- |
| `enablesViewAreas` | permits multi-ViewArea negotiation/runtime transitions |
| `enablesUIAppearance` | arms per-display UI appearance controls |
| `enablesMapAppearance` | arms per-display map appearance controls |
| `enablesFocusTransfer` | arms focus transfer between CarPlay/native surfaces |
| `enablesUIContext` | required for the richer UI-context family |
| `enablesCornerMasks` | geometry/cutout capability; separate from ViewArea switching |

Do not couple `supportsFocusTransfer` to ViewArea acceptance. Public receiver work shows these are
orthogonal features.

---

## 10. Semantic cluster press action

Apple exposes:

```text
CRSUIClusterPressAction
  initWithPressType:
  actionType
```

and:

```text
CRSUIClusterPressBSActionsHandler
  -> selectButtonPressedWithType:
```

This exists in iOS 17.6.1 and later.

In iOS 18.2, DashBoard's `DBInstrumentClusterApplicationViewController::buttonPressedWithType:`:

1. validates that the hosted Apple cluster app supports the press type;
2. creates `CRSUIClusterPressAction`;
3. sends it as a scene action to the hosted cluster app.

The same generation explicitly associates support with Apple `CarTrip` / `CarTirePressure`
cluster apps.

Therefore the current best classification is:

```text
APPLE_INTERNAL
not a proven accessory AirPlay command
```

Do not invent a `pressType` wire packet solely because the scene action class exists.

Use the known HID/knob or semantic `changeMapZoomLevel` wire paths for MU1440 controls unless a
real external press producer is recovered.

---

## 11. mapsMediaCarousel and other hosted presentations

`mapsMediaCarousel` is real Apple first-party state.

By iOS 26.1:

- Maps reads `hostedAltScreenPresentationType`;
- Maps has cluster chrome/config logic for that presentation;
- Media participates in a cluster state described as Maps + Media composition.

This is stronger than a dead string.

However, the scene also carries modern `displayLocation` and hosted-presentation state, and the
private hosted URL family is not accepted by the classic URL validator.

Therefore:

```text
mapsMediaCarousel = real Apple feature
legacy Stream-111 invocation = unresolved
```

The same guardrail applies to:

- `dcaCarousel`;
- `popover`;
- `passengerDisplay`;
- `deck` (seen in post-26.1 public diffs).

For legacy MHI2, the alternative architecture remains valid and independent:

```text
direct Stream-111 map video
+
native VAG cluster NowPlaying / AudioSD composition
```

That route should be evaluated separately from any attempt to impersonate a next-generation hosted
gauge-cluster scene.

---

## 12. MU1440 experiment order

Keep transport and control changes independent.

Recommended order:

1. `changeMapZoomLevel` with the current Stream-111 display UUID.
2. If required, A/B `features=0x0a` + `primaryInputDevice=3`.
3. `showUI` classic content:
   - base / AnyContent;
   - map;
   - instruction card.
4. Classic query controls:
   - `showETA`;
   - `showSpeedLimit`;
   - `showCompass`;
   - left/right/top `maneuverLayout`.
5. Declare two legacy ViewAreas and exercise `requestViewArea` / `updateViewArea`.
6. Measure whether the Type-111 session remains intact during ViewArea transitions.
7. Test `uiAppearanceUpdate` / `mapAppearanceUpdate` only after the matching enables flags are
   advertised.
8. Test `updateDisplayPanels` separately from legacy ViewArea switching.
9. Probe `nextGenHostedContent` only behind an explicit experimental switch and only after a real
   capability/scene gate has been identified.
10. Keep `maxFPS`, actual AU cadence, scene `frameRateLimit`, PTS/PCR timing and physical VC refresh
    as separate measurements.

---

## 13. Cross-reference summary

| Function / setting | 17.6.1 | 18.2 | 26.1 | 26.7.1 status | Legacy MU1440 |
| --- | --- | --- | --- | --- | --- |
| classic cluster URLs | yes | yes | yes | no 26.7->26.7.1 delta | test now |
| showETA/speed/compass/layout | yes | yes | yes | no 26.7->26.7.1 delta | test now |
| `CRSUIClusterPressAction` | yes | yes | yes | no evidence of removal | Apple internal |
| cluster `frameRateLimit` | yes | yes | yes | no 26.7->26.7.1 delta found | internal policy |
| `hostedAltScreenPresentationType` | no evidence in 17.6.1 | yes | yes | persists through current diff history | next-gen/hosted |
| `nextGenInstrumentCluster:` | no | yes | superseded | historical | not legacy target |
| `nextGenHostedContent:` | no | no in 18.2 | yes | current family; no 26.7.1 delta | gate unresolved |
| `mapsMediaCarousel` | no | yes | yes | no removal surfaced | gate unresolved |
| `displayLocation` scene setting | not in 18.2 class | not in 18.2 class | yes | modern topology | not classic wire |
| `deck` presentation string | no | no | not in 26.1 parser | introduced after 26.1 | unresolved |
| semantic map zoom wire command | corroborated family | yes | protocol persists | no 26.7.1 delta | test now |
| ViewArea runtime switch | infrastructure exists | yes | yes | active modern family | high-value test |
| `updateDisplayPanels` | later/modern | present by 18.2 CarKit | yes | modern family | later A/B |

---

## 14. Pinned evidence used for this index

Public iOS reverse material:

- `SuperChaoM/iPhone15-3_17.6.1_21G101_Restore@95df6b804bee0e01538eb2ddad0413609938d063`
- `EthanArbuckle/iPhone17-1_18.2_22C152_Restore@e26ed4563f78871c59d2d96856756a65d62517e5`
- `EthanArbuckle/iPhone18-3_26.1_23B85_Restore@90aa0cfe59d9682b4265e1354c8b19ec3c7823ab`
- `blacktop/ipsw-diffs`, especially:
  - 18.2 -> 18.3 hosted URL transition;
  - 26.1 -> 26.2 `deck` addition;
  - 26.7 (23H24) -> 26.7.1 (23H30) no-CarPlay-dylib delta.

Protocol / receiver references:

- `45clouds/WirelessCarPlay@51145ef55f8dd9f1cbadd58353cacb5e0ca215e9`
- `lvalen91/ocbm@c9a718d0ca49d2f4dff458febc8eb833283a75bd`
- `omonob/MHI2-Carplay-Maps@49882eb56db83a7b42f185adb426161f35a08295`
- `arctus/mib2-carplay-rgi-altscreen@404ccc23450e385a0183d37fc93677a0c9a5637d`
- `luka-dev/mib2q-carplay-rgi`

Related project docs:

- `STREAM111_PROTOCOL.md`
- `VC_VIEWAREA_STATE.md`
- `IOS27_SENDER_LIFECYCLE.md`
- `PUBLIC_REFERENCES.md`

---

## 15. Research rule

For every future parameter, record separately:

1. the string/class/key exists;
2. an Apple caller writes it;
3. a wire command exists;
4. a public receiver implements the wire shape;
5. a legacy Stream-111 receiver advertises the required capability;
6. MU1440 accepts it without transport changes;
7. vehicle-visible behavior is observed.

Only step 7 closes the MU1440 behavior question.
