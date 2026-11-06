# updateDisplayPanels native scaling proof of concept

Status: **Experimental source only. Not built, deployed, or vehicle-proven.**
Target: exact MU1440 / Stream 111 on a parked vehicle.
Branch: `experiment/update-display-panels-scale-poc-20261106`.

## Scope

This experiment tests whether iOS updates native display scaling after receiving an
`updateDisplayPanels` command on an **existing** AirPlay/CarPlay session.

This is **not** the previously verified live `updateViewArea` implementation.
It neither changes the permanent scaling preferences nor attempts a USB,
iAP2, AirPlay or head-unit reconnect. It does not change Type 110.

The iOS 26.1 `CARSession` handler is known to update display-plugin /
video-stream associations. It does **not** prove the incoming `zoomFactor`
or physical dimensions will be adopted. iOS 27 differs internally; this
POC is designed to produce actual evidence rather than assuming support.

## Code and safety boundary

- Only the existing GEN2 `libaltscreen111_gen2.c` runtime source is changed; supporting diagnostic shell scripts and the volatile-path allowlist are included.
- The currently advertised, successful cluster `/info` descriptor is retained
  in memory. Both display UID and the original `initialVideoStreams` array
  are reused in the `updateDisplayPanels` command. The video stream list
  **must not be omitted**, because the iOS 26.1 handler replaces it.
- Pixel width/height, screen UUID and stream identifiers are unchanged.
- `ZOOM=N` varies only `zoomFactor`. `PHYSICAL=PXX` varies only
  `widthPhysical`/`heightPhysical`; the prior zoom remains unchanged.
- An active, confirmed Type-111 session, an acknowledged `showUI` and an
  idle normal command queue are mandatory.
- One in-flight command only; the GEN2 command worker pauses ordinary
  commands while the experimental asynchronous completion is outstanding.
- A three-second completion timeout releases the worker. Session teardown
  invalidates the probe and discards the retained descriptor. A late callback
  cannot overwrite the current result.
- No changes to the broker, persistent setting definitions, menu, installer or firmware. The three new volatile diagnostic paths are declared in the registry path allowlist for publication auditing.
  No process kill or forced reconnect.
- All controls are volatile under `/tmp`; the POC starts **disabled**.

The result file always says `visual_effect=UNKNOWN`. The AirPlay send
completion indicates acceptance of a command, not that iOS rendered a
different density.

## Operator control (QNX ksh)

Use the helper `runtime/diagnostics/gen2_panel_scale_poc.sh` from the
source tree, or copy it alongside the installed GEN2 diagnostic scripts.
Run with `/bin/ksh` (the GitHub Contents API does not preserve executable
file mode when creating a new file).

```sh
/bin/ksh gen2_panel_scale_poc.sh on
/bin/ksh gen2_panel_scale_poc.sh zoom 70
/bin/ksh gen2_panel_scale_poc.sh status
/bin/ksh gen2_panel_scale_poc.sh logs

/bin/ksh gen2_panel_scale_poc.sh zoom 150
/bin/ksh gen2_panel_scale_poc.sh status
/bin/ksh gen2_panel_scale_poc.sh physical P20
/bin/ksh gen2_panel_scale_poc.sh status
/bin/ksh gen2_panel_scale_poc.sh collect
/bin/ksh gen2_panel_scale_poc.sh off
```

The existing HMI switch **Logs auf SD-Karte** remains unchanged. The
`logs` subcommand acts as a one-click log viewer, and `collect`
reuses `gen2_collect_logs.sh`, including the new POC result. Its
default output is on internal storage (/mnt/app/root/mibr-gen2-reports);
MIBR_REPORT_DIR may override the destination to a verified writable SD mount.
The
production HMI is deliberately not extended for a protocol proof of concept.

Direct one-shot marker format for testing without the helper:

```sh
touch /tmp/mibr-alt111-panel-poc.enabled
echo ZOOM=125 > /tmp/mibr-alt111-panel-poc.request
cat /tmp/mibr-alt111-panel-poc.status
```

Allowed values: `ZOOM=70|85|100|125|150` or
`PHYSICAL=BASE|P20|P30|P50`.

## Evidence required

1. Baseline: working, connected iPhone and moving VC map with unchanged
   Type-111 session; note active iOS version and existing scaling.
2. First probe: resend the same native zoom; capture response and stream
   generation. No crash, dropout or display loss is acceptable.
3. A/B zoom: e.g. 70 -> 150; compare photo and source H.264 coded dimensions,
   UI element sizes and Type-111/110 setup and teardown.
4. A/B physical size separately: BASE -> P20, with the prior zoom unchanged.
5. If ignored, classify as `ACK_EFFECT_UNKNOWN` or `NO_VISIBLE_CHANGE` based
   on **actual** visual/capture evidence. Do not infer scale effectiveness
   from the callback or updated status file alone.
6. After a rejected or stale session, use `off` and the existing
   controlled stock handback procedure. Do not blindly restart
   `smartphone_integrator` or `dio_manager`.

## Build gate

From repository root, with the pinned QNX toolchain and test prerequisites:

```sh
python3 tools/generate_alt111_settings.py --check
bash tools/test_installed_gen2_host.sh
QCC=arm-unknown-nto-qnx6.5.0eabi-gcc bash tools/build_altscreen111_gen2.sh build/gen2/libaltscreen111.so
```

Keep the resulting ELF as an **experimental artifact**. Do not include it
in the normal beta installer/release until host, cross-build, firmware hash,
vehicle/stream and safe-recovery tests pass.

## Research pointers

- `docs/research/carplay/CARPLAY_CLUSTER_CONFIGURATION_INDEX_IOS26_7_1_2026-10-01.md`
- iOS 26.1 `CARSession.mm`, `_sessionUpdatesQueue_handleDisplayPluginsUpdateWithParameters:`
- iOS 27 CarKit / AirPlaySender diffs: `zoomFactorByDisplayIndex`,
  `DisplayConfigurationChanged`, `CRFetchScaledDisplaysForDisplayScaleModeV2`.
