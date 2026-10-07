# MU1440 debug / test configuration surface

Status: **development authority for the configurable vehicle-test build**  
Target: **MHI2 ER SKG13 P4526 MU1440 + AID10, classic CarPlay AlternateScreen type 111**

## Goal

The near-term vehicle build is intentionally a debug/test configuration, not a fixed one-off patch.

The same semantic settings backend should serve three phases:

1. direct SSH / scripted vehicle testing;
2. the planned on-unit HMI configuration menu;
3. later stable defaults once individual controls are qualified.

A setting must not gain a second implementation merely because it moves from shell testing into the
HMI. The registry/helper remains the authority.

## Layer model

Current registry precedence:

```text
temp > persistent > profile > compiled
```

Temporary state is the normal A/B-test surface. Persistent mutation remains policy-gated until the
backup/power-loss contract for the full settings backend is qualified. Drive diagnostics have their
own separately qualified temp/persistent switches.

## Apply classes

Every setting declares when it can take effect:

- `live`: current session can consume it without rebuilding CarPlay negotiation;
- `presentation`: serialized UI/presentation refresh is required;
- `session`: parity ownership/session restart boundary;
- `reconnect`: fresh CarPlay AlternateScreen negotiation is required.

The future HMI must expose this distinction instead of implying that every toggle is instantaneous.

## Current registry

The current schema contains 48 settings.

### Normal

User-facing vehicle-test controls:

- CarPlay AltScreen enabled;
- selected ViewArea;
- navigation query generation;
- navigation surface: base / map / instruction card;
- ETA visibility;
- speed-limit visibility;
- compass visibility;
- maneuver layout.

### Advanced

Composition and timing controls:

- profile selection;
- announced/output max FPS;
- compatibility source version;
- keyframe mode and cadence;
- showUI-assisted keyframe recovery;
- ViewArea enable/count/initial index/transition time;
- ViewArea 0 and 1 geometry;
- nested SafeArea 0 and 1 geometry;
- adjacency;
- raw navigation URL override.

The project-neutral compatibility profile is `classic_single_view`. The current AID10 dual-layout
test profile remains `mibr_dual_view`.

### Developer

Low-level diagnostic controls:

- gap recovery;
- latency recovery;
- ownership backend;
- display physical dimensions and UUID;
- read-only fixed AID10 pixel dimensions;
- advertised/suggested UI URL set;
- read-only legacy Auto-Direct state.

## Drive diagnostics

Drive diagnostics are deliberately separate from visual CarPlay configuration.

`parity_drive_status.sh` controls:

- status logging on/off;
- statistics on/off;
- temp or persistent override;
- clear-temp.

Statistics require live status counters. The drive supervisor records evidence only to:

```text
/net/mmx/fs/sda0/esd/carplay-test/logs/parity-drive/
```

after a successful SD RW remount and write test.

## Already testable classic control families

The research matrix supports controlled MU1440 experiments for:

- `showUI`, `stopUI`, `requestUI`, `suggestUI`;
- `forceKeyFrame`;
- `changeMapZoomLevel`;
- `requestViewArea` / `updateViewArea`;
- per-display UI/map appearance controls;
- ViewArea/SafeArea selection and geometry.

These should become explicit semantic actions/settings in the debug surface as they are promoted from
research probes.

## Experimental configuration backlog

The following areas remain valuable for the later debug build but are **not** part of the current
drive candidate:

- `primaryInputDevice` / Knob and display-bound HID advertisement;
- focus-transfer and UI-context capabilities;
- Smart Display Zoom / display scale;
- hosted/NextGen presentation modes;
- PassengerDisplay;
- Enhanced Siri;
- GaugeCluster / DataProtocol-related capability experiments;
- broader feature-advertisement experiments.

They must be guarded, off by default and visibly labelled experimental until exact-target negotiation
and rollback behavior is established.

## Raw-bit rule

Raw AirPlay feature bits are not user-facing configuration.

In particular:

- bit 26 is Audio AES capability, not an AlternateScreen enable switch;
- bit 37 is CarPlay Control / connection-control capability, not a Type-111 display switch.

If a future experiment requires one of these capabilities, expose the semantic capability with its
scope and apply class. Do not reintroduce generic `bit26 on/off` or `bit37 on/off` UI controls.

## HMI direction

The planned HMI should consume the same registry and group controls into:

```text
CarPlay Cluster
  ├─ Normal
  ├─ Advanced
  ├─ Developer
  ├─ Diagnostics
  └─ Experimental
```

For every mutable setting the UI should show:

- effective value;
- source layer;
- apply class;
- whether reconnect/session restart is required;
- temporary test vs persistent storage state.

This keeps the present SSH test build and the later on-unit menu on one control plane.

## Public naming rule

Implementation-facing names are project-neutral. Comparator/upstream identities stay in research and
provenance documentation, not in project runtime filenames, branch names, profile IDs, log paths or
build artifact names.
