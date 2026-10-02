# Advanced runtime switches and hidden feature flags

This is the consolidated reference for runtime switches that otherwise live only in scripts or in
the GEN2 native source.

## MU1440 reference defaults

- coded-frame/map canvas: **1010x376**
- `MIBR-NavIgnore.jar`: active
- `MIBR-Most20FPS.jar`: active
- Auto-Direct: persistent
- GEN2 D2 source-keyframe recovery: persistent
- D2 source-IDR watchdog: **1000 ms**
- D2 minimum keyframe-request gap: **1000 ms**
- `turns` / `suggestUI` event debounce: **250 ms**

## Persistent controls under `/mnt/app/root`

| Path | Meaning |
| --- | --- |
| `/mnt/app/root/mibr-carplay-autodirect.enabled` | Persistent Auto-Direct enable. |
| `/mnt/app/root/mibr-alt111-keyframe-policy.enabled` | Persistent D2 keyframe policy. Default on the MU1440 reference deployment. |
| `/mnt/app/root/mibr-carplay111-viewareas.enabled` | Enable the experimental ViewArea-capable descriptor. |
| `/mnt/app/root/mibr-carplay111-safearea.conf` | SafeArea geometry configuration. |
| `/mnt/app/root/mibr-carplay111-autoshow.disabled` | Disable automatic showUI behavior. |
| `/mnt/app/root/mibr-carplay111-url-map.enabled` | Prefer `maps:/car/instrumentcluster/map` over the bare base URL. |
| `/mnt/app/root/mibr-carplay111-bit26.force-on` | Force AirPlay root feature bit 26 on. Diagnostic A/B only. |
| `/mnt/app/root/mibr-carplay111-bit26.force-off` | Force AirPlay root feature bit 26 off. Diagnostic A/B only. Never set both bit26 markers. |
| `/mnt/app/root/mibr-carplay111-nav-query.enabled` | Enable navigation query parameters. |
| `/mnt/app/root/mibr-carplay111-nav.surface` | Navigation surface selector: base, map or instructioncard. |
| `/mnt/app/root/mibr-carplay111-nav.showETA` | ETA preference: yes, no or user. |
| `/mnt/app/root/mibr-carplay111-nav.showSpeedLimit` | Speed-limit preference: yes, no or user. |
| `/mnt/app/root/mibr-carplay111-nav.showCompass` | Compass preference: yes, no or user. |
| `/mnt/app/root/mibr-carplay111-nav.maneuverLayout` | Maneuver alignment: none, leftAligned, rightAligned or topAligned. |

Use the shipped helpers where possible:

```sh
/mnt/app/root/altscreen-u2/scripts/gen2_keyframes.sh status
/mnt/app/root/altscreen-u2/scripts/gen2_keyframes.sh on
/mnt/app/root/altscreen-u2/scripts/gen2_keyframes.sh off

/mnt/app/root/altscreen-u2/scripts/gen2_nav_config.sh status
```

`gen2_keyframes.sh on` is persistent across reboot. `session-on` is the explicit volatile variant.

## Volatile `/tmp` controls

| Path | Meaning |
| --- | --- |
| `/tmp/mibr-alt111-keyframe-policy.enabled` | Session-only D2 enable; also compatibility mirror for older vehicle-tested GEN2 binaries. |
| `/tmp/mibr-alt111-gen2-reacquire` | One-shot same-stream reacquire: stopUI -> showUI -> updateViewArea -> forceKeyFrame. |
| `/tmp/mibr-alt111-resync.enabled` | Enable manual Candidate-D same-stream IDR recovery. |
| `/tmp/mibr-alt111-resync-arm` | One-shot manual resync arm. |
| `/tmp/mibr-alt111-keyframe-only` | Diagnostic forceKeyFrame-only command. |
| `/tmp/mibr-alt111-show-only` | Diagnostic showUI-only command. |
| `/tmp/mibr-alt111-stop-only` | Diagnostic stopUI-only command. |
| `/tmp/mibr-alt111-url-mode` | Volatile URL-mode diagnostic state. |
| `/tmp/mibr-isotx2-gate.direct` | DisplayManager gate is in DIRECT ownership mode. Normally controlled by Auto-Direct. |

Read-only state/telemetry includes:

```text
/tmp/mibr-alt111-gen2.status
/tmp/mibr-alt111-capture.status
/tmp/mibr-alt111-source-timing.status
/tmp/mibr-carplay111.state
/tmp/mibr-carplay111.heartbeat
/tmp/mibr-direct-remux.status
/tmp/mibr-isotx2-gate.stats
```

## Navigation composition profiles

```sh
gen2_nav_config.sh use stock
gen2_nav_config.sh use base-rich
gen2_nav_config.sh use base-right
gen2_nav_config.sh use base-left
gen2_nav_config.sh use base-top
gen2_nav_config.sh use map-rich
gen2_nav_config.sh use map-clean
gen2_nav_config.sh use maneuver-only
```

`use` persists the profile and applies it through the serialized same-stream transition ending in a
fresh keyframe request. It does not deliberately rebuild Stream 111.

## SafeArea / ViewArea

SafeArea operates inside the fixed **1010x376** reference canvas. Do not use SafeArea to reinterpret
the physical 1280x480 cluster panel as the coded video contract.

Development helper:

```sh
runtime/navigation/gen2_safearea.sh status
runtime/navigation/gen2_safearea.sh full
```

Custom SafeArea values remain layout/target specific until vehicle-calibrated.

## Direct Stream-111 frame pacing

The direct remuxer has an optional low-cost packet-level pacer. It does **not** decode or re-encode
H.264. A small reader queue absorbs short arrival-time jitter and the mux/write side releases access
units on a monotonic output clock.

Reference settings:

```text
DIRECT_OUTPUT_FPS=30
DIRECT_PACE=1
DIRECT_PACE_BUFFER=3
```

Runtime helper:

```sh
/mnt/app/root/altscreen-u2/scripts/direct_fps.sh status
/mnt/app/root/altscreen-u2/scripts/direct_fps.sh 30
/mnt/app/root/altscreen-u2/scripts/direct_fps.sh 25
/mnt/app/root/altscreen-u2/scripts/direct_fps.sh 20
/mnt/app/root/altscreen-u2/scripts/direct_fps.sh 40
/mnt/app/root/altscreen-u2/scripts/direct_fps.sh default
```

The switch persists the same requested rate for both layers:
`/mnt/app/root/mibr-direct-output-fps` controls the direct remux/pacer and
`/mnt/app/root/mibr-carplay111-fps` changes the maxFPS advertised by GEN2 on subsequent `/info`
responses. The active Direct-VC bridge is restarted immediately. A currently connected CarPlay
session keeps the rate it already negotiated, so after changing the source maxFPS reconnect CarPlay
before judging the matched source/sink result. 30 fps remains the reference default; 40 fps is an
explicit diagnostic option. No compressed H.264 P-frames are discarded to fake a lower frame rate.

Source timing telemetry can be enabled with the shipped configuration:
`ALTSCREEN111_TIMING_DEBUG=1`, `ALTSCREEN111_TIMING_INTERVAL_MS=1000` and
`DIRECT_TELEMETRY=1`. GEN2 then publishes measured accepted-AU cadence, source H.264 bit rate and
the two **raw/uninterpreted** Stream-111 timestamp words in
`/tmp/mibr-alt111-source-timing.status`. Auto-Direct correlates these with
`/tmp/mibr-direct-remux.status` and persists a per-session `telemetry.tsv` plus stable FPS-change
events.

This is observation only: Apple timestamp words do not yet drive PTS/PCR. See
`docs/testing/MU1440_SOURCE_TIMING_TELEMETRY.md`.

## Most20FPS

The standalone one-class Java patch is now a reference default for the exact MU1440/AID10-class target.

```text
MIBR-Most20FPS.jar
SHA-256 dbd45609fe4ba69948d39e9e649b224484f680f6aa7934b68c261a4d360ea5bb
```

Vehicle capture proved real stock DisplayManager H.264/MPEG-TS output changing from **10 fps to 20 fps**
at 1010x376. The five-frame GOP remains, so native I/IDR cadence changes from about 0.5 s to about 0.25 s.

This is separate from the GEN2 CarPlay `forceKeyFrame` recovery policy. `MIBR-NavIgnore.jar` owns the
navigation/CarPlay arbitration classes; `MIBR-Most20FPS.jar` owns only `ChangeDataRateSequence.class`.
Do not reintroduce the historical combined `NavActiveIgnore.jar` alongside the split pair.

## Bit26

Bit26 is an AirPlay capability A/B switch, not an AltScreen mode bit. The reference default is
**stock/unforced**. Force-on and force-off exist only for receiver capability experiments.

## Recovery note

If a development switch leaves the VC stale/frozen, return the gate to STOCK and disable the
experimental switch first. A fast MHI2 reboot does not necessarily reset every cluster/MOST/DSI peer
state; the reference vehicle has required a full vehicle bus-sleep cycle to recover a missing dynamic
H.264/MOST display.
