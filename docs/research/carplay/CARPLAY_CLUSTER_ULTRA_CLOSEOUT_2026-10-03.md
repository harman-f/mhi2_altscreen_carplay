# CarPlay cluster / Ultra research closeout — 2026-10-03

> **Research status · 2026-11-05:** **CARPLAY RESEARCH REFERENCE.** Preserve the original date and evidence level; newer source and actual installed behavior must be checked separately. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


This note closes the public-research thread that started from LIVI's cluster-stream implementation and
then expanded into current iOS CarPlay/CarPlay Ultra internals. It is deliberately split into
**current MU1440 work**, **protocol conclusions**, and a **deferred local-compositor side track**.

## Scope and exact current Apple target

The current sender authority remains:

- iOS `27.2 beta 2`
- build `24B5089g`
- device slice `iPhone14,2`
- AirPlaySender source generation `1005.8.1.0.0`

See [IOS27_SENDER_LIFECYCLE.md](IOS27_SENDER_LIFECYCLE.md) for exact hashes and extraction
provenance.

## Closed classic Type-111 conclusions

### 1. Type 111 is the actual auxiliary cluster video stream

The classic CarPlay instrument-cluster path is a distinct Auxiliary / ScreenAlt stream. Normal
navigation-provider or UI-role changes do not by themselves imply a fresh Type-111 SETUP.

### 2. The relevant classic cluster URL family is three roles

Current exact iOS 27.2 evidence uses:

```text
maps:/car/instrumentcluster
maps:/car/instrumentcluster/map
maps:/car/instrumentcluster/instructioncard
```

Interpretation:

| URL | Role |
| --- | --- |
| base | generic/root instrument-cluster presentation |
| `/map` | persistent map-oriented presentation |
| `/instructioncard` | transient maneuver / turn-card presentation |

No fourth classic `maps:/car/instrumentcluster/...` role was established in this research pass.
Private/modern families such as `nextGenHostedContent:` belong to a different hosted/next-generation
presentation system and must not be treated as drop-in classic `showUI` URLs.

### 3. `suggestUI`, `showUI`, `modesChanged` and ViewArea are separate controls

Do not collapse these into one state machine:

- `suggestUI` advertises/evaluates candidate UI contexts;
- `showUI` / `stopUI` control a selected presentation;
- `modesChanged` carries ownership/app/audio/turn state;
- ViewArea switching uses the ViewArea control path.

A provider/app change can therefore happen while Type 111 remains established.

## ViewArea / SafeArea closeout

### Protocol model

The receiver declares one or more ViewAreas during display negotiation. Each declared ViewArea owns
its geometry and nested SafeArea.

Conceptually:

```text
Display 111
  viewAreas[0]
    rect      = A
    safeArea  = A-safe

  viewAreas[1]
    rect      = B
    safeArea  = B-safe

  initialViewArea = 0
```

An in-session transition selects a **previously declared index**:

```text
type = updateViewArea
params.uuid                    = <display UUID>
params.viewAreaIndex           = <declared index>
params.animationDurationMillis = <duration>
params.adjacentViewAreas       = [ ... ]
```

This is a same-screen presentation transition. It does not inherently create a new Type-111 stream
and it does not carry a replacement rectangle.

### SafeArea consequence

There is no evidence here for an arbitrary classic command equivalent to:

```text
setSafeArea(x, y, w, h)
```

during a running session.

The supported model is instead:

```text
declare ViewArea 0 + SafeArea 0
declare ViewArea 1 + SafeArea 1
...
select ViewArea N in-session
```

Thus a live SafeArea change is achievable by switching among predeclared ViewArea presets, not by
mutating the active rectangle in place.

### LIVI correction

LIVI demonstrates that CarPlay display and cluster descriptors can carry independent `viewArea` and
`safeArea` values, but LIVI is **not** evidence for live mutation of those values.

Its CarPlay `applyDisplayConfig()` only merges configuration locally. The UI lists
`clusterViewArea*` and `clusterSafeArea*` among settings requiring projection restart; the new
geometry is then used during the next negotiation/`/info` cycle.

The live mechanism to study is therefore the actual CarPlay multi-ViewArea protocol, not LIVI's
settings refresh path.

## Current MU1440 implementation state

The GEN2 source already contains an `updateViewArea` command builder, but the current advertised
descriptor contains only one ViewArea. The existing command builder also does not yet serialize the
full `adjacentViewAreas` field.

Therefore:

- the protocol path is understood;
- the current implementation has scaffolding;
- a real 0 <-> 1 transition is not yet a vehicle-proven feature;
- this is not a blocker for the current single-ViewArea Type-111 milestone.

A bounded future PoC, if desired, is:

1. advertise two calibrated ViewAreas with different SafeAreas;
2. provide valid adjacency metadata;
3. switch 0 <-> 1 with `updateViewArea`;
4. verify that Type 111 remains established;
5. record VideoConfig/IDR behavior and transition latency;
6. only then bind the selector to a real VC layout-state signal.

## Deferred side track: local video/instrument compositor

The discussion also explored whether CP111 could contain arbitrary locally controlled gauges such as
speed and RPM.

Conclusion: classic CP111 itself is iPhone-rendered. The head unit can negotiate display geometry and
UI context but does not get a free-form canvas inside the iPhone-generated video.

Current CarPlay Ultra architecture is nevertheless valuable as a blueprint because it explicitly
separates:

```text
remote iPhone video
+ local vehicle-rendered instruments
+ vehicle-state data sources
+ local composition / synchronization
```

Publicly recoverable framework structure supports a declarative instrument model. Relevant current
concepts include:

- `CarPlayAsset` / `CarPlayAssetUI`;
- `InstrumentDataIdentifier`;
- `DataSourceManager` / `InstrumentDataSource`;
- `DBInstrumentDataSources`;
- `ClusterTransitionCoordinator`;
- local instrument families for speedometer, tachometer, power, charge/fuel and temperature.

Concrete instrument data identifiers recovered during this pass include, among many others:

```text
vehicleSpeed
vehicleSpeedUnit
vehicleSpeedMax
showSecondarySpeed

engineRPM
engineRPMState
engineRPMMax
engineMarkerRedlineRPM

transmission
gearShiftRecommendation
cruiseControlSpeed
cruiseControlState
fuelLevel
chargeLevel
engineTemperature
outsideTemperature
```

The vehicle-data layer also exposes matching primitives such as `CAFEngineRPM` with rotational speed,
state, redline and maximum, which are adapted by Dashboard into abstract instrument data sources.

This makes a future MHI2 architecture plausible:

```text
CP111 map video -> decode -> local GLES compositor
                              +
                       EXLAP / DSI / BAP / CAN
                              ->
                        local instruments
                              ->
                             MOST
                              ->
                             AID
```

That architecture is **DEFERRED**. It is not part of the current implementation target and should not
be allowed to complicate the proven direct compressed-video path.

## Research closure

For the current classic CP111 milestone, this research thread is considered closed:

- classic URL roles: resolved;
- LIVI geometry behavior: resolved;
- same-session ViewArea mechanism: resolved at protocol/static-analysis level;
- SafeArea semantics: resolved as per-ViewArea negotiated metadata;
- arbitrary local overlays inside CP111: not supported by the classic model;
- local Ultra-like compositor: preserved as a deferred design track.

Remaining work in these areas is implementation/vehicle validation, not another broad static-research
pass.
