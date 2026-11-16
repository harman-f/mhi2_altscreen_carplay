# observability and display-update probe


## Logging (always on, log + status file)
- `GEN2 OBS SETUP` / `GEN2 OBS TEARDOWN`: per stream type 110/111 and whole-session, with running counters.
- `GEN2 OBS /info build`: every descriptor build; local SETUP preflights counted separately.
- `GEN2 OBS updateViewArea build`: the viewAreaIndex actually sent.
- `GEN2 OBS UI completion`: type, view, status, ack time in ms.
- Status file keys `obs_*` and `probe186_*`.

## P8 focus (owner decision 2026-11-12)
Primary test = P8: leave 110 unchanged, remove 111 from the panel list, re-add 111 with the changed zoom (`cycle`).
Procedure: set the cockpit zoom in the MIBR menu first (scaling.conf, menu shows reconnect pending), then
`echo "cycle 70 500" > /tmp/mibr-alt111-probe186`. For 15 s after a panel probe, a phone-initiated SETUP(111)
WITHOUT `features` is re-advertised from desired settings (`gen2_ensure_advert_preflight`) instead of being
withheld (-6700), so a P8 re-SETUP can pick up the new descriptor. Evidence for the four P8 questions:
1. `GEN2 OBS TEARDOWN has111=1` and `GEN2 OBS SETUP has111=1` after `cycleA`/`cycleB`.
2. No `GEN2 OBS TEARDOWN has110=1`/`full=1`, `obs_setup110_count` unchanged; visual check of the main screen and audio.
3. `GEN2 OBS /info 111 descriptor zoomFactor=..` and `GEN2 PROBE186 P8 SETUP(111) ... re-advert` (new descriptor offered); new 111 video generation in status (`stream_gen`/`codec_gen`).
4. Photo/video of the cockpit before/after (text and map size).
`info`/`infoall` stay available but are not the focus (P5: likely no-op).

## Probe (operator marker only, parked vehicle)
```
echo "cycle 70 500" > /tmp/mibr-alt111-probe186
```
Variants: `info <zoom>`, `infoall <zoom>`, `panels <zoom>`, `cycle <zoom> [gap_ms]`; zoom 70|85|100|125|150, gap 100..3000 ms.
The 111 entry is the exact GEN2 /info descriptor (desired settings) with the zoomFactor replaced; the advertised
snapshot bookkeeping is not touched. The marker is consumed on read, there is no retry, no teardown and no reconnect.
Wire shapes are unproven on iOS; a completion status only answers the transport question (G2). A rescale counts
only together with `GEN2 OBS TEARDOWN has111=1` + `GEN2 OBS SETUP has111=1` and a visible change (G3).

## Per-view scaling (r12, default OFF)
Interim GEN2-local configuration (not yet in `settings/registry.json`, so menu JAR and broker stay unchanged;
moving it into the registry with an `apply` class for stream 111 is the later integration step).

Key names follow the HTML configurator view-profile format (`MIBR_NAV_VIEW_PROFILES`, `view.<center|wide|full>.*`),
so a later configurator export (`/3` with a `geometry` section) is the same file GEN2 reads. GEN2 ignores all other
keys of that format (safeArea, carplay, native, guidance, magic line, crc32); the CRC is not checked by this interim reader.

File: `/tmp/mibr-view-profiles.conf` (volatile, wins) or `/mnt/app/root/mibr/config/cockpit/view-profiles.conf` (flash).
```
global.transition.enabled=1
global.transition.mode=cycle
global.transition.gap_ms=500
global.transition.min_interval_ms=3000
view.wide.geometry.zoom=100
view.full.geometry.zoom=85
view.center.geometry.zoom=70
```
Unit area index (`viewarea.selected`): 0 Wide, 1 Voll (`full`), 2 Center. `inherit` = value from `cockpit/scaling.conf`.

Behaviour when `global.transition.enabled=1`:
- `/info` advertises the 111 zoomFactor of the currently selected area (full reconnect always lands on the right zoom).
- After an acknowledged `updateViewArea`, GEN2 compares the area's zoom with the last advertised/sent 111 zoom.
  Same zoom: nothing else happens (only ViewArea/SafeArea). Different zoom: one P8 operation (`cycle` = 111 out, gap,
  111 in with the new zoom; `panels` = one update with the new zoom). Latest view wins; at most one run per
  `min_interval_ms`; no retry, no reconnect, 110 untouched.
- Status keys `viewscale_*`; log lines `GEN2 VIEWSCALE ...`.
`global.transition.enabled=0` or no file = r11 behaviour.
