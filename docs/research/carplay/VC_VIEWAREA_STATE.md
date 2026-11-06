# MU1440 Virtual Cockpit view-state / ViewArea research

> **Research status · 2026-11-05:** **CARPLAY RESEARCH REFERENCE.** Preserve original evidence boundaries; newer build behavior needs separate proof. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


This page documents the **Škoda/VW MU1440** state seams currently considered valid for future
dynamic CarPlay ViewArea/SafeArea work.

It also records one important correction: an earlier prototype used Audi/MHI2Q evidence that is not
present in the exact MU1440 stock Java corpus.

## 1. Do not use Audi CombiMapController as MU1440 authority

The recovered Audi/MHI2Q HMI package contains a `CombiMapController` and APIs around view size,
skin, context and KDK state.

A later exact-target audit proved that class is **not present** in the reconstructed MU1440 LSD
baseline.

Therefore these are useful comparator clues, not exact MU1440 source authority:

- Audi `CombiMapController`;
- model 402521 / `ChoiceModelGUI`;
- Audi HMI terminal ViewSize;
- Audi KDK composition state.

Do not build a Škoda runtime listener around those names merely because the behavior looks similar.

## 2. Exact MU1440 KombiView family

The exact MU1440 Java corpus contains:

```text
de.vw.mib.asl.internal.mostkombi.kombiview.controller.KombiViewController
```

and related:

- `KombiViewCategoryManager`;
- `KombiViewHsmContext`;
- initialize/running states;
- enable/visibility/route-info functions.

This appears to be a real feature/lifecycle slot, but it does not by itself expose a complete
physical AID layout selector.

## 3. Stronger current-state seam: mostkombi.streamsink

### NavigationMapAdapter

Exact class:

```text
de.vw.mib.asl.internal.mostkombi.streamsink.api.navimap.NavigationMapAdapter
```

Useful passive state:

- `getKombiMapStatus()`;
- `getKombiMapVisibility()`;
- `getMapSwitchState()`;
- `getMapInAbtVisibility()`;
- `getNavigationMapServiceState()`;
- `isMapSwitchPossible()`.

These describe map ownership/visibility and ABT<->Kombi transitions.

### DisplayManagementAdapter

Exact class:

```text
de.vw.mib.asl.internal.mostkombi.streamsink.api.displaymanagement.DisplayManagementAdapter
```

Useful passive state:

- `getKombiDisplay()`;
- `getDataFrameRate()`.

Known command-side methods include:

- `switchToKombiDisplayContext(int)`;
- `setDataFrameRate(int)`.

The first measurement phase should remain passive.

### DSI stream-sink state

Already used by the Direct-VC research:

```text
DSIKOMOGfxStreamSink.ATTR_DATARATE
 -> ChangeDataRate.dsiKOMOGfxStreamSinkUpdateDataRate(...)
```

This is a reliable graphics-stream state but is not yet proven to distinguish every physical cluster
layout.

## 4. Current passive state tuple

The first useful MU1440 layout probe should correlate at least:

```text
raw DSI requested rate
effective project policy rate
Kombi display
DisplayManagement data-frame-rate state
Kombi map status
Kombi map visibility
map switch state
map-in-ABT visibility
navigation-map service state
map-switch possible
navigation-map-switch-supported
```

Then manually change exactly one visible VC layout.

If the entire tuple stays unchanged while the physical AID layout changes, that is valuable negative
evidence:

> the actual layout selector is elsewhere, likely another datapool/BAP/cluster-display service.

Do not force-fit Audi model IDs into that gap.

## 5. CarPlay ViewArea / SafeArea model

Current sender-side research establishes that the secondary display can expose a `viewAreas` array
with a nested `safeArea` and an `initialViewArea`.

The current GEN2 development source deliberately starts conservatively with one full-canvas
1010×376 ViewArea/SafeArea rather than importing Audi-specific geometry.

The long-term model may become:

```text
actual stock VC layout state
       │
       ▼
project layout abstraction
       │
       ▼
matching CarPlay ViewArea / SafeArea
       │
       ▼
existing Type-111 session
```

Exact iOS research also identifies an in-session ViewArea request path, so a different physical
layout does not automatically imply another Type-111 stream.

## 6. Screenshot lead

The exact MU1440 DisplayManager tooling includes a screenshot path, and DMDT exposes a `ts`
operation.

This can potentially help measure cluster regions, but one question must be answered first:

> Does a screenshot of the relevant logical display contain the final Virtual Cockpit composition
> including gauge overlays, or only an upstream source surface?

Until proven, do not use a DMDT screenshot as unquestioned pixel geometry authority.

## 7. Privacy rule for layout work

Front-on vehicle screenshots/photos may reveal navigation position.

Prefer:

- state tuples;
- generic test patterns;
- sanitized/cropped captures;
- manually measured rectangles without location-bearing map content.

## 8. Contribution target

A particularly useful external contribution is a table like:

| Human-visible layout | State tuple changed? | ViewArea candidate | Cluster/AID |
| --- | --- | --- | --- |
| large map / small dials | ... | ... | ... |
| classic / large dials | ... | ... | ... |
| sport / other | ... | ... | ... |

The first goal is not to force a dynamic ViewArea change. It is to map the real stock state reliably.
