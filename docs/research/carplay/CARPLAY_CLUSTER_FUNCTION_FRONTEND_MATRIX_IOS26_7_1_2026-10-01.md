# CarPlay cluster function / frontend-effect matrix — iOS 26.7.1

> **Research status · 2026-11-05:** **CARPLAY RESEARCH REFERENCE.** Preserve the original date and evidence level; newer source and actual installed behavior must be checked separately. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


Date: 2026-10-01  
Current public target: **iOS 26.7.1 (23H30)**  
Legacy project target: Harman MHI2 auxiliary screen / Stream 111

This is the second-pass deep dive behind the broader
[CarPlay cluster / AltScreen configuration index](CARPLAY_CLUSTER_CONFIGURATION_INDEX_IOS26_7_1_2026-10-01.md).

The purpose of this document is to answer a narrower question:

> If a CarPlay cluster setting, command or presentation mode exists, what does it actually change in the
> visible frontend, which URL/view does it belong to, and how strong is the evidence?

The main correction from earlier research is that several similarly named controls live on different
planes. In particular there are **three unrelated zoom systems**:

1. semantic cluster **map zoom** (`changeMapZoomLevel`);
2. Apple-internal cluster zoom Scene Actions (`CRSUIClusterZoomAction`);
3. whole-CarPlay **Smart Display Zoom / display scaling** (`displayScaleMode` + `ZoomFactor`).

They must not be mixed.

---

## Evidence legend

| Mark | Meaning |
| --- | --- |
| **O** | Official Apple public documentation / WWDC behavior. |
| **P** | Proven in a concrete Apple binary/decompiled call path. |
| **W** | Proven/corroborated at the AirPlay/CarPlay wire or receiver-SDK level. |
| **D** | Device-proven in an independent receiver implementation. |
| **I** | Inference from names/layout state; useful, but exact visible behavior is not fully pinned. |

For legacy MHI2, **test now** means the function can be exercised without replacing the current
Stream-111 H.264 transport architecture. It does not mean a particular OEM cluster is guaranteed to
honor the result.

---

## 1. Current iOS 26.7.1 checkpoint

The public `blacktop/ipsw-diffs` comparison for:

```text
iOS 26.7 (23H24) -> iOS 26.7.1 (23H30)
```

shows one updated shared-cache dylib:

```text
/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics
```

No change is listed for DashBoard, CarKit, CarPlay.framework, CarPlayUIServices, AirPlaySender or
AVRouting.

Therefore **26.7.1 does not add a visible CarPlay control-surface delta relative to 26.7** in that
public diff. This does **not** prove that every intermediate 26.x release was CarPlay-identical; the
known 26.x evolution is summarized later.

Evidence:

- https://support.apple.com/149226
- https://github.com/blacktop/ipsw-diffs/tree/main/iOS/26_7_23H24_vs_26_7_1_23H30

---

## 2. Frontend-effect matrix

The original single table became too wide to be useful on GitHub. It is now split by functional layer.
Public visual references are attached **directly to the relevant rows/sections** instead of living only
in a separate reference appendix.

### 2.1 Classic cluster navigation and controls

| Function | View / scope | Visible frontend effect | Evidence / visual reference |
| --- | --- | --- | --- |
| `maps:/car/instrumentcluster` | classic cluster base | Generic / AnyContent navigation presentation rather than map-only or turn-card-only content. **MU1440: test now.** | **P** · [Apple CarPlay docs](https://developer.apple.com/documentation/carplay) |
| `.../map` | `maps:/car/instrumentcluster/map` | Map-centric cluster presentation. **MU1440: test now.** | **O+P** · [WWDC19 second-screen examples](https://developer.apple.com/videos/play/wwdc2019/252/) |
| `.../instructioncard` | `maps:/car/instrumentcluster/instructioncard` | Maneuver / guidance-card presentation instead of the map view. **MU1440: test now.** | **O+P** · [WWDC19](https://developer.apple.com/videos/play/wwdc2019/252/) |
| `showETA=yes/no/user` | classic navigation UI | Shows/hides ETA content; TemplateUIHost drives the ETA tray/controller. **MU1440: test now.** | **O+P** · [WWDC23](https://developer.apple.com/videos/play/wwdc2023/10150/) |
| `showSpeedLimit=yes/no/user` | classic navigation UI | Shows/hides the speed-limit sign/indicator. **MU1440: test now.** | **O+P** · [WWDC23](https://developer.apple.com/videos/play/wwdc2023/10150/) |
| `showCompass=yes/no/user` | classic navigation UI | Shows/hides compass / heading indication. **MU1440: test now.** | **O+P** · [WWDC23](https://developer.apple.com/videos/play/wwdc2023/10150/) |
| `maneuverLayout=topAligned/leftAligned/rightAligned` | classic + hosted navigation | Repositions/justifies maneuver/guidance content and changes map insets/layout. **MU1440: test now.** | **P** |
| `itemType` | derived scene setting | Selects map (1), instruction card (2), or generic/AnyContent (3); causes a real child-controller change. | **P** |
| `changeMapZoomLevel` | cluster display UUID + map | Semantic map-camera zoom, completely separate from touch emulation. Wire values: **0=in, 1=out**. **MU1440: highest-priority test.** | **O+W** · [WWDC23 — Apple explicitly calls out cluster map zoom](https://developer.apple.com/videos/play/wwdc2023/10150/) |
| `CRSUIClusterZoomAction` | Apple hosted Scene Action | Internal semantic zoom event. Different enum: **1=in, 2=out**. Do not emit as an AirPlay command. | **P** |
| `showUI` / `stopUI` | display UUID + approved URL | Presents or removes the chosen cluster UI without redefining the video transport. **MU1440: test now.** | **W** |
| `suggestUI` | candidate URL set | Soft presentation suggestion; withdrawing candidates does not imply Stream-111 teardown. | **P+W** |
| `requestUI` | UI/session context | Requests UI presentation; semantically separate from `showUI` and from a Home-button action. | **W** |

Apple's 2023 session explicitly groups **ETA, speed-limit signs, compass and instrument-cluster map zoom**
as vehicle-system integration features:

[WWDC23 — Optimize CarPlay for vehicle systems](https://developer.apple.com/videos/play/wwdc2023/10150/)

![Apple WWDC23 CarPlay visual-integration session artwork](https://devimages-cdn.apple.com/wwdc-services/images/D35E0E85-CCB6-41A1-B227-7995ECD83ED5/8207/8207_wide_900x506_2x.jpg)

---

### 2.2 View Areas, Safe Areas and live geometry

| Function | View / scope | Visible frontend effect | Evidence / visual reference |
| --- | --- | --- | --- |
| `viewAreas[]` | display geometry | A list of predefined rectangles where CarPlay may draw. Each entry uses pixel coordinates: `originXPixels`, `originYPixels`, `widthPixels`, `heightPixels`. Multiple areas represent alternate layouts. | **O+W+D** · [WWDC19](https://developer.apple.com/videos/play/wwdc2019/252/) · [WWDC23](https://developer.apple.com/videos/play/wwdc2023/10150/) |
| nested `safeArea` | inside one View Area | Rectangle inside the View Area where important/interactable UI must remain visible. It is **not** the video crop: imagery may fill the View Area while controls/route guidance remain inside Safe Area. | **O+W+D** · [WWDC19](https://developer.apple.com/videos/play/wwdc2019/252/) |
| `initialViewArea` | display state | Selects the initial View Area by array index. | **W+D** |
| `adjacentViewAreas[]` | display state | Declares which other View Area indices are reachable from the current state. | **W+D** |
| `requestViewArea` | iPhone → accessory | Requests transition to a previously declared View Area index. No new rectangle and no new screen stream are created by the command itself. | **P+W+D** · [WWDC19 dynamic resizing](https://developer.apple.com/videos/play/wwdc2019/252/) |
| `updateViewArea` | accessory → iPhone | Confirms/applies the selected index and carries `animationDurationMillis` plus the new adjacent-index set. **MU1440: high-value probe.** | **W+D** · [WWDC19](https://developer.apple.com/videos/play/wwdc2019/252/) |
| `viewAreaTransitionControl` | per-area modern metadata | Marks participation in controlled/animated resizing. Some current SDK emission paths gate this metadata to type 110, so its exact type-111 applicability must be vehicle-tested. | **P/W** |
| `viewAreaStatusBarEdge` | per-area modern metadata | Tells CarPlay which edge should own the status-bar relationship for that layout. | **P/W** |
| `drawUIOutsideSafeArea` | per-area modern metadata | Controls whether non-critical UI may draw outside the Safe Area. | **P/W** |
| `updateDisplayPanels` | modern display topology | Much broader live reconfiguration of panel geometry, dimensions, UUIDs, streams, initial URL/ViewArea, appearance and scaling. Keep separate from a simple ViewArea switch. | **P+W** · [WWDC24 architecture](https://developer.apple.com/videos/play/wwdc2024/10111/) |

Apple's WWDC19 example is almost exactly the scenario relevant to a configurable Virtual Cockpit:
the **View Area extends between/behind virtual gauges**, while a smaller Safe Area keeps important
content visible. Apple then demonstrates **two View Areas for the same instrument cluster** and a timed
transition as the native tachometers move.

<p>
  <img src="https://pics.computerbase.de/8/8/1/0/6/7-1080.eabb9d44.jpg" alt="Apple WWDC19 instrument-cluster View Area and Safe Area example, mirrored by ComputerBase" width="32%">
  <img src="https://pics.computerbase.de/8/8/1/0/6/10-1080.f2c5681b.jpg" alt="Apple WWDC19 alternate View Areas / dynamic screen sizing example, mirrored by ComputerBase" width="32%">
  <img src="https://pics.computerbase.de/8/8/1/0/6/3-1080.11f8968f.jpg" alt="Apple WWDC19 irregular-display View Area and Safe Area example, mirrored by ComputerBase" width="32%">
</p>

*WWDC19 Apple presentation material, externally mirrored by ComputerBase for still-image convenience.
Primary source: [Apple WWDC19 — Advances in CarPlay Systems](https://developer.apple.com/videos/play/wwdc2019/252/).*

> **Important legacy caveat:** Apple publicly demonstrates dynamic resizing on an instrument cluster,
> but newer SDK reconstruction shows that several auxiliary ViewArea metadata flags are emitted only on
> certain screen types. For legacy type-111 MHI2, **multiple selectable View Areas are therefore a test
> target, not yet a guaranteed capability**.

---

### 2.3 Next-generation hosted / dynamic cluster content

| Function | View / scope | Visible frontend effect | Evidence / visual reference |
| --- | --- | --- | --- |
| `nextGenHostedContent:` | private hosted/gauge-cluster scene | Entry point for Apple's newer hosted-content family. The classic URL validator still separately recognizes `maps:/car/instrumentcluster...`, so this is not automatically a legacy `showUI` target. | **P** · context: [WWDC24 design system](https://developer.apple.com/videos/play/wwdc2024/10112/) |
| `mapsPresentation=map` | hosted Maps | Map-centric hosted content; resolves to item type 1. | **P** |
| `mapsPresentation=instructionCard` | hosted Maps | Hosted maneuver/guidance-card content; item type 2. | **P** |
| `mapsPresentation=anyContent` | hosted Maps | Generic hosted navigation content; item type 3. | **P** |
| `altScreenPresentation=dcaCarousel` | hosted cluster carousel | Real carousel presentation with active-item/rotation machinery and DCA-specific Maps sizing. Exact expansion of “DCA” remains unresolved. | **P** · visual context: [WWDC24 dynamic content](https://developer.apple.com/videos/play/wwdc2024/10112/?time=878) |
| `altScreenPresentation=mapsMediaCarousel` | hosted Maps + Media | **Joint Maps/Media cluster mode.** Maps reports `isRenderedInMediaCarousel`; Media independently sets `isClusterMapsAndMedia = (type == 2)`. Exact OEM geometry remains asset/layout dependent. | **P, very strong** · [WWDC24 — Maps + Now Playing are shown as dynamic-content choices](https://developer.apple.com/videos/play/wwdc2024/10112/?time=878) · [Now Playing docs](https://developer.apple.com/documentation/NowPlaying) |
| `altScreenPresentation=popover` | hosted cluster | Dedicated transient/floating cluster content surface. Trip/TirePressure and CarPlayAssetUI all have matching popover concepts. | **P + I geometry** · [WWDC24 — dynamic-content area also hosts notifications/pop-ups](https://developer.apple.com/videos/play/wwdc2024/10112/?time=878) |
| `altScreenPresentation=passengerDisplay` | passenger-display scene | Routes content to a separate passenger scene/window rather than merely changing a cluster card. | **P** · [WWDC24 architecture](https://developer.apple.com/videos/play/wwdc2024/10111/) |
| `altScreenPresentation=deck` | hosted content, 26.2+ | Generic deck/card/carousel composition. 26.2 introduces `deck`, `DeckActivity`, carousel direction/model and swipe handling. Exact OEM presentation remains unresolved. | **P existence + I exact UI** |
| `displayLocation` | hosted scene topology | Places hosted content on locations such as Center Console, Passenger Display or Secondary Cluster. | **P** · [WWDC24 architecture](https://developer.apple.com/videos/play/wwdc2024/10111/) |

The WWDC24 **Dynamic content** chapter is the closest public visual analogue to the hosted-content
family found in current iOS binaries: Apple shows a large map paired with compact instrumentation,
steering-wheel cycling through content, **Maps and Now Playing**, vehicle trip/tire-pressure/ADAS
content, and notifications/pop-ups in the same dynamic-content region.

[WWDC24 — Say hello to the next generation of CarPlay design system, Dynamic content @ 14:38](https://developer.apple.com/videos/play/wwdc2024/10112/?time=878)

![Illustrative Apple next-generation CarPlay cluster with map between gauges](https://cdn.mos.cms.futurecdn.net/v2/t%3A0%2Cl%3A631%2Ccw%3A1612%2Cch%3A1612%2Cq%3A80%2Cw%3A1612/dZewdpYMLnLC3gy2gwXNgJ.png)

*Apple promotional next-generation CarPlay imagery, externally mirrored by Tom's Guide. It is useful
for visual orientation only and is **not** proof that this exact layout equals the private
`mapsMediaCarousel` enum.*

---

### 2.4 Appearance, scaling, timing and input

| Function | View / scope | Visible frontend effect | Evidence / visual reference |
| --- | --- | --- | --- |
| `uiAppearanceUpdate` | named display | Changes general CarPlay UI/chrome appearance per display. | **P+W** · [WWDC23](https://developer.apple.com/videos/play/wwdc2023/10150/) |
| `mapAppearanceUpdate` | map display | Changes map appearance independently of general UI appearance. | **O+P+W** · [WWDC23](https://developer.apple.com/videos/play/wwdc2023/10150/) |
| `setNightMode` | global/advisory | Day/night state that can trigger dark appearance; separate from per-display map appearance. | **W** · [WWDC23](https://developer.apple.com/videos/play/wwdc2023/10150/) |
| `mapStyle` | Apple Scene setting | Internal resolved map-style state consumed by CarPlay scenes. | **P** |
| Smart Display Zoom / `displayScaleMode` | whole CarPlay display | Rescales the **entire CarPlay UI** to a different display scale. Not map zoom and not ViewArea switching. | **O+P** · [WWDC25 — Smart Display Zoom](https://developer.apple.com/videos/play/wwdc2025/216/) |
| display `ZoomFactor` / `zoomFactor` | display-scale computation | Numeric input to CarKit's scale/canvas calculation. Later 26.x propagates it deeper into session-host configuration. | **P** |
| `forceKeyFrame` | existing video stream | No deliberate layout change; requests a fresh H.264 keyframe for stale/frozen-video recovery. | **P+W** |
| `maxFPS` | display advertisement | Receiver/display frame-rate ceiling; does not define source AU timing. | **W** |
| `frameRateLimit` | Apple cluster scene | Apple-side render scheduling/limit; exists since at least iOS 17.6.1 and is not a proven classic accessory setter. | **P** |
| `CRSUIClusterPressAction` | Apple hosted Scene Action | Semantic select/button action to hosted Apple cluster apps. Not a proven AirPlay `pressType` command. | **P** |
| Knob / D-Pad HID | display-bound HID | Physical rotation/select/nudge/Home/Back input when the matching HID capabilities are declared. | **W** |
| `enablesViewAreas` | capability gate | Arms ViewArea negotiation/switching on stacks that require the feature gate. | **W+D** |
| `enablesMapAppearance` / `enablesUIAppearance` | capability gates | Arms the corresponding runtime appearance controls. | **W** |
| `enablesFocusTransfer` / `viewAreaSupportsFocusTransfer` | multi-surface focus | Allows focus movement between CarPlay and native surfaces; orthogonal to ViewArea geometry. | **W+D** |
| `changeUIContext` / UI-context URL sets | multi-surface UI | Transfers logical UI context among eligible surfaces/URLs. | **W** |

Apple's iOS 26 **Smart Display Zoom** is a useful visual reminder that display scaling is a completely
different mechanism from semantic map zoom:

[WWDC25 — Turbocharge your app for CarPlay](https://developer.apple.com/videos/play/wwdc2025/216/)

---

## 2a. Non-visual gates that determine whether the rows above work

These do not normally create a visible frontend effect by themselves, but omitting them can make a
valid command or URL appear to be unsupported.

| Gate / advertisement | Role | Practical consequence |
| --- | --- | --- |
| `altScreenURLs` | Declares the cluster URLs supported by the auxiliary display/session. | A classic cluster `showUI` target must be represented in the negotiated URL surface. |
| `approvedClusterURLs` | Accessory/config allow-list for cluster UI URLs. | A syntactically valid Maps cluster URL can still be rejected if it is outside the approved set. |
| `altScreenSuggestUIURLs` | Declares URLs eligible for the softer `suggestUI` mechanism. | Controls the candidate set that iOS may suggest for the cluster; it is not the same as `altScreenURLs`. |
| `initialURL` | Seeds the auxiliary video stream with its first content role. | Common cluster value is `maps:/car/instrumentcluster/map`; this affects initial presentation but is not a runtime command. |
| `showsInstruments` | Marks a display panel as an instrument/cluster role. | Helps iOS classify the surface as cluster content rather than an ordinary display. |
| `supportsAltScreen` / negotiated `altScreen` feature | Enables the auxiliary-screen feature at session level. | Without successful feature negotiation, the type-111 display description alone is insufficient. |
| display `uuid` / HID `displayUUID` consistency | Binds commands and input devices to the correct screen. | `showUI`, map zoom, ViewArea and HID operations can silently target the wrong/nonexistent surface if UUID ownership is inconsistent. |

These gates are one reason an Apple-internal `nextGenHostedContent:` URL cannot be assumed to work
merely because its parser exists.

---

## 3. Why `changeMapZoomLevel` was easy to miss

It sits between the layers previously searched:

```text
classic URL parser
    └─ showETA / showSpeedLimit / showCompass / maneuverLayout

AirPlay command plane
    └─ changeMapZoomLevel { uuid, zoomDirection }

Apple hosted scene plane
    └─ CRSUIClusterZoomAction
```

So a search centered on cluster URLs will not find the wire command, while a search centered on
CarPlayUIServices finds an internal Scene Action with a **different enum**.

This distinction is important enough to pin:

| Zoom mechanism | Scope | Values |
| --- | --- | --- |
| AirPlay `changeMapZoomLevel` | map content on cluster | 0 = zoom in, 1 = zoom out |
| `CRSUIClusterZoomAction` | Apple-internal hosted Scene Action | 1 = zoom in, 2 = zoom out |
| Smart Display Zoom | whole CarPlay UI/display scale | display-scale mode, not directional map zoom |
| display `ZoomFactor` | display-scaling heuristic | numeric scale input |

Apple also documents the user-facing requirement publicly: a vehicle that exposes map zoom controls for
its instrument cluster should implement CarPlay map zoom.

Official source:

- https://developer.apple.com/videos/play/wwdc2023/10150/

---

## 4. `mapsMediaCarousel`: exact current interpretation

The earlier conclusion can now be strengthened.

### Maps side

`CarInstrumentClusterChromeConfiguration`:

- reads `hostedAltScreenPresentationType`;
- returns true from `isRenderedInMediaCarousel` when presentation type is **2**;
- consumes ETA, speed-limit, compass and layout state;
- feeds hybrid instrument-cluster map/navigation controllers.

### Media side

The Media app:

- accepts hosted presentation types 1..3 as **cluster scenes**;
- accepts type 4 as a separate **passenger display scene**;
- when cluster scene settings change, sets:
  `isClusterMapsAndMedia = (hostedAltScreenPresentationType == 2)`;
- logs the state as:
  `Radio cluster maps and media`.

This makes the functional interpretation unusually strong:

> **`mapsMediaCarousel` is an Apple first-party cluster composition in which Maps and Media are both
> participants in the same hosted-cluster presentation.**

What remains unknown is **the exact OEM-visible geometry**: which side/card is larger, whether album art
or metadata is shown in a particular slot, and what cluster chrome surrounds the content. Those details
are driven by CarPlayAssetUI/vehicle assets and layout configuration.

It is therefore not safe to translate this directly into “send
`nextGenHostedContent...?altScreenPresentation=mapsMediaCarousel` over classic MHI2 `showUI`”.

---

## 5. Hosted presentation family

The 26.1 parser maps:

```text
dcaCarousel       -> 1
mapsMediaCarousel -> 2
popover           -> 3
passengerDisplay  -> 4
```

All 1..3 are treated by Media as cluster-scene presentations; type 4 is passenger-display-specific.

### DCA carousel

Concrete evidence:

- CarPlayAssetUI: “Setting new active DCA carousel item”;
- carousel model/direction;
- Trip: `CAFUIAppPresentationMode.clusterDCA`;
- Maps: dedicated DCA-carousel guidance-card sizing.

Result:

> **Proven carousel presentation; exact meaning of the “DCA” acronym is intentionally left unresolved.**

### Popover

Concrete evidence:

- Trip: `CAFUIAppPresentationMode.clusterPopover`;
- TirePressure selects a popover UI configuration for hosted type 3;
- CarPlayAssetUI contains `PopoverModel`, `PopoverView`, `PopoverContainer` and transition handling.

Result:

> **Proven cluster popover surface.** It is reasonable to describe the visible behavior as
> transient/floating content rather than a full persistent map pane, but exact placement is vehicle-asset
> dependent.

### Passenger display

Media contains separate passenger-scene and passenger-window state and logs a new passenger display
scene when hosted presentation type is 4.

Result:

> **Proven separate passenger display destination**, not a special MHI2 VC map mode.

### Deck — post-26.1

The 26.1 -> 26.2 public diff adds:

```text
nextGenHostedContent:/?altScreenPresentation=deck
deck
DeckActivity
deckDataByID
Carousel
CarouselModel.Direction
handleCarouselSwipeLeftGesture
handleCarouselSwipeRightGesture
```

along with widget-host migration and ViewArea-state strings.

Result:

> High-confidence **generic hosted deck/card/carousel composition**, broader than Maps. Exact visual
> semantics and numeric enum are not pinned by the 26.1 parser and should remain marked inferred until a
> complete 26.2+ call path is reconstructed.

---

## 6. Smart Display Zoom: a separate control family we had not indexed before

This is a significant second-pass addition.

The iOS 26.1 CarPlay Settings app contains:

```text
SMART_DISPLAY_ZOOM_CELL_TITLE
CPSettingsSmartDisplayZoomToggle
```

and shows the control only when a connected screen reports that Smart Zoom is allowed.

CarKit `CRDisplayScaleInfo` exposes:

```text
allowsSmartZoom
canvasPixelSizeForDisplayScaleMode:
displayScaleModesForCanvasPixelSize:
defaultDisplayMode
optimizedPointScale
originalPointScale
preferredPointScale
zoomFactor
```

It reads `ZoomFactor` from AirPlay display configuration and computes alternative canvas sizes.

Apple publicly describes the visible iOS 26 behavior as a CarPlay Settings option that adjusts display
scale; apps are automatically resized to the new scale.

This is therefore **not**:

- cluster map zoom;
- a MapKit camera control;
- the same thing as ViewArea cropping.

A 26.3 -> 26.4 carkitd diff also adds explicit propagation of:

```text
displayScaleMode
zoomFactor
```

into `CARSessionRequestHost`, showing that the display-scaling path continued to evolve after 26.1.

Official source:

- https://developer.apple.com/videos/play/wwdc2025/216/

---

## 7. iOS 26.x evolution after the 26.1 full-tree baseline

The second pass did **not** surface a new classic Stream-111 cluster command after
`changeMapZoomLevel` / ViewArea / appearance / UI-control families already known.

It did surface continued evolution in the hosted/display layer:

| Range | Relevant change |
| --- | --- |
| 26.1 -> 26.2 | `deck` hosted presentation; deck/carousel asset model; carousel swipe handlers; widget-host migration; new ViewArea state strings. |
| 26.2 / 26.3 | CarPlayAssetUI deck/carousel/slot composition continues to evolve. |
| 26.3 -> 26.4 | DashBoard ViewArea update paths change; CarKit/carkitd deepen `displayScaleMode` + `zoomFactor` session handling. |
| 26.5 -> 26.6 betas | Appearance-resolution and AVRouting/ViewArea internals change; no new classic cluster command name was found in the reviewed diffs. |
| 26.7 -> 26.7.1 | No CarPlay-related dylib delta in public 23H24 -> 23H30 diff; CoreGraphics is the only updated shared-cache dylib. |

Do not interpret the table as proof that every private implementation detail stayed byte-identical
across all intermediate builds. It describes the **publicly visible diff evidence** relevant to this
research.

---

## 8. Practical MU1440 test order

The shortest path from research to visible vehicle evidence remains:

```text
1. changeMapZoomLevel
2. classic URL / itemType A/B:
      base
      map
      instructioncard
3. showETA / showSpeedLimit / showCompass
4. maneuverLayout top / left / right
5. two declared ViewAreas
6. requestViewArea / updateViewArea
7. appearance controls
8. maxFPS A/B while measuring real AU cadence
9. updateDisplayPanels as a separate experiment
10. nextGenHostedContent only after a real hosted capability/scene gate is identified
```

Do **not** combine in one experiment:

- map zoom and Smart Display Zoom;
- `maxFPS` and Apple scene `frameRateLimit`;
- ViewArea switching and `updateDisplayPanels`;
- classic `maps:/car/instrumentcluster...` URLs and private `nextGenHostedContent:` URLs.

---

## 9. Source anchors

### Apple public

- WWDC19 — Advances in CarPlay Systems:
  https://developer.apple.com/videos/play/wwdc2019/252/
- WWDC23 — Optimize CarPlay for vehicle systems:
  https://developer.apple.com/videos/play/wwdc2023/10150/
- WWDC25 — Turbocharge your app for CarPlay:
  https://developer.apple.com/videos/play/wwdc2025/216/

### Full public iOS restore trees

- `SuperChaoM/iPhone15-3_17.6.1_21G101_Restore@95df6b804bee0e01538eb2ddad0413609938d063`
- `EthanArbuckle/iPhone17-1_18.2_22C152_Restore@e26ed4563f78871c59d2d96856756a65d62517e5`
- `EthanArbuckle/iPhone18-3_26.1_23B85_Restore@90aa0cfe59d9682b4265e1354c8b19ec3c7823ab`

High-value 26.1 files:

```text
DashBoard/DBInstrumentClusterURLHandler.mm
CarPlayUIServices/CRSUIInstrumentClusterSceneSettings.mm
CarPlayUIServices/CRSUIMutableInstrumentClusterSceneSettings.mm
CarPlayUIServices/CRSUIClusterZoomAction.mm
CarPlayUIServices/CRSUIClusterZoomBSActionsHandler.mm
CarPlayUIServices/CRSUIClusterPressAction.mm
CarPlayTemplateUIHost/CARTemplateUIHostInstrumentClusterViewController.mm
Maps/CarInstrumentClusterChromeConfiguration.mm
Maps/CarHybridInstrumentClusterNavigationModeController.mm
Maps/UIWindow.mm
Media/Media_07.mm
CarKit/CRDisplayScaleInfo.mm
CarPlaySettings/CARDisplayPanel.mm
```

### Public diff evidence

- `blacktop/ipsw-diffs`
- especially 18.2 -> 18.3 hosted-content evolution;
- 26.1 -> 26.2 `deck` / carousel additions;
- 26.3 -> 26.4 display-scale / ViewArea changes;
- 26.7 -> 26.7.1 current no-CarPlay-dylib delta.

### Receiver / wire cross-reference

- `45clouds/WirelessCarPlay@51145ef55f8dd9f1cbadd58353cacb5e0ca215e9`
- `lvalen91/ocbm` — command and ViewArea ground-truth work
- `omonob/MHI2-Carplay-Maps@49882eb56db83a7b42f185adb426161f35a08295`
- `arctus/mib2-carplay-rgi-altscreen@404ccc23450e385a0183d37fc93677a0c9a5637d`
- `luka-dev/mib2q-carplay-rgi`

---

## 10. Research rule

For a new function, keep these questions separate:

1. Does a string/class/key exist?
2. Does Apple write/read it in a real call path?
3. Does it select a real frontend component?
4. Is there an AirPlay wire command?
5. Is the wire command accessory-reachable?
6. Is a capability/URL allowlist required?
7. Can a legacy type-111 receiver advertise that capability?
8. Does the MU1440 vehicle visibly honor it?

This separation is specifically what prevents internal Scene Actions, next-generation hosted URLs and
classic AirPlay commands from being merged into one misleading “CarPlay parameter” list.


---

## 11. Reference layout

Public Apple references and visual examples are now linked **inline next to the function they support**
in sections 2.1–2.4. This keeps the evidence close to the corresponding control and avoids a second,
duplicated link catalogue at the end of the document.

Primary public talks used throughout the matrix:

- [WWDC19 — Advances in CarPlay Systems](https://developer.apple.com/videos/play/wwdc2019/252/)
- [WWDC23 — Optimize CarPlay for vehicle systems](https://developer.apple.com/videos/play/wwdc2023/10150/)
- [WWDC24 — Say hello to the next generation of CarPlay design system](https://developer.apple.com/videos/play/wwdc2024/10112/)
- [WWDC24 — Meet the next generation of CarPlay architecture](https://developer.apple.com/videos/play/wwdc2024/10111/)
- [WWDC25 — Turbocharge your app for CarPlay](https://developer.apple.com/videos/play/wwdc2025/216/)

Still images embedded above are external mirrors or public Apple CDN assets and are included only for
visual orientation; the linked Apple talks remain the primary public evidence.
