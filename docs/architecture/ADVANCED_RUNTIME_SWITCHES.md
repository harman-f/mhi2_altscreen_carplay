# Advanced runtime switches and configuration surface

Status: **current development reference**  
Target: **MHI2_ER_SKG13_P4526_MU1440 + AID10**  
Scope: classic CarPlay AlternateScreen / ScreenAlt / stream type 111 plus parity-drive runtime controls.

> [!IMPORTANT]
> This document is no longer a historical marker-by-marker list.
> The active implementation uses the shared semantic settings registry in
> [`settings/registry.json`](../../settings/registry.json), with the design contract documented in
> [`MU1440_DEBUG_CONFIGURATION_SURFACE.md`](MU1440_DEBUG_CONFIGURATION_SURFACE.md).
>
> Do not silently add, remove, rename or redefine settings merely because a comparator, experiment or
> older script uses a different marker. New controls must be promoted deliberately into the shared
> semantic surface.

## 1. Current architecture boundary

The runtime configuration belongs to the current four-component vehicle path:

```text
libaltscreen111.so
  CarPlay Type-111 source/control plane

parity-session
  ownership, watchdog, lifecycle and fail-safe stock restore

direct-ts-parity
  complete M1AU/AU -> PTS/PES/MPEG-TS -> /dev/mlb/isoTX2

libmibr_isotx2_guard.so
  DisplayManager-side STOCK/DIRECT arbitration proof
```

`alt111-settings` is the CLI frontend to the shared settings subsystem. It is not a separate
settings daemon. The parity-drive supervisor is orchestration only and does not own the safety
boundary.

## 2. Configuration precedence

The current semantic registry uses:

```text
temp > persistent > profile > compiled
```

Nominal locations:

```text
/tmp/<basename>          temporary override
/mnt/app/root/<basename> persistent override
profile                  selected compatibility/profile defaults
compiled                 final fallback
```

Temporary state is the preferred A/B-test surface. General persistent mutation is still policy-gated
until the backup/power-loss contract is qualified. The separately qualified parity-drive diagnostic
switches support both temporary and persistent layers.

## 3. Apply classes

Every semantic setting declares when it becomes effective:

| Apply class | Meaning |
| --- | --- |
| `live` | Current session can consume the value directly. |
| `presentation` | Serialized presentation/UI refresh is required. |
| `session` | Parity/ownership session boundary. |
| `reconnect` | Fresh CarPlay AlternateScreen negotiation is required. |

Do not use repeated hard restarts of stock `smartphone_integrator`, `dio_manager` or
`DisplayManager` as a generic apply mechanism.

## 4. Current profiles

### `classic_single_view`

Current project-neutral single-view reference profile:

- CarPlay enabled;
- maxFPS 40;
- sourceVersion 950.7.1;
- one ViewArea, 1010x376;
- ViewArea-0 SafeArea 202,16 / 606x344;
- map presentation URL;
- source-frame keyframe mode, 20-frame interval;
- legacy Auto-Direct disabled.

### `mibr_dual_view`

Current two-layout AID10 test profile:

- maxFPS 40;
- sourceVersion 950.7.1;
- two ViewAreas;
- ViewArea-0 SafeArea 202,16 / 606x344;
- ViewArea-1 SafeArea 0,58 / 1010x248;
- navigation URL auto;
- advertised base/map/instruction-card URLs.

### `mibr_legacy`

Compatibility/reference profile:

- maxFPS 30;
- sourceVersion 1005.8.1;
- two ViewAreas;
- legacy-style navigation defaults.

## 5. Active semantic registry

The current schema contains **48 settings**. The generated registry is the implementation source of
truth for exact basenames, validation ranges and defaults.

### Normal

| Key | Backing setting | Apply |
| --- | --- | --- |
| `carplay.enabled` | `mibr-carplay111-enabled` | session |
| `viewarea.selected` | `mibr-carplay111-viewarea-selected` | live |
| `navigation.query` | `mibr-carplay111-nav.conf:query` | presentation |
| `navigation.surface` | `mibr-carplay111-nav.conf:surface` | presentation |
| `navigation.ETA` | `mibr-carplay111-nav.conf:showETA` | presentation |
| `navigation.speedLimit` | `mibr-carplay111-nav.conf:showSpeedLimit` | presentation |
| `navigation.compass` | `mibr-carplay111-nav.conf:showCompass` | presentation |
| `navigation.maneuver` | `mibr-carplay111-nav.conf:maneuverLayout` | presentation |

### Advanced

| Key | Backing setting | Apply |
| --- | --- | --- |
| `preset.id` | `mibr-carplay111-compat-profile` | reconnect |
| `maxFPS` | `mibr-carplay111-fps` | reconnect |
| `sourceVersion` | `mibr-carplay111-sourceversion` | reconnect |
| `keyframe.mode` | `mibr-carplay111-keyframes.conf:mode` | live |
| `keyframe.interval_frames` | `...:interval_frames` | live |
| `keyframe.interval_ms` | `...:interval_ms` | live |
| `keyframe.showui` | `...:showui` | live |
| `viewareas.enabled` | `mibr-carplay111-viewareas.conf:enabled` | reconnect |
| `viewareas.count` | `...:count` | reconnect |
| `viewareas.initial` | `...:initial` | reconnect |
| `viewareas.transition_ms` | `...:transition_ms` | live |
| `viewarea.0.x/y/w/h` | ViewArea 0 geometry | reconnect |
| `viewarea.0.safe.x/y/w/h` | ViewArea 0 SafeArea | reconnect |
| `viewarea.0.adjacent` | ViewArea 0 adjacency | reconnect |
| `viewarea.1.x/y/w/h` | ViewArea 1 geometry | reconnect |
| `viewarea.1.safe.x/y/w/h` | ViewArea 1 SafeArea | reconnect |
| `viewarea.1.adjacent` | ViewArea 1 adjacency | reconnect |
| `navigation.url` | `mibr-carplay111-url` | presentation |

### Developer

| Key | Backing setting | Apply |
| --- | --- | --- |
| `keyframe.gap_recovery` | `mibr-carplay111-keyframes.conf:gap_recovery` | live |
| `keyframe.latency_recovery` | `...:latency_recovery` | live |
| `ownership.backend` | `mibr-carplay111-ownership.conf:backend` | session |
| `display.widthPixels` | fixed 1010 | reconnect / read-only |
| `display.heightPixels` | fixed 376 | reconnect / read-only |
| `display.widthPhysical` | display physical width | reconnect |
| `display.heightPhysical` | display physical height | reconnect |
| `display.uuid` | AlternateScreen display UUID | reconnect |
| `presentation.suggested_urls` | `mibr-carplay111-ui-urls.conf:urls` | reconnect |
| `legacy.autodirect` | `mibr-carplay-autodirect` | session / read-only, forced 0 |

Exact allowed values and numeric ranges are intentionally not duplicated here where that would create
a second schema. Read them from `settings/registry.json`.

## 6. Runtime helpers

Current vehicle-facing helpers include:

```text
parity_profile.sh
parity_session.sh
parity_status.sh

parity_drive_supervisor.sh
parity_drive_enable.sh
parity_drive_disable.sh
parity_drive_status.sh

master_settings.sh
direct_fps.sh
gen2_sourceversion.sh
gen2_enabled.sh
gen2_display.sh
gen2_keyframes.sh
gen2_viewareas.sh
gen2_safearea.sh
gen2_nav_config.sh
gen2_url.sh
gen2_ui_urls.sh
gen2_compat_profile.sh
```

The wrappers must consume the shared settings backend. They must not create an independent settings
model.

## 7. Parity-drive lifecycle controls

Parity drive is the current guarded long-run/autostart path. It supersedes the legacy Auto-Direct
supervisor for this candidate.

Persistent enable marker:

```text
/mnt/app/root/mibr-parity-drive.enabled
```

Primary helpers:

```sh
/mnt/app/root/altscreen-u2/scripts/parity_drive_enable.sh
/mnt/app/root/altscreen-u2/scripts/parity_drive_disable.sh
/mnt/app/root/altscreen-u2/scripts/parity_drive_status.sh
```

Properties:

- default drive session is true until-stop operation;
- finite 60..7200-second operation remains a diagnostic override;
- no generic stock-process kill path;
- an existing parity owner is not disturbed;
- disable uses the token-bound `parity-session --stop` path;
- legacy Auto-Direct persistent state is forced to 0 for parity-drive operation;
- stock ownership restore remains the responsibility of `parity-session`, not the supervisor.

## 8. Status and statistics switches

Drive diagnostics are deliberately separate from visual CarPlay settings.

Controls:

```sh
parity_drive_status.sh status

parity_drive_status.sh status-on temp
parity_drive_status.sh status-off temp
parity_drive_status.sh statistics-on temp
parity_drive_status.sh statistics-off temp
parity_drive_status.sh all-on temp
parity_drive_status.sh all-off temp
parity_drive_status.sh clear-temp

parity_drive_status.sh status-on persistent
parity_drive_status.sh statistics-on persistent
```

Backing markers:

```text
/tmp/mibr-parity-status-enabled
/mnt/app/root/mibr-parity-status-enabled

/tmp/mibr-parity-statistics-enabled
/mnt/app/root/mibr-parity-statistics-enabled
```

Rules:

- temporary overrides persistent;
- default is ON for both in the current debug/test build;
- statistics require live status counters;
- diagnostic configuration applies to the next parity session.

SD evidence root:

```text
/net/mmx/fs/sda0/esd/carplay-test/logs/parity-drive/
```

The supervisor requires a successful SD RW remount and write test before starting a drive session.

## 9. Current source timing and transport model

The old direct-remux CFR/pacer description is obsolete for the current parity path.

Current transport contract:

```text
input              complete M1AU / complete H.264 AU
source clock       Stream-111 32.32 timestamp
PTS clock          source-derived 90 kHz
frame pacer        none
device pacing      QNX /dev/mlb/isoTX2 backpressure
physical write     12032 bytes = 64 * 188-byte TS packets
device open        write-only + O_NONBLOCK
write timeout      bounded 500 ms EAGAIN/write wait
```

The application no longer imposes a guessed 40-ms hardware-drain deadline.

Telemetry distinguishes source AUs, IDRs/non-IDRs, H.264 slice types, completed transport output,
sequence gaps, safe recovery, queue depth, block/byte counts, EAGAIN/errors and last/max write time.

Transport completion proves acceptance at the TS/MOST write boundary. It does **not**, by itself,
prove visible P-frame decode in the cluster; correlate counters with actual moving AID10 video.

## 10. Keyframe/recovery controls

Current keyframe modes:

```text
source_frames
source_time
event_only
off
```

Current reference profiles use `source_frames` with a 20-frame interval.

The recovery path may also issue bounded event-driven keyframe requests. A target-compatible
force-keyframe-only fallback exists through:

```text
/tmp/mibr-alt111-keyframe-only
```

Do not infer encoder GOP behavior merely from the configured request cadence.

## 11. ViewArea / SafeArea

The coded current canvas is **1010x376**. Do not reinterpret the physical 1280x480 AID10 panel as the
coded-video contract.

Current important candidates:

```text
ViewArea 0:
  x=0 y=0 w=1010 h=376
  SafeArea x=202 y=16 w=606 h=344

ViewArea 1:
  x=0 y=0 w=1010 h=376
  SafeArea x=0 y=58 w=1010 h=248
```

`classic_single_view` advertises one active ViewArea. `mibr_dual_view` advertises both.

Definition changes are reconnect-class. Selection between already advertised areas is live.

## 12. Navigation composition

Supported semantic surface values:

```text
base
map
instructioncard
```

Current navigation controls cover:

- query generation;
- surface;
- ETA;
- speed limit;
- compass;
- maneuver layout;
- raw URL override;
- advertised/suggested URL set.

These are presentation semantics, not media-transport settings.

## 13. Classic control/action backlog

The following actions/capabilities remain part of the controlled research/debug surface even when
they are not all first-class registry entries yet:

- `showUI`;
- `stopUI`;
- `requestUI`;
- `suggestUI`;
- `forceKeyFrame`;
- `changeMapZoomLevel`;
- `requestViewArea` / `updateViewArea`;
- per-display UI/map appearance controls.

Promotion into normal HMI/runtime configuration must use the shared semantic backend rather than
creating one-off markers.

## 14. Required switchable lockout

A recently introduced/decided **switchable lockout** remains a required debug/test control.

Its exact canonical semantics are not yet durably pinned in the public runtime schema under the term
"lockout". Until that reconciliation is complete:

- do not delete or forget the requirement;
- do not invent a new meaning, basename, default or target subsystem;
- do not claim the public configuration surface is complete while silently omitting it;
- reconcile the exact recent implementation semantics before promoting it into the registry/HMI.

This is intentionally fail-closed against accidental loss of the control.

## 15. Experimental backlog

Not part of the current drive baseline, but explicitly preserved for later controlled experiments:

- `primaryInputDevice` / knob behavior;
- display-bound HID/input advertisement;
- focus transfer / UI-context capabilities;
- Smart Display Zoom / display scaling;
- hosted/NextGen presentation modes;
- PassengerDisplay;
- Enhanced Siri;
- GaugeCluster / DataProtocol capability experiments;
- AllScreen/full-screen capability experiments;
- broader semantic feature-advertisement experiments.

These must remain guarded and clearly marked experimental until exact-target behavior and rollback are
qualified.

## 16. Raw feature-bit rule

Raw AirPlay feature bits are not normal user-facing switches.

In particular:

- bit 26 = Audio AES capability, **not** AlternateScreen enable;
- bit 37 = CarPlay Control / connection-control capability, **not** Type-111 enable.

If either capability is tested later, expose the semantic capability with explicit scope and apply
class. Do not reintroduce generic `bit26 on/off` or `bit37 on/off` UI controls.

## 17. Legacy controls no longer active

Do not revive these as current configuration:

- legacy persistent Auto-Direct supervisor;
- old D2 enable marker;
- split direct-output-FPS marker;
- old URL-map/autoshow markers;
- old standalone ViewArea marker;
- old nav-query marker;
- bit26/bit37 force markers as normal controls;
- direct-remux CFR/pacing settings as the current parity data path.

Historical files may still reference them for provenance, cleanup or rollback.

## 18. HMI direction

The planned on-unit HMI should consume the same registry:

```text
CarPlay Cluster
  ├─ Normal
  ├─ Advanced
  ├─ Developer
  ├─ Diagnostics
  └─ Experimental
```

For every mutable item, expose:

- effective value;
- source layer;
- apply class;
- temporary vs persistent state;
- reconnect/session/presentation requirement;
- capability/availability where relevant.

The HMI must not duplicate transport, ownership or settings logic.

## 19. Recovery rule

If an experimental configuration leaves the VC stale/frozen:

1. stop/disable the experimental path through its supported control;
2. return ownership to STOCK through the parity-session restore path;
3. verify ownership/gate state;
4. use the normal MHI/vehicle recovery boundary if necessary.

A fast MHI reboot does not necessarily reset every cluster/MOST/DSI peer state; full vehicle bus
sleep has previously been required for some stale dynamic-display states.

## Related current documents

- [MU1440 debug / test configuration surface](MU1440_DEBUG_CONFIGURATION_SURFACE.md)
- [MU1440 parity regression contract](MU1440_PARITY_REGRESSION_CONTRACT.md)
- [Current development status](../status/CURRENT_DEVELOPMENT_STATUS.md)
- [Settings registry](../../settings/registry.json)

Older dated Classic-111 contracts remain useful as historical evidence, but they no longer define the
current parity-drive runtime surface.
