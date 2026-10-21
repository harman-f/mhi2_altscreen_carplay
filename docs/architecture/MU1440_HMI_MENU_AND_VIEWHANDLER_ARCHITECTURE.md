# MU1440 HMI menu and ViewHandler architecture

> **October 2026 update:** This document preserves the original static architecture and early WidgetFactory proposal. Current development additionally includes a project-owned HOME tile, OEM-style Settings rows, a separate native MIBR/3 settings/action controller and a source-only scrollbar extension. The latest outcome and individual build/vehicle acceptance gates are in [module boundaries and SEAT/VW portability](MODULE_BOUNDARIES_AND_PORTABILITY.md) and [integration status](../status/INTEGRATION_STATUS_2026-10-21.md). The exact MU1440 widget IDs, skins, CIO routes and classloader details are **not portable binaries**; another firmware/brand requires its own read-only original HMI audit.


**Status:** static reverse-engineering / implementation design  
**Reference target:** `MHI2_ER_SKG13_P4526_MU1440`  
**Scope:** stock MIB2 High main-menu composition, application-local settings navigation, ViewHandler loading, and the proposed AltScreen settings integration path.

> [!NOTE]
> This document describes the HMI architecture recovered from the MU1440 reference target and cross-checked against readable public MIB2 framework sources. It is not an end-user installation guide and does not imply cross-firmware compatibility.
>
> For the newest cross-topic status — including the current WidgetFactory proof level, settings registry, media/keyframe design and steering-wheel integration — see the [current research preview](../research/CURRENT_RESEARCH_PREVIEW_2026-10-05.md).

## 1. Executive summary

The MU1440 HMI does **not** use one central static menu tree.

There are two distinct navigation layers:

1. **Top-level main menu**
   - dynamically assembled from registered CIO intents;
   - filtered by `MenuAction` + `GridMenuAction`;
   - ordered using persisted CIO IDs;
   - published through the GridMenu ASL list;
   - rendered by `SimpleGridMenu` / `Sgm`;
   - dispatched through `CioDispatcher`.

2. **Application-local menus and settings**
   - owned by generated application state machines;
   - entered through actions / CIO dispatch / service calls;
   - open symbolic view names through `showView("<ViewName>")`;
   - resolve those names to generated ViewHandler classes;
   - load the corresponding JXE container from the active skin.

For the AltScreen project this is an important simplification:

> A stock-looking CarPlay / Virtual Cockpit settings page does not require rebuilding the top-level main menu.

The lowest-coupling design is to enter a dedicated sibling view from an existing settings owner, preferably the stock FPK / Virtual Cockpit area.

---

## 2. Exact target authority

Reference firmware:

`MHI2_ER_SKG13_P4526_MU1440`

Exact retained LSD identity:

- path on target: `/ifs/lsd.jxe`
- size: `55,840,933` bytes
- SHA-256:  
  `a55d9cfb69c5756f8202b7f7aa4079d4d5b637ae4c2fd0fe723f1d6816cbeea8`

The relevant conclusions below were derived from the exact target LSD and exact target ViewHandler containers.

Readable public MIB2 framework sources were additionally used to cross-check the implementation mechanics of classes such as:

- `MainMenuTarget`
- `GridMenuAppInfoPlatesListTransformer`
- `ASLGridMenuDeviceImpl`
- `SimpleGridMenuActivity`
- CIO visualization services
- `JxeSkinClassLoader`
- Microdoc J9/XIP loader classes

Target-specific claims remain gated to MU1440 unless explicitly marked as generic/public-framework evidence.

---

# 3. Main-menu architecture

The stock main-menu flow is:

```text
feature/application registers a CIO intent
        |
        | intent class = "MenuAction"
        | usage        = "GridMenuAction"
        v
CioDictionary
        |
        | getCioIntents("MenuAction", "GridMenuAction")
        v
MainMenuTarget
        |
        | live CioIntent objects
        | persisted CIO-ID ordering
        v
GridMenu ASL list 4810002
"AppInfoPlatesList"
        |
        v
SimpleGridMenu
context "Menu"
view "Sgm"
        |
        | selected list index
        v
MainMenuTarget.dispatchGridMenuEntry(index)
        |
        v
CioDispatcher.dispatch(cioIntent)
        |
        v
owning application / state machine / view
```

The main menu is therefore not a fixed array such as:

```text
0 = Radio
1 = Media
2 = Navigation
3 = Car
...
```

The grid is a runtime projection of registered intents.

---

# 4. `MainMenuTarget` responsibilities

The main-menu runtime owner maintains two important structures:

```text
CIO intent ID -> live CioIntent object
ordered list of live CioIntent objects
```

The first is required because persisted order is stored by stable CIO ID.

The second is the actual runtime order used for rendering and index-based dispatch.

Conceptually:

```text
CioDictionary
     |
     +----> ID -> CioIntent map
     |
     +----> orderedIntents
                  ^
                  |
          persisted CIO-ID order
                  |
                  v
            ASL GridMenu
```

---

# 5. Startup and lifecycle

The main-menu target initializes approximately as follows:

```text
construct MainMenuTarget
  -> register GenericEvents target
  -> retrieve ASL list
  -> register CIO listeners
  -> register profile-change listener
  -> register factory-reset participant
  -> load persistence
  -> query current GridMenuAction CIOs
  -> apply persisted order
  -> publish menu
```

This has several consequences:

- menu content depends on the live CIO registry;
- order depends on the active user/profile persistence;
- the menu can change when CIOs register or unregister;
- profile changes reconstruct the menu;
- factory reset restores default ordering.

---

# 6. Main-menu CIO filter

The main grid explicitly asks for:

```text
CIO intent class: "MenuAction"
usage:            "GridMenuAction"
```

Equivalent framework operation:

`CioDictionary.getCioIntents("MenuAction", "GridMenuAction")`

Other menu-action usages exist for other UI surfaces, so registering a generic `MenuAction` is not sufficient.

A top-level grid entry must satisfy the `GridMenuAction` usage contract.

---

# 7. Dynamic CIO registration

The target listens for CIO registration changes.

When a new matching CIO appears:

```text
cioRegistered(...)
  -> usage == GridMenuAction
  -> addGridMenuEntryIntent(...)
  -> add ID -> intent mapping
  -> append to runtime order
  -> publish menu
```

When it disappears:

```text
cioUnregistered(...)
  -> usage == GridMenuAction
  -> remove from map
  -> remove from runtime order
  -> publish menu
```

This is useful for capability-gated applications because the main-menu framework itself does not require a static rebuild when an application appears or disappears.

---

# 8. Persisted ordering

The user/profile-specific menu order is stored as an ordered list of **CIO IDs**.

On initialization the effective order is reconstructed as:

```text
1. load persisted CIO IDs
2. discard IDs that are not currently registered
3. add surviving CIOs in persisted order
4. append currently registered CIOs not present in persistence
```

Pseudocode:

```text
known = persistedIds filtered by runtimeMap.contains(id)

ordered = []
for id in known:
    ordered += runtimeMap[id]

for intent in currentGridMenuIntents:
    if intent.id not in known:
        ordered += intent
```

This explains several stock behaviors:

- removed features do not leave unusable menu entries;
- newly introduced features can appear without an old persisted slot;
- stable CIO IDs preserve menu identity across normal persistence cycles.

### Practical implication

A future project-owned top-level CIO should use a stable ID.

Changing its identity between builds will make the persistence layer treat it as a new menu item.

---

# 9. Reordering

The main-menu target receives a move request containing:

```text
fromIndex
toIndex
```

The runtime behavior is equivalent to:

```text
intent = orderedIntents.remove(fromIndex)
orderedIntents.add(toIndex, intent)
publish menu
persist CIO-ID order
```

The persistence format therefore represents **order**, not grid geometry.

It does not store:

- icon positions;
- pixel coordinates;
- labels;
- destination ViewHandlers.

---

# 10. Profile and reset behavior

On profile change the menu is reconstructed from:

- the live CIO registry;
- that profile's persisted CIO-ID order.

On system/personalization factory reset:

```text
grid-menu persistence -> resetToDefaults()
menu -> reinitialize
```

A custom top-level feature should therefore participate in the existing CIO model rather than introduce a second independent main-menu ordering mechanism.

---

# 11. GridMenu ASL bridge

The generated GridMenu device exposes the logical list:

`4810002`

Name:

`AppInfoPlatesList`

The runtime updates that list with the current ordered `CioIntent` objects.

However, the list transformer reduces each row to one value:

```text
CioIntent -> getCioIntentId()
```

So the actual HMI-facing row identity is effectively:

```text
row N = CIO intent ID
```

The list itself is not carrying the full final presentation.

---

# 12. Presentation is separate from menu order

The CIO system separates three responsibilities:

```text
DISCOVERY
  CIO class / usage / stable ID

PRESENTATION
  CIO visualization mapping

BEHAVIOR
  CioDispatcher target/action
```

Generated applications provide CIO visualization services that resolve visualization IDs to resources such as:

- icon/image vectors;
- normal/focused color vectors;
- localized text;
- optional dynamic visual state.

Therefore `MainMenuTarget` does not need to know the Media, Navigation, Car or App-Connect label/icon details.

This is important for any future top-level AltScreen tile: registering the CIO alone would not be enough. It would also need a visualization contract and a valid dispatch target.

---

# 13. Selection and dispatch

Grid activation is index-based.

The main-menu runtime receives the selected visible-list index and performs:

```text
validate index
  -> cioIntent = orderedIntents[index]
  -> CioDispatcher.dispatch(cioIntent)
```

Application-specific navigation starts only **after** this boundary.

The main-menu owner therefore acts as a generic router.

---

# 14. `SimpleGridMenu` / `Sgm`

The generated `SimpleGridMenuActivity` opens the stock grid using:

`showView("Sgm", ...)`

and closes it using:

`hideView("Sgm")`

For the main menu, the recovered presentation context is:

```text
context = "Menu"
view    = "Sgm"
```

This gives a useful architectural split:

```text
MainMenuTarget
  = content, ordering, persistence, dispatch

Sgm ViewHandler / skin
  = concrete grid presentation and widget geometry
```

Exact pixel geometry, focus animations, paging layout and cell dimensions belong to the ViewHandler/skin layer, not the menu-structure layer.

---

# 15. Application-local settings are a different system

Once a CIO dispatch enters an application, navigation is normally controlled by that application's generated state machine.

Typical flow:

```text
CIO dispatch / internal action
        |
        v
generated application state machine
        |
        +--> state transition
        +--> datapool updates
        +--> observer/service calls
        |
        v
showView("<ViewName>", ...)
        |
        v
LocalViewHandlerFactory
        |
        v
generated ViewHandler class
        |
        v
widgets / lists / controls / events
```

This means there is no single global "System -> ... -> ..." configuration file containing every submenu in the HMI.

Adding an item inside a settings application is a different operation from adding a top-level CIO.

---

# 16. Exact FPK / Virtual Cockpit route

The recovered stock route is:

```text
ShowFPKSetupView
  -> CarApp / ShowActualViewsService
  -> CarSetupFPKSettingsView
  -> getToFullScreen = 11
  -> CarActivity guard
  -> Car state 61
  -> showView("Cmc", ...)
```

Therefore:

> `Cmc` is the concrete stock FPK / Virtual Cockpit settings view on the MU1440 reference target.

This is currently the strongest semantic integration point for an AltScreen settings UI.

---

# 17. FPK backend pattern

The exact MU1440 LSD exposes a dedicated `Car.FPK` model with dynamic lists and services for concepts including:

- display content selection;
- available modes;
- content availability;
- presets;
- function existence;
- function availability;
- unavailable reason.

Observed list IDs include:

- `10863`
- `10866`
- `10867`
- `10868`
- `10883`
- `10884`
- `10885`
- `10886`

Observed service routing includes:

- `1192034368` — content selection;
- `1158479936` — select preset;
- `1175257152` — save preset.

Even where the numeric binding is not yet fully mapped per control, the architectural value is clear:

`Cmc` is an OEM example of a configuration UI with:

```text
available choices
+ current selection
+ capability gating
+ availability reason
+ backend action
```

That pattern maps well to AltScreen settings.

---

# 18. Smartphone Integration: setup vs active CarPlay canvas

The generated SmartphoneIntegration state machine clearly separates configuration from active projection.

## Setup

```text
SubCSmiSetupIncludeState
  -> showView("Ssm_5458", ..., 122)
```

The decoded `Ssm_5458.jxe` contains normal setup UI patterns including device selection, connection type and CarPlay-related rows.

## Active CarPlay bridge

Separately:

```text
SubICarplayBridge
  -> showView("Cm_0409", ..., 135)
```

The decoded `Cm_0409.jxe` contains the active CarPlay canvas/black-screen/gesture boundary.

This stock separation is useful design guidance:

> AltScreen configuration should remain separate from the active CarPlay canvas.

Putting settings directly into `Cm_0409` would couple configuration to projection lifecycle and canvas handling.

---

# 19. View-name resolution

For ordinary application-local views, a symbolic view name is resolved to a generated class name.

Example:

```text
"Cmc"
  -> generated.de.vw.mib.car.view.internal.Cmc
```

A proposed new sibling would naturally map as:

```text
"MibrAltScreenSettings"
  -> generated.de.vw.mib.car.view.internal.MibrAltScreenSettings
```

The inspected factory logic contains special handling for known shared views/popups, but ordinary local views are constructed from the owning application's package prefix plus the supplied view name.

No ordinary-view name whitelist was found in this path.

This makes a new sibling ViewHandler structurally plausible.

---

# 20. Production ViewHandler loader

The MU1440 startup configuration selects ZIP-based ViewHandlers:

```text
-Dviewhandler.format=zip
```

The active skin resolves beneath the configured resource directory and `JxeSkinClassLoader` loads the skin's:

`viewhandler.zip`

Per-view container naming is derived from the simple class name:

```text
generated.de.vw.mib.car.view.internal.Cmc
    -> Cmc.jxe

generated.de.vw.mib.smartphoneintegration.view.internal.Ssm_5458
    -> Ssm_5458.jxe
```

The loader then resolves and instantiates the ViewHandler class from the target J9/XIP environment.

---

# 21. Exact MU1440 ViewHandler evidence

The exact target `skin1/viewhandler.zip` contains 1,232 flat JXE members.

Relevant extracted members:

| View | Generated class | Size | SHA-256 |
| --- | --- | ---: | --- |
| `Cmc.jxe` | `generated.de.vw.mib.car.view.internal.Cmc` | 258,698 B | `6ca037c2afbd716129125a7e37c16fc133a8237df125c6d3d107997a99b467c5` |
| `Ssm_5458.jxe` | `generated.de.vw.mib.smartphoneintegration.view.internal.Ssm_5458` | 47,895 B | `285d12699338d463c1cfe93db6bccfdf4832c51cc1d7b51e1cecafa6717df5f2` |
| `Cm_0409.jxe` | `generated.de.vw.mib.smartphoneintegration.view.internal.Cm_0409` | 11,814 B | `87b31fe09e95f257ede721ff38ac21fde888db733f0aeccb65d69ea586c2c166` |

This confirms the production view-name / JXE-container relationship on the exact target.

---

# 22. Multi-archive XIP loader finding

A readable public Microdoc J9/XIP implementation used by MIB2 exposes an `XIPClassLoader` that accepts an ordered array of archive URLs.

Its JXE lookup iterates those archives in order and stops at the first matching container.

Conceptually:

```text
XIPClassLoader(
    custom-viewhandlers.zip,
    stock viewhandler.zip
)

loadJXE("MibrAltScreenSettings.jxe")
  -> custom archive first
  -> stock archive fallback
```

That creates an attractive additive design:

```text
custom overlay archive
  -> only project-owned ViewHandlers

stock viewhandler.zip
  -> remains untouched
  -> supplies every OEM ViewHandler
```

### Confidence

Public/readable MIB2 implementation:

`MULTI_ARCHIVE_XIP_SEARCH = PROVEN`

Exact MU1440 binary equivalence:

`OPEN / MUST BE VERIFIED`

Before this is used as a target compatibility claim, the exact MU1440 implementations should be compared for:

- `com.microdoc.j9.xip.XIPClassLoader`
- `com.microdoc.j9.xip.FileSPI`
- `com.microdoc.j9.xip.Archive`
- `com.microdoc.j9.xip.JxeClassLoader`

---

# 23. Top-level tile vs sibling settings view

A new **top-level** main-menu feature requires at least:

```text
GridMenuAction CIO
+ stable CIO ID
+ visualization mapping
+ dispatcher target
+ application/state-machine entry
+ destination view
+ resources
+ profile/reset lifecycle
```

A new **application-local sibling settings view** requires a smaller surface:

```text
existing settings owner
+ one entry/action
+ one state/view transition
+ ViewHandler
+ widget/event/model bindings
+ normal Back lifecycle
```

It does not inherently require:

- changing `MainMenuTarget`;
- introducing a new GridMenu persistence format;
- adding a new top-level visualization service;
- creating a complete standalone HMI application.

For the first AltScreen settings implementation, the sibling-view approach is therefore preferred.

---

# 24. Proposed AltScreen HMI integration

Preferred semantic path:

```text
Vehicle / Virtual Cockpit
        |
        v
stock FPK settings
        |
        v
CarPlay AltScreen
        |
        v
MibrAltScreenSettings
```

Conceptual class:

`generated.de.vw.mib.car.view.internal.MibrAltScreenSettings`

Conceptual container:

`MibrAltScreenSettings.jxe`

The existing `Cmc` view should initially be treated as:

- the semantic parent;
- a donor/reference for OEM FPK UI patterns;
- an entry-point candidate.

It should not be replaced wholesale for the first prototype.

---

# 25. Why not replace `Cmc`

The recovered `Cmc` ViewHandler is large and highly integrated:

- 188 fields;
- 298 methods;
- many unrelated Car/FPK surfaces and bindings.

Replacing it would mean preserving a large generated behavior surface merely to add one feature.

A dedicated sibling dramatically reduces regression and rollback risk.

---

# 26. Why `Ssm_5458` remains useful

`Ssm_5458` is a useful fallback/donor because it already demonstrates stock settings patterns such as:

- list rows;
- dropdowns;
- clone rows;
- setup actions;
- datapool/list listener lifecycle.

If a fully additive new ViewHandler remains blocked by JXE-generation constraints, a controlled SmartphoneIntegration extension may be a practical fallback.

Semantically, however, FPK / Virtual Cockpit remains the cleaner owner for cluster-display settings.

---

# 27. Proposed user-facing settings model

The first page can map directly to controls already present in the public AltScreen runtime:

```text
CarPlay AltScreen

Display
  Surface
  Maneuver position
  ETA
  Speed limit
  Compass

Stream
  Auto-Direct
  Frame rate

Layout
  ViewArea / SafeArea preset
  [capability-gated / experimental]

Controls
  Zoom in
  Zoom out
  Steering-wheel mapping
  [later]

Advanced / Diagnostics
  Keyframe recovery policy
  Runtime/capability status
```

The HMI should expose semantic settings rather than raw marker-file or shell terminology.

---

# 28. HMI/runtime ownership boundary

The ViewHandler should not directly own native stream lifecycle or modify persistent runtime files itself.

Preferred architecture:

```text
MibrAltScreenSettings
        |
        | validated user intent
        v
small HMI adapter
        |
        v
AltScreen runtime broker
        |
        +--> persistence
        +--> capability checks
        +--> source/showUI sequencing
        +--> keyframe recovery
        +--> reconnect-required state
        |
        v
GEN2 / direct runtime
```

Useful model states are:

| State | Meaning |
| --- | --- |
| Requested | user's persistent preference |
| Effective | currently applied runtime value |
| Capability | whether current target/session supports the feature |
| Diagnostic | reason requested and effective state differ |

This preserves the existing runtime as the single owner of stream-control behavior.

---

# 29. Current status by layer

| Area | Status |
| --- | --- |
| Main-menu CIO enumeration | **PROVEN on MU1440** |
| `MenuAction + GridMenuAction` filter | **PROVEN on MU1440** |
| Persisted CIO-ID ordering | **PROVEN / framework cross-check** |
| Dynamic CIO registration/removal | **PROVEN / framework cross-check** |
| GridMenu list `4810002` | **PROVEN** |
| Grid row -> CIO ID transformation | **PROVEN / framework cross-check** |
| `Sgm` main-grid view | **PROVEN** |
| CIO visualization separation | **PROVEN / framework cross-check** |
| Selection -> `CioDispatcher` | **PROVEN** |
| FPK entry -> `Cmc` | **PROVEN on MU1440** |
| Smartphone setup -> `Ssm_5458` | **PROVEN on MU1440** |
| Active CarPlay canvas -> `Cm_0409` | **PROVEN on MU1440** |
| View name -> generated local class | **PROVEN / framework cross-check** |
| ViewHandler JXE naming | **PROVEN on MU1440** |
| Active-skin `viewhandler.zip` | **PROVEN on MU1440** |
| Multi-archive XIP lookup | **PROVEN in readable public MIB2 implementation** |
| Same multi-archive behavior on exact MU1440 | **OPEN: verify exact classes** |
| Building a new target-compatible JXE | **OPEN** |
| New sibling ViewHandler vehicle load | **OPEN** |

---

# 30. Next implementation gate

No further main-menu archaeology is required before the next meaningful prototype.

The remaining gate is:

> prove one additive, target-compatible ViewHandler while keeping all OEM ViewHandlers byte-identical.

Recommended sequence:

1. compare the exact MU1440 Microdoc XIP classes against the readable public implementation;
2. determine the valid JXE/XIP build path for the target J9 runtime;
3. build one minimal class:
   `generated.de.vw.mib.car.view.internal.MibrAltScreenSettings`;
4. use an in-memory/dummy backend first;
5. prove:
   - entry;
   - render;
   - input;
   - Back;
   - unload/re-entry;
6. only then bind real AltScreen controls.

The first prototype should not replace:

- `Cmc.jxe`;
- `Ssm_5458.jxe`;
- `Cm_0409.jxe`;
- the stock `viewhandler.zip`.

---

# 31. Architecture summary

```text
                         TOP-LEVEL MAIN MENU
                         ===================

Feature/App
  |
  | registers CioIntent
  | class=MenuAction
  | usage=GridMenuAction
  v
CioDictionary
  |
  v
MainMenuTarget
  |
  +--> live ID->intent map
  |
  +--> ordered intents
  |      ^
  |      |
  |   persisted CIO-ID order
  |
  v
ASL GridMenu list 4810002
AppInfoPlatesList
  |
  | row identity = CIO ID
  v
SimpleGridMenu / Sgm
  |
  | user selects index
  v
MainMenuTarget
  |
  v
CioDispatcher
  |
  v
Feature/App target


                       APPLICATION-LOCAL MENU
                       ======================

Feature/App target
  |
  v
generated application state machine
  |
  v
showView("ViewName")
  |
  v
LocalViewHandlerFactory
  |
  v
generated.<app>.view.internal.ViewName
  |
  v
JxeSkinClassLoader
  |
  v
ViewName.jxe
  |
  v
ViewHandler + widgets + lists + events
  |
  v
application/backend services
```

For AltScreen, the current preferred direction is:

```text
stock FPK / Virtual Cockpit settings
        |
        v
dedicated project-owned sibling
MibrAltScreenSettings
        |
        v
small HMI adapter
        |
        v
existing AltScreen runtime contract
```

The architecture question is now substantially resolved.

The remaining problem is not how the MU1440 menu is structured, but how to materialize and load one new target-compatible ViewHandler as cleanly and reversibly as possible.


---

# 32. Additive-loader follow-up

The menu architecture itself is no longer the primary unknown. The remaining question is how to provide one new project-owned ViewHandler with the smallest possible firmware-specific surface.

## 32.1 Bootclasspath-only ViewHandler hypothesis

Readable MIB2 J9/XIP framework code suggests two relevant behaviors:

1. a missing per-view JXE load can be caught before the loader continues to qualified-class resolution;
2. the XIP class loader attempts ordinary parent/super class loading before falling back to classes from loaded JXE containers.

That creates a potentially simpler first prototype:

```text
showView("MibrAltScreenSettings")
        |
        v
generated.de.vw.mib.car.view.internal.MibrAltScreenSettings
        |
        +--> MibrAltScreenSettings.jxe lookup fails
        |    [potentially non-fatal]
        |
        v
normal class resolution
        |
        v
project class supplied through bootclasspath
```

If the exact MU1440 implementation behaves the same way, a new JXE may not be required for the first sibling-view PoC.

Current classification:

`BOOTCLASSPATH_ONLY_NEW_VIEWHANDLER = STRONG HYPOTHESIS / NOT VEHICLE-PROVEN`

This must be verified against the exact MU1440 `JxeSkinClassLoader` / Microdoc J9 classes before deployment.

## 32.2 Thin compatibility-shim design

A separate VW MIB2 implementation has independently reported a similar portability pattern:

```text
small firmware-specific loader / adapter
        |
        +--> native hooks via LD_PRELOAD where needed
        |
        +--> Java hooks via bootclasspath where needed
        |
        v
largely project-owned feature libraries
```

That report is useful corroboration, but it is not source-verified evidence for this project.

The design principle is nevertheless consistent with the project's own firmware corpus:

> keep target-specific ABI knowledge in a small compatibility layer rather than spreading firmware-specific assumptions through the AltScreen feature implementation.

## 32.3 MU1440 vs VWG13 K4525 MU1367

A useful nearby VW baseline is `MHI2_ER_VWG13_K4525_MU1367`.

| Component | MU1440 | VWG13 K4525 MU1367 | Relation |
| --- | --- | --- | --- |
| `lsd.jxe` | 55,840,933 B · `a55d9cfb69c5...` | 55,840,541 B · `09167f1d0ae5...` | whole file differs |
| `dio_manager` | 686,552 B · `4d6867bdd4c9...` | 684,305 B · `ead570d45071...` | binary differs |
| `smartphone_integrator` | 806,539 B · `14b8458144c2...` | 806,540 B · `a566f3bebfd7...` | binary differs |
| `libairplay.so` | 703,688 B · `193a4fd9101e...` | 703,688 B · `193a4fd9101e...` | byte-identical |

The important interpretation is:

```text
same/near platform family
    !=
all loader-facing binaries byte-identical
```

At the same time, whole-`lsd.jxe` inequality does **not** imply all relevant Java classes differ. The existing compatibility work already shows exact stock-class matches for multiple Direct-VC Java seams between these profiles.

The exact VWG13 `gal` hash is not yet included in the curated comparison used for this section and should be retrieved from the already admitted corpus before making an equality claim.

---

# 33. Minimal future HMI vehicle PoC

The first HMI vehicle test should prove only the additive UI mechanism.

Suggested page:

```text
CarPlay AltScreen

Enabled     [On / Off]
Alignment   [Auto / Left / Right]

Back
```

The backend should initially be in-memory only.

The first test should not:

- change CarPlay transport state;
- write productive DSI values;
- edit persistent runtime markers;
- replace `Cmc.jxe`, `Ssm_5458.jxe` or `Cm_0409.jxe`;
- replace the stock `viewhandler.zip`.

Required result:

1. stock HMI starts normally;
2. the existing FPK parent remains usable;
3. the new sibling opens;
4. input works;
5. Back works;
6. re-entry works;
7. unrelated stock views remain unaffected;
8. disabling/removing the project addition restores stock behavior deterministically.

Only after this UI-only proof should real AltScreen settings be connected.

---

# 34. Static work before vehicle testing

The following can be completed without another vehicle session:

1. compare the exact MU1440 `JxeSkinClassLoader`, `XIPClassLoader`, `FileSPI`, `Archive` and `JxeClassLoader` implementations with the readable framework source;
2. determine whether missing-`MibrAltScreenSettings.jxe` is operationally non-fatal on the exact target;
3. prove or reject parent/bootclasspath resolution for a new generated-package ViewHandler class;
4. map the minimal ViewHandler ABI: superclass, interfaces, constructor, post-construction lifecycle, widget initialization, event/listener lifecycle and Back handling;
5. build a compile-only normal-JAR prototype before considering JXE generation;
6. retrieve and compare the VWG13 `gal` artifact from the already admitted corpus;
7. define exact deployment/rollback files and keep stock behavior as the default gate.

Decision tree:

```text
missing per-view JXE non-fatal?
        |
   no --+--> custom JXE / XIP overlay path
        |
       yes
        |
        v
bootclasspath class visible to loader?
        |
   no --+--> custom JXE / XIP overlay path
        |
       yes
        |
        v
normal JAR class satisfies ViewHandler ABI?
        |
   no --+--> target JXE generation / loader patch
        |
       yes
        |
        v
minimal bootclasspath-only sibling-view PoC
```

This is now the preferred order of work.


---

# 35. Existing-view WidgetFactory injection

A separate VW MIB2 implementation clarified an important alternative to creating a new ViewHandler.

That implementation leaves stock ViewHandler JXEs unchanged and instead:

- prepends a small Java boot JAR with `-Xbootclasspath/p:`;
- overrides the generated global `WidgetFactoryImpl`;
- returns project-owned subclasses for selected stock widget types;
- builds the extra UI programmatically from normal stock widgets inside an existing stock view;
- guards activation by the host view identity plus target ID;
- reuses the stock host view lifecycle and close/back behavior.

This is external implementation evidence rather than vehicle proof for MU1440, but the mechanism matches the readable MIB2 framework architecture closely.

## 35.1 Why the seam exists

The generated global factory implements:

`WidgetModel getWidgetInstance(int widgetType)`

and maps type IDs to concrete widget classes such as:

| Type | Stock widget |
| ---: | --- |
| 2 | `Button` |
| 3 | `Canvas` |
| 11 | `Container` |
| 49 | `TextArea` |
| 54 | `View` |
| 55 | `WidgetList` |

The stock tree-builder path wraps this factory with `PoolingWidgetFactory`.

Therefore a bootclasspath replacement of the factory can preserve the stock JXE/tree definition while changing the concrete Java class instantiated for one widget type.

## 35.2 Important safety property

This seam is global.

A replacement for a common type such as `Container` or `WidgetList` can be instantiated in many unrelated views and may also be created during pool prefill.

The custom subclass must therefore be completely stock-compatible outside its intended target.

Target gating should happen only after normal tree initialization has provided context such as:

- host `ViewModel`;
- target ID;
- widget name;
- parent/qualified widget path.

The constructor must remain side-effect free.

## 35.3 Relevance to AltScreen

This creates a lower-complexity candidate for the first HMI extension:

```text
stock Cmc or Ssm_5458 JXE
        |
        v
stock tree builder
        |
        v
bootclasspath-overridden WidgetFactoryImpl
        |
        v
one guarded project widget subclass
        |
        v
small UI subtree made from stock widgets
```

No new ViewHandler JXE is required by this design.

Preferred final product location remains the stock FPK / Virtual Cockpit area (`Cmc`).

The smaller Smartphone Integration setup view (`Ssm_5458`) remains a useful first engineering proof because the external implementation already demonstrates the same general App-Connect injection pattern.

---

# 36. Updated HMI implementation priority

The preferred order is now:

1. **Existing-view WidgetFactory injection**  
   Lowest unresolved format/tooling cost. No new JXE and no stock ViewHandler replacement.

2. **New sibling ViewHandler through ordinary Java/bootclasspath resolution**  
   Still useful if the product UX requires a fully separate page.

3. **Custom JXE / multi-archive XIP overlay**  
   Keep as a fallback if a separate page cannot be supplied through normal Java loading.

4. **Replace a stock ViewHandler/JXE**  
   Avoid for the first implementation.

The first static task is therefore no longer custom-JXE generation.

It is to identify one robust anchor widget in `Cmc` or `Ssm_5458`, verify the exact MU1440 factory ABI and build an exact-stock-compatible factory override that is inert everywhere else.


---

# 37. Exact MU1440 WidgetFactory anchor and compile proof

The WidgetFactory path has now been checked against the exact retained MU1440 Java baseline.

## 37.1 Exact App-Connect host

The exact `Ssm_5458.jxe` contains:

```text
View "SMI_SETUP_MAIN"
  targetId = 24786208
  └─ Container "Container"
     targetId = 81171177
     x=0 y=84 w=1280 h=556
     └─ WidgetList "WidgetList"
        targetId = 47234883
```

This exactly matches the `SMI_SETUP_MAIN + 81171177` host guard independently reported by a
compatible VW implementation.

The target ID was recovered from the exact J9 ROM `WidgetInit.initContainer(...)` call, not from a
free-form string search.

Classification:

`MU1440_SMI_WIDGETFACTORY_HOST_MATCH = PROVEN_EXACT_STATIC`

## 37.2 Exact factory/tree/pooling ABI

The retained MU1440 decompilation is byte/text-identical to the readable public MIB2 source for the
relevant seam, including:

- `WidgetFactoryImpl`;
- `WidgetTreeBuilderFactory`;
- `Container`;
- `AbstractWidget`;
- `PoolingWidgetFactory`;
- `PoolingWidgetFactory$WidgetPool`;
- `WidgetFactory`.

The stock tree builder creates widgets through the global factory, then separately assigns the stock
controller and UI and applies the stock parent/child relationships.

The stock factory maps type 11 to `Container`. The exact Container pool is configured for 1,580
instances, so a replacement class can be created during pool prefill before a view exists. Any
project subclass must therefore have a side-effect-free constructor and strict runtime host gating.

## 37.3 Compile-only two-class PoC

A private/research compile-only prototype now builds successfully against the exact retained MU1440
classpath using the target IBM J9 toolchain.

The PoC contains exactly:

```text
generated/de/vw/mib/global/view/internal/WidgetFactoryImpl.class
de/mibr/hmi/MibrContainer.class
```

The modified factory changes only:

```text
type 11:
  Container -> MibrContainer
```

The subclass currently injects **no UI**. It only verifies that the exact host guard can be expressed
against the stock ABI and that project state is cleared on de-initialization/pool reset.

Both classes compile as classfile major 46.

Build classification:

`WIDGETFACTORY_COMPILE_POC = PROVEN_BUILD`

Vehicle classification:

`VEHICLE_WIDGETFACTORY_POC = NOT_RUN`

## 37.4 Remaining static gate

The next problem is ownership of newly created child widgets.

Stock `WidgetTreeBuilderImpl` normally owns:

```text
widget allocation
+ controller allocation
+ UI allocation
+ parent/child relationships
+ separate controller/UI/widget destruction
```

A raw programmatic `new Button()` or `new TextArea()` inside the custom Container does not
automatically pass through that ownership path.

The first vehicle test should therefore wait until a lifecycle-correct injected-child pattern is
established or until the first PoC is deliberately reduced to reusing an existing stock child.


---

# 38. Programmatic child ownership and staged proof

Exact MU1440 framework analysis closes most of the lifecycle question for project-owned widgets.

A custom host Container does not have to push manually created children through the stock widget
pools. It can own them directly.

The exact stock APIs provide:

```text
widget.setController(controller)
  -> controller.setWidget(widget)

widget.setUI(ui)
  -> ui.setWidget(widget)

container.setChildren(...)
  -> establishes parent relationships
```

The host Container then naturally propagates:

```text
activate
deActivate
deInit
```

through its current child array.

For a child appended after `super.init(viewModel)`, the project must explicitly call
`child.init(viewModel)`, because the stock Container's child-init pass has already completed.

A project-owned directly allocated widget/controller/UI should not be returned to the stock pools.
After normal de-initialization and removal from the host child array, the objects can be released by
normal VM garbage collection.

## 38.1 Lower-risk proof before adding children

A compile-only visible-marker variant has also been prepared using an existing stock widget rather
than creating a new one.

The factory substitutes a `TextArea` subclass only for the exact stock CarPlay row label:

```text
view       = SMI_SETUP_MAIN
targetId   = 92192369
widgetName = TextArea
```

The subclass keeps the stock UI/lifecycle and only replaces the displayed label with an unmistakable
test string. It performs no CarPlay/runtime action.

This gives a useful staged validation order:

```text
P0  factory + strict host guard compile             complete
P1  existing-widget visible marker                  built; vehicle test pending
P2  one project-owned Button + TextArea             next
P3  one semantic AltScreen action                   later
P4  full stock-style settings controls              later
```

The intent of P1 is to prove the bootclasspath/factory mechanism on the vehicle before changing the
stock child tree.


---

# 39. Minimal first vehicle proof

The first future HMI vehicle proof has been reduced further.

It does **not** substitute `Container` and does not add any new child widgets.

The minimal candidate changes only the stock widget factory's type-49 allocation:

```text
TextArea -> project TextArea subclass
```

and that subclass remains inert unless the exact stock host matches:

```text
view       = SMI_SETUP_MAIN
targetId   = 92192369
widgetName = TextArea
```

This target is the existing TextArea inside the stock CarPlay information row.

The only proof effect is a visible test string. No CarPlay or AltScreen runtime state is changed.

The candidate build additionally verifies its generated `WidgetFactoryImpl` against the retained
exact MU1440 source and rejects any factory delta beyond the intended TextArea substitution.

Therefore the staged order is now:

```text
P1  one existing stock TextArea subclass only
P2  guarded Container + project-owned child widgets
P3  semantic runtime action
P4  complete stock-style settings UI
```

This keeps the first runtime experiment independent of the more invasive pooled-Container path.
