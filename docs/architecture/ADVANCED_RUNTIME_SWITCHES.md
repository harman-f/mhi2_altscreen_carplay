# Runtime-control contract

This is the authoritative runtime-switch contract for the MU1440 / AID10 AltScreen development path.

## Precedence

Every **user-facing configuration value** uses the same basename in two locations:

```text
/tmp/<name>                   temporary override, highest priority
/mnt/app/root/<name>          persistent override
compiled/config default       used when neither file exists
```

Consequences:

- temporary A/B tests never require writing `/mnt/app`;
- a reboot removes the temporary layer automatically;
- after reboot the previous persistent value becomes effective again;
- a temporary value can explicitly disable a persistent enable by containing `0`;
- marker-file presence is no longer the user-facing configuration API.

One-shot diagnostic commands and read-only runtime state remain `/tmp`-only and are intentionally
outside this two-layer configuration model.

## Audited active settings

| Basename | Default | Values | Function |
| --- | --- | --- | --- |
| `mibr-carplay-autodirect` | `1` | `0/1` | Automatic Stream111 -> remux -> MOST ownership/runtime. |
| `mibr-carplay111-fps` | `30` | `20/25/30/40` | One FPS contract for both advertised Type-111 `maxFPS` and direct-output pacing. |
| `mibr-carplay111-framing` | `raw` | `raw/m1au` | Local GEN2 -> remux framing. M1AU preserves metadata; PTS/PCR remains CFR. |
| `mibr-carplay111-keyframes.conf` | see below | config | Automatic D2 receiver-requested keyframe recovery and timing. |
| `mibr-carplay111-sourceversion` | `1005.8.1` | `stock` or dotted version | AirPlay compatibility persona. Not the AltScreen gate. |
| `mibr-carplay111-viewareas` | `1` | `0/1` | Advertise `viewAreas` capability/descriptor. |
| `mibr-carplay111-safearea.conf` | full 1010x376 | rectangle config | SafeArea inside the Type-111 1010x376 logical canvas. |
| `mibr-carplay111-nav-query` | `0` | `0/1` | Enable navigation URL query parameters. |
| `mibr-carplay111-nav.surface` | `base` | `base/map/instructioncard` | Select classic cluster URL role. |
| `mibr-carplay111-nav.showETA` | `yes` | `yes/no/user` | `showETA` query value. |
| `mibr-carplay111-nav.showSpeedLimit` | `user` | `yes/no/user` | `showSpeedLimit` query value. |
| `mibr-carplay111-nav.showCompass` | `user` | `yes/no/user` | `showCompass` query value. |
| `mibr-carplay111-nav.maneuverLayout` | `none` | `none/left/right/top` | Maneuver alignment query. |

For every basename above the paths are mechanically:

```text
temporary  = /tmp/<basename>
persistent = /mnt/app/root/<basename>
```

## FPS

`mibr-carplay111-fps` intentionally replaces the former split between source FPS and direct-output
FPS. Testing mismatched source/sink rates is no longer a normal runtime switch; if such an experiment
is required it should be a deliberately instrumented diagnostic build.

Helper:

```sh
direct_fps.sh status
direct_fps.sh 20              # temporary
direct_fps.sh temp 25
direct_fps.sh persist 30
direct_fps.sh clear-temp
direct_fps.sh clear-persist
```

Changing effective source `maxFPS` requires a fresh CarPlay negotiation.

## Local framing

```sh
direct_source_mode.sh status
direct_source_mode.sh m1au          # temporary
direct_source_mode.sh persist raw
direct_source_mode.sh clear-temp
```

`raw` is raw Annex-B. `m1au` selects the 56-byte M1AU v1 access-unit envelope. The eight source
timestamp bytes remain raw/uninterpreted and do not drive PTS/PCR yet.

## D2 keyframe policy

Both enable/disable and timing now live in one file:

```text
mibr-carplay111-keyframes.conf

enabled=1
event_delay_ms=250
min_gap_ms=1000
watchdog_ms=1000
```

Defaults are exactly those four values. `watchdog_ms=0` disables only the periodic source-IDR
watchdog; event/suggestUI recovery can remain enabled.

These controls govern additional receiver-requested `forceKeyFrame` recovery. They do **not** set
the iPhone encoder's native GOP/IDR cadence.

Helper:

```sh
gen2_keyframes.sh status
gen2_keyframes.sh off                       # temporary
gen2_keyframes.sh timing 250 2000 0         # temporary
gen2_keyframes.sh persist on
gen2_keyframes.sh persist timing 250 1000 1000
gen2_keyframes.sh clear-temp
```

## sourceVersion

Default compatibility persona:

```text
1005.8.1
```

Useful diagnostics:

```sh
gen2_sourceversion.sh 950.7.1          # temporary
gen2_sourceversion.sh stock            # temporary; preserve stock MU1440 value
gen2_sourceversion.sh persist 1005.8.1
gen2_sourceversion.sh clear-temp
```

Changing the effective value requires a fresh CarPlay connection.

The canonical auxiliary-screen capability remains:

```text
AlternateScreen 0x01
 -> "altScreen" in enabledFeatures
 -> ScreenAlt / Type 111
```

## Navigation composition

The individual navigation fields remain separate on purpose: they map one-to-one to the classic
cluster URL/query contract and are useful for isolated A/B tests.

```sh
gen2_nav_config.sh status
gen2_nav_config.sh use-temp map-clean
gen2_nav_config.sh use-persist map-rich
gen2_nav_config.sh temp eta no
gen2_nav_config.sh persist maneuver right
gen2_nav_config.sh clear-temp
```

Known profiles remain:

`stock`, `base-rich`, `base-right`, `base-left`, `base-top`, `map-rich`,
`map-clean`, `maneuver-only`.

## SafeArea / ViewAreas

SafeArea is always relative to the 1010x376 Type-111 logical canvas, not the physical 1280x480 AID
panel.

```sh
gen2_safearea.sh status
gen2_safearea.sh set 0 58 1010 248          # temporary
gen2_safearea.sh persist set 0 58 1010 248
gen2_safearea.sh clear-temp

viewarea_mode.sh off                         # temporary
viewarea_mode.sh persist on
```

## Removed from the active contract

The switch audit deliberately removes these user-facing controls:

- `mibr-carplay111-bit26.force-on`
- `mibr-carplay111-bit26.force-off`

Root AirPlay bit 26 (`0x04000000`) is `AudioAES_128_MFi_SAPv1`, not AlternateScreen. MU1440
stock already advertises it. It is no longer an AltScreen runtime knob.

Also removed:

- `mibr-carplay111-url-map.enabled` — superseded by `mibr-carplay111-nav.surface`;
- `mibr-carplay111-autoshow.disabled` — GEN2 control ownership already has AutoShow disabled;
- `mibr-direct-output-fps` — merged into `mibr-carplay111-fps`;
- `mibr-direct-source-framing` — renamed/normalized to `mibr-carplay111-framing`;
- `mibr-alt111-keyframe-policy.enabled` — merged into `mibr-carplay111-keyframes.conf`;
- `mibr-carplay111-viewareas.enabled` — replaced by the explicit `0/1` value file;
- `mibr-carplay111-nav-query.enabled` — replaced by the explicit `0/1` value file;
- `mibr-carplay-autodirect.enabled` — replaced by the explicit `0/1` value file.

Legacy files may be preserved by rollback/evidence logic, but current runtime code does not treat
them as active configuration.

## /tmp-only diagnostic commands

These are not persistent settings and therefore intentionally do not get `/mnt/app/root` twins:

```text
/tmp/mibr-alt111-gen2-reacquire
/tmp/mibr-alt111-resync.enabled
/tmp/mibr-alt111-resync-arm
/tmp/mibr-alt111-keyframe-only
/tmp/mibr-alt111-show-only
/tmp/mibr-alt111-stop-only
```

They are development commands/diagnostic state, not product configuration.

Internal runtime state is likewise not a user switch, for example:

```text
/tmp/mibr-isotx2-gate.direct
/tmp/mibr-alt111-au-framing.enabled
/tmp/mibr-alt111-source-timing.enabled
/tmp/mibr-alt111-source-timing-interval-ms
```

Read-only status/telemetry includes:

```text
/tmp/mibr-alt111-gen2.status
/tmp/mibr-alt111-capture.status
/tmp/mibr-alt111-source-timing.status
/tmp/mibr-carplay111.state
/tmp/mibr-carplay111.heartbeat
/tmp/mibr-direct-remux.status
/tmp/mibr-isotx2-gate.stats
```

## Reference Java patches

`MIBR-NavIgnore.jar` and `MIBR-Most20FPS.jar` remain separate from this runtime configuration
contract. Most20FPS changes the stock DisplayManager native-navigation output path; it is not the
CarPlay source-FPS or D2 keyframe setting.

## Recovery

If a development override produces a stale/frozen VC, delete the relevant temporary file first.
A reboot automatically clears the whole temporary configuration layer and returns to persistent
settings/defaults. A fast MHI2 reboot does not necessarily reset every cluster/MOST peer; a full
vehicle bus-sleep cycle may still be required for receiver-side recovery.
