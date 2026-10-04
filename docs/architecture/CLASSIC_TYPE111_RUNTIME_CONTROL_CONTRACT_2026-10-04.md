# Classic Type-111 runtime-control contract — MU1440 / AID10

Status: **vehicle-test candidate contract**  
Target: **MHI2_ER_SKG13_P4526_MU1440 + AID10**  
Scope: classic CarPlay auxiliary display / ScreenAlt / stream type 111.  
Media/Now Playing, CarPlay Ultra/NextGen, PassengerDisplay, GaugeCluster, HEVC, Enhanced Siri,
raw AirPlay feature-bit experiments, HID/input and appearance experiments are explicitly out of scope.


## Validated vehicle-test candidate

Final audited source:

```text
repository=harman-f/mhi2_altscreen_carplay
branch=work/source-timestamp-framing-v1
HEAD=bbfa20cb11c574d14b3cb607731ea20ccfb9fef8
PR=#10 (draft; not for merge before vehicle validation)
```

All four required workflows are green on that exact HEAD:

```text
Publication integrity audit              37183996901  success
Build experimental GEN2 AltScreen        37183996904  success
Build unstripped MU1440 direct-ts-remux  37183996910  success
Build MU1440 framing-v1 candidate overlay 37183996909 success
```

Vehicle artifact:

```text
Actions artifact ID=11296122415
artifact name=mu1440-framing-v1-candidate
Actions archive digest=sha256:db352311fa0e0dc89b5f8ada06c801b1878466c75cefeabc24e8a1ad01119465

inner vehicle ZIP=MHI2_AltScreen_MU1440_FRAMING_V1_CANDIDATE.zip
inner vehicle ZIP SHA256=2a09a8c2c03045f36db6e5e71fc9f03c3c6728fc764623190c35c1ed2b95de21
GEN2 libaltscreen111.so SHA256=8cccf1cb1764952acd973cbb4f881cfd70f3312e7f6a29cdef7fec930c83d25c
direct-ts-remux SHA256=3f0e730523bd290608dc13e186baa962eeb9c46f117d4d4976be523c0cd94c09
```

Final package audit additionally verified:

- outer and inner ZIP digests;
- `PAYLOAD.sha256` and `PACKAGE-SHA256SUMS.txt` completely;
- every shipped shell script with `bash -n`;
- no ZIP path traversal;
- ARM/QNX ELF identity for GEN2, remux and bundled SHA helper;
- required Classic111 strings in the compiled GEN2 binary;
- absence of the retired bit26, old nav-query marker and old D2 marker from the GEN2 binary;
- installer exact-target guard on the MU1440 `libairplay.so` SHA;
- backup-before-mutation, orphan-backup refusal and active-candidate mismatch refusal;
- exact one-to-one rollback coverage for all 41 backed-up binaries, helpers, settings and legacy-state files.

The only legacy marker names still present in the vehicle package are explicit installer cleanup lines
for stale `/tmp` state; they are not active configuration.

## 1. One configuration model

All user-facing settings use the same two-layer precedence:

```text
/tmp/<basename>                   temporary override; highest priority; disappears on reboot
/mnt/app/root/<basename>          persistent override
compiled/configured default       used when neither file exists
```

The basename is identical in both layers. A temporary value can therefore explicitly override a
persistent value in either direction; e.g. persistent FPS 30 + temporary FPS 20 means 20 now and 30
again after reboot.

One-shot actions are intentionally different. They live only in `/tmp` and are not persistent state.

## 2. Final Classic Type-111 settings

| Setting | Basename | Default | Values / content | Apply class |
| --- | --- | --- | --- | --- |
| AltScreen master | `mibr-carplay111-enabled` | `1` | `0/1` | reconnect |
| Auto-Direct | `mibr-carplay-autodirect` | `1` | `0/1` | runtime |
| FPS | `mibr-carplay111-fps` | `30` | `20/25/30/40` | reconnect |
| local framing | `mibr-carplay111-framing` | `raw` | `raw/m1au` | bridge |
| video pacing | `mibr-carplay111-video.conf` | pace=1, pace_buffer=3 | config | bridge |
| D2 keyframes | `mibr-carplay111-keyframes.conf` | see §5 | config | live |
| sourceVersion | `mibr-carplay111-sourceversion` | `1005.8.1` | `stock` or dotted version | reconnect |
| raw UI URL | `mibr-carplay111-url` | `auto` | `auto` or exact URL | presentation |
| advertised UI URLs | `mibr-carplay111-ui-urls.conf` | three classic URLs | up to url0..url7 | reconnect |
| navigation composition | `mibr-carplay111-nav.conf` | see §3 | config | presentation |
| display descriptor | `mibr-carplay111-display.conf` | 1010×376, 200×74 mm, stock candidate UUID | config | reconnect |
| ViewAreas | `mibr-carplay111-viewareas.conf` | two areas | config | definition=reconnect, selection=live |

Apply classes are semantic contract metadata:

- **live**: the running GEN2 process re-reads the value.
- **presentation**: bounded same-session presentation reacquire: stopUI → showUI(new URL) → forceKeyFrame.
- **bridge**: restart only the local direct bridge/remux path.
- **reconnect**: disconnect/reconnect CarPlay so the next `/info` / projection negotiation consumes it.
- **runtime**: Auto-Direct supervisor can be stopped/started without restarting CarPlay.

Do **not** hard-restart `smartphone_integrator` or `dio_manager` as an apply mechanism. Vehicle
testing showed repeated hard restarts can damage/exhaust the service stack. If a reconnect-class
setting does not renegotiate cleanly, use the normal vehicle/MHI reboot recovery boundary rather than
repeated process kills.

## 3. URL and navigation

Raw URL override:

```text
/tmp/mibr-carplay111-url
/mnt/app/root/mibr-carplay111-url
```

`auto` means GEN2 builds the URL from `mibr-carplay111-nav.conf`. Any valid non-auto string
containing a URL scheme separator is used verbatim for `initialURL` and showUI.

Default navigation config:

```ini
query=0
surface=base
showETA=yes
showSpeedLimit=user
showCompass=user
maneuverLayout=none
```

Supported surfaces:

```text
base             maps:/car/instrumentcluster
map              maps:/car/instrumentcluster/map
instructioncard  maps:/car/instrumentcluster/instructioncard
```

The default advertised URL capability list is:

```ini
url0=maps:/car/instrumentcluster
url1=maps:/car/instrumentcluster/map
url2=maps:/car/instrumentcluster/instructioncard
```

The list is receiver capability metadata (`altScreenSuggestUIURLs`), not an immediate showUI command.

## 4. Display descriptor

Default:

```ini
widthPixels=1010
heightPixels=376
widthPhysical=200
heightPhysical=74
uuid=b7e6c5a0-2222-4000-8000-000000000002
```

The descriptor is re-read at the next `AirPlayCopyServerInfo()` negotiation. Type remains 111 and is
not user-configurable.

## 5. D2 receiver-requested keyframe recovery

Default:

```ini
enabled=1
event_delay_ms=250
min_gap_ms=1000
watchdog_ms=1000
```

This controls additional receiver-originated `forceKeyFrame` recovery requests. It does **not**
change the iPhone encoder's native GOP/IDR cadence. `watchdog_ms=0` disables only the periodic
watchdog while retaining event-driven behavior when enabled.

## 6. FPS and source timing

`mibr-carplay111-fps` is deliberately one user setting. It controls both:

1. the Type-111 `maxFPS` announced to iOS; and
2. the direct-output pacing target.

The diagnostic timing path remains independent:

- GEN2 measures actual complete Stream-111 AU arrival cadence with `CLOCK_MONOTONIC`;
- telemetry exposes measured source FPS, arrival intervals and source bitrate;
- M1AU v1 preserves the exact eight raw timestamp bytes carried in the Stream-111 header;
- the remux reports M1AU sequence, raw timestamp values/deltas, input/remux/MOST bitrate,
  pacing, jitter, EAGAIN and backpressure.

The eight source timestamp bytes are still semantically unproven. They therefore **do not drive
PTS/PCR**. PTS/PCR remain the existing CFR-derived path for this candidate.

## 7. Two ViewAreas with two SafeAreas

Canonical config:

```text
mibr-carplay111-viewareas.conf
```

Candidate defaults:

```ini
enabled=1
count=2
initial=0
transition_ms=0

view0.x=0
view0.y=0
view0.w=1010
view0.h=376
view0.safe.x=0
view0.safe.y=0
view0.safe.w=1010
view0.safe.h=376
view0.adjacent=1

view1.x=0
view1.y=0
view1.w=1010
view1.h=376
view1.safe.x=0
view1.safe.y=58
view1.safe.w=1010
view1.safe.h=248
view1.adjacent=0
```

Interpretation:

- ViewArea 0 = **MAP_FULL**
- ViewArea 1 = **GAUGE_REDUCED**
- the Area-1 SafeArea `0,58,1010,248` is a **vehicle-calibration candidate**, not final geometry.

Changing the ViewArea definitions requires a fresh CarPlay negotiation. Switching between already
advertised indices is live through `updateViewArea`.

The live action helper writes:

```text
/tmp/mibr-alt111-viewarea-request
```

with `0` or `1`. GEN2 consumes it and drives the normal serialized control path.

The implementation also models adjacency `0 ↔ 1`. On targets where the optional CFLite
`CFNumberCreate` symbol is available, GEN2 serializes `adjacentViewAreas=[1]` or `[0]` in the
descriptor/update command. If that optional symbol is absent, GEN2 logs this and keeps the rest of
the two-ViewArea path active rather than failing the whole candidate.

## 8. Helpers shipped in the vehicle candidate

```text
direct_autodirect.sh
direct_fps.sh
direct_source_mode.sh
gen2_video.sh
gen2_keyframes.sh
gen2_sourceversion.sh
gen2_enabled.sh
gen2_display.sh
gen2_url.sh
gen2_ui_urls.sh
gen2_nav_config.sh
gen2_viewareas.sh
gen2_safearea.sh      compatibility wrapper for ViewArea-0 SafeArea
viewarea_mode.sh      compatibility wrapper
```

Bare test-oriented commands write the temporary layer where applicable. Persistent changes require
an explicit `persist` form. The future HMI broker must call the same semantic backend rather than
create a second settings store.

## 9. HMI contract

Future HMI semantics:

```text
Testen       -> write /tmp
Speichern    -> write /mnt/app/root
Test löschen -> remove /tmp
```

For every setting the broker should expose:

```text
default
persistent
temporary
effective
source
apply_class
```

The Java HMI should not remount `/mnt/app` itself. A broker/CLI layer owns validation, atomic
replace, sync and RW/RO remounting.

## 10. Explicitly removed / excluded

Removed from active Classic-111 configuration:

- bit26 force-on/force-off: bit26 is AudioAES_128_MFi_SAPv1, not AlternateScreen;
- bit37 CarPlayControl: connection-initiation protocol, not the Type-111 display gate;
- old `url-map.enabled`, `autoshow.disabled`, split output-FPS marker,
  old keyframe-policy marker, old ViewArea/query marker files.

Not in this vehicle candidate:

- Media / Now Playing / mapsMediaCarousel;
- GaugeCluster, DataProtocol, PassengerDisplay / Ferrite / Ultra;
- Enhanced Siri, HEVC;
- HID/input feature advertisement;
- appearance/corner-mask experiments;
- raw enabledFeatures override;
- source timestamp → PTS/PCR mode.

## 11. Tomorrow's controlled baseline

Do not start by changing multiple variables. Baseline:

```text
AltScreen master 1
Auto-Direct 1
FPS 30
framing raw
pace 1
pace_buffer 3
sourceVersion 1005.8.1
URL auto
nav query 0 / surface base
ViewArea 0 initial
D2 1 / 250 / 1000 / 1000
PTS/PCR CFR
```

Then test one variable at a time, with M1AU and ViewArea switching as the first controlled A/B axes.
