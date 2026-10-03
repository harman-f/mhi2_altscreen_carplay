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
- AirPlay receiver compatibility persona (`sourceVersion`): **1005.8.1**

## Persistent controls under `/mnt/app/root`

| Path | Meaning |
| --- | --- |
| `/mnt/app/root/mibr-carplay-autodirect.enabled` | Persistent Auto-Direct enable. |
| `/mnt/app/root/mibr-alt111-keyframe-policy.enabled` | Persistent D2 keyframe policy. Default on the MU1440 reference deployment. |
| `/mnt/app/root/mibr-carplay111-keyframes.conf` | Live D2 timing control: event delay, minimum request gap and watchdog interval. |
| `/mnt/app/root/mibr-carplay111-sourceversion` | Optional `sourceVersion` persona override. Missing file defaults to `1005.8.1`; value `stock` preserves the stock 210.81 value. |
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

### Live D2 keyframe timing

The current defaults are still the vehicle-tested D2 policy, but they are no longer compile-time-only.
GEN2 reads the persistent control file live:

```text
/mnt/app/root/mibr-carplay111-keyframes.conf

event_delay_ms=250
min_gap_ms=1000
watchdog_ms=1000
```

Use the helper instead of editing the file by hand:

```sh
# current defaults
/mnt/app/root/altscreen-u2/scripts/gen2_keyframes.sh timing 250 1000 1000

# keep event-driven recovery but disable the periodic source-IDR watchdog
/mnt/app/root/altscreen-u2/scripts/gen2_keyframes.sh timing 250 1000 0

# restore compiled fail-safe defaults by removing the override
/mnt/app/root/altscreen-u2/scripts/gen2_keyframes.sh timing-default
```

Accepted ranges are 0–5000 ms for event delay and 0–60000 ms for minimum gap/watchdog.
`watchdog_ms=0` disables only the watchdog. A malformed or out-of-range file fails safely to
250/1000/1000. Changes are consumed live; no CarPlay reconnect or unit reboot is required.

These values govern **additional receiver-requested `forceKeyFrame` recovery**, not the iPhone's
native GOP or autonomous IDR cadence.

### AirPlay `sourceVersion` persona

GEN2 now advertises `sourceVersion=1005.8.1` by default on its modified server-info path. This is
the exact AirPlaySender generation associated with the current iOS 27.2 beta-2 research target and
is treated only as a compatibility persona; it is **not** the AltScreen capability gate.

Optional persistent diagnostic overrides:

```sh
echo stock    > /mnt/app/root/mibr-carplay111-sourceversion   # preserve MU1440 stock 210.81
echo 950.7.1  > /mnt/app/root/mibr-carplay111-sourceversion   # historical compatibility persona
echo 1005.8.1 > /mnt/app/root/mibr-carplay111-sourceversion   # current development persona
```

Any well-formed numeric dotted version is accepted; malformed values fall back to `1005.8.1`.
Changing this value requires a fresh CarPlay connection so the iPhone consumes a new `/info`
response. The direct AltScreen contract remains `"altScreen"` in `enabledFeatures` followed by
ScreenAlt/type 111.

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

The historical bit26 A/B mutates the **global AirPlay root `features` mask**. It is **not** an
AltScreen capability switch.

Public Apple-derived AirPlay headers identify root bit 26 (`0x04000000`) as
`AudioAES_128_MFi_SAPv1`. MU1440 stock already advertises this bit, so force-on is normally a
no-op. Force-off removes a normal MFi-SAPv1 audio-encryption capability and can perturb or break an
otherwise valid CarPlay baseline.

The canonical AltScreen gate is instead the SETUP feature token `"altScreen"` in
`enabledFeatures`, followed by the Type-111 / `ScreenAlt` transport.

Therefore:

- leave bit26 **stock/unforced** for normal use;
- do not use bit26 to test whether AltScreen is enabled;
- retain the force-on/off markers only as a legacy/reference capability diagnostic;
- prefer `altScreen` / `viewAreas` negotiation controls for auxiliary-screen experiments.

## Recovery note

If a development switch leaves the VC stale/frozen, return the gate to STOCK and disable the
experimental switch first. A fast MHI2 reboot does not necessarily reset every cluster/MOST/DSI peer
state; the reference vehicle has required a full vehicle bus-sleep cycle to recover a missing dynamic
H.264/MOST display.
