# MU1440 right-wheel CarPlay zoom — two-phase implementation authority

Issue [#45](https://github.com/harman-f/mhi2_altscreen_carplay/issues/45), Draft [PR #36](https://github.com/harman-f/mhi2_altscreen_carplay/pull/36). Vehicle: Škoda MHI2_ER_SKG13_P4526_MU1440 / AID10. This developer branch is **NOT installed or vehicle-proven**. Existing production Parity/MOST/Source111 settings and all original OEM Java/DSI handlers are unchanged.

## V1 — user-authorized FIRST phase: *parallel* zoom only
- Every **confirmed native navigation zoom** from the physical RIGHT MFW roller can additionally queue one `changeMapZoomLevel` for the current negotiated display UUID through the existing GEN2 AirPlay sender.
- The **native zoom MUST continue unchanged**, including its overlay, BAP protocol acknowledgements/status, native map-scale mutations, original DSIKeyPanel listener fan-out and other controls. Dual native + CarPlay zoom is a **deliberate V1 result**, not a defect. No suppressing, swallowing, remapping, patching Java/LS D/J9 or global BAP(50,45).
- No alternate bindings or extra features: no KEY38/39 Omonob short/long, provider switching, VIEW, menu injection, zoom button or long-press, source toggle, left-volume encoder44 or KEY40 press. V1 recognizes right encoder rotations **only**.
- Default **OFF**. Volatile operator marker `/tmp/mibr-alt111-zoom-v1.enabled` explicitly arms the bounded parked experimental observer; removing it cancels its pending queue. This manual marker is NOT automated proof of visible VC owner: user must establish active visible 111/DIRECT before any trial. Not an autonomous production toggle. The thread when disarmed does not connect to DebugSPI.

## V1 implementation and trace provenance

### Physical / semantic signal
- Private actual 300-s dual run `native-41771151` + `vc-r2-capture-41648264`: eleven right encoder `f902/tag0x002e` records matching `(4,40,±1,0,1)` (5×+1 then 6×−1), each near `f904/tag56` and DSIBAP NavSD(50,45) event family. Observed new scale-like values: 4000,3000,2000,1500,1000,1500,2000,3000,4000,5000,7500. Some trace record order is inverted by a few milliseconds.
- `alt111_zoom_debugspi.c` accepts original, framed MLP DebugSPI bytes **receive-only** on loopback port 15001. No DebugSPI protocol bytes are sent, no logger files or OEM configs are changed. Only strict type1 0x0110 / f902 five-int right-wheel tuple and f904/tag56 with **|source timestamp delta| ≤40 ms** produce one bounded callback. Tag56 is an EMPIRICAL zoom-dependent marker, **not yet independently decoded as a particular Java method**. Neither bare right roller nor arbitrary active source111 is a sufficient V1 trigger. Parser tolerates TCP segmentation and either event ordering and consumes both parts exactly once. Its bounded buffer is 270 KiB, heap allocated in the worker.
- The live observer is in **the existing GEN2 process**, rather than a fifth service, another AirPlay session, new local UDP ingress or a second MOST/isoTX2 writer. The matched sign is enqueued to existing `alt111_zoom.c` policy under `g2_core_lock`.
- At each callback, check opt-in marker, active matching source111 generation, `g2_command_ready`, `g2_control.active/desired/shown_ack`, no reacquisition, and `g2_video.active/config_valid/consumer_primed`. The empirical Tag56 correlation is the **temporary per-detent navigation zoom discriminator**; the parked operator opt-in temporarily stands in for independent DIRECT/VC ownership. This is **not valid for autonomous V2**.
- Native scale values decrease with right +1, hence provisional +1 → `zoomDirection=0` (IN), −1 → 1 (OUT). Confirm visually on iPhone Maps/Waze/Google Maps during pilot; AirPlay send acknowledgement is not visual app proof. At most 12 pending and one in flight; 140 ms pacing. Loss of marker/socket/live GEN2 readiness clears queued events; stale completion generation is rejected.
- `libaltscreen111_gen2.c` constructs `type=changeMapZoomLevel`, `params.uuid=<active negotiated display UUID>`, `params.zoomDirection=0/1` and sends through the current AirPlay session only. No pixel zoom.
- The pre-existing speculative `alt111_zoom_route_map_action()` function is preserved for a possible V2 but **has no V1 caller**. Do NOT call it from this probe or enqueue the same detent from another input path.

### Tests / gates
`bash tools/test_alt111_zoom_host.sh` now includes the original twelve left/right tuple policy regressions, the 11 measured native zoom signed scale sequence in the route policy tests, and `alt111_zoom_debugspi_test.c`: precise sanitized eleven timestamp pairs, f904-before-f902 ordering, split MLP/TCP, invalid/left inputs, wrong tag, stale pair, duplicate marker and 32-bit clock rollover. QNX build through `tools/build_altscreen111_gen2.sh` links the new matcher; do not claim vehicle-success from successful CI.
No private raw vehicle files or OEM binaries may be committed publicly.

## V1 acceptance: parked vehicle, separate authorization required
1. Confirm stock native 110 map: right +/- still changes only native scale with marker OFF.
2. Confirm actually visible 111/DIRECT, GEN2 source111 live, marker OFF: both sides keep previous behavior; **no new zoom**.
3. Explicitly arm marker while parked and visibly in CarPlay map. Right +/- → native OEM zoom still occurs AND AirPlay `changeMapZoomLevel` submit/response and visible CarPlay map change are separately observed, one per eligible signed tick after paced dispatch.
4. Open VC menu / Radio / Telephone with source111 still live: right-wheel scroll must not produce correlated zoom callback or CarPlay zoom; left volume must not be affected. If tag56 also occurs in this context, STOP and investigate rather than claim validated focus discrimination.
5. Remove marker, stop/restart session, drop DebugSPI or return STOCK: no new observer zoom and no duplicate queued events. Verify no HMI instability and rollback to prior original artifact.
6. Log all failures including absent DebugSPI service, no Tag56, wrong physical direction or rejected AirPlay commands. Re-enable only after diagnosis.

## V2 — deferred EXCLUSIVE zoom, NOT in V1
After V1 has actual app-level zoom proof and exact-target MU1440 native MapScale callsite + independent VC focus/actual DIRECT owner provenance are verified, implement a **separate** reversible semantic branch that only skips the native map-scale side effect while preserving BAP ACK/status/other handlers. Do not skip `super` or block all BAP(50,45) based on this correlation. User explicitly postponed this stage.

## Omonob and portability
Omonob Free790 uses `DSIKeyPanelDispatcher.updateKey2` for KEY38/39 on MU1440: this does **not** decode the actual physical right encoder (4/40). We reuse the idea of semantic AirPlay zoom commands and the existing target-native libaltscreen111 sender, **not** Omonob's KEY38/39 mapping, extra feature bindings or its third-party JAR. Audi MHI2Q `ScreenCombiBAPListener` is only a comparator, never a drop-in MU1440 class.
