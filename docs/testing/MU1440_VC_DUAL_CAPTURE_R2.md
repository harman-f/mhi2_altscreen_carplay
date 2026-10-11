# MU1440 VC dual-observer R2 — implementation phase 1 (2026-10-11)

**Goal:** correlate physical wheel/key input and six OEM cockpit DSI interfaces without conflating DebugSPI HK events with five-int encoder tuples, TCP recv chunks with DSI method boundaries, or cockpit native menus with HU menus. No J285 injection, input remap, MOST/video mutation, source-111 changes or emulator.

## Actual architecture

- Existing `mibr-keypanel-native` v1.4 remains UNMODIFIED: receive-only Java DebugSPI `127.0.0.1:15001`; `native-<PID>/combined.log` interleaves human `NOTE` and OEM HK `EVENT` with QNX monotonic milliseconds; retains full `debugspi-original.bin`, text and report. v1.3 ran on vehicle. v1.4 QNX CI/synthetic capture validated; live v1.4 result needs checking.
- Latest `tools/decode_keypanel_f902.py` (already in main) can extract five signed fields from narrowly selected `0x0110/f902/0x002e` DebugSPI records. Its tag is NOT a proven DSI method number. Validate physical left/right, direction and 32-bit clock relationship with human notes, before claiming `updateEncoder2` provenance.
- OEM `DSITracer.jar`, `DSITracer-VW-H29.319.93.jar`, `DSITracer-clientData.bin` are present per live R1. `DSITRACER_ACTIVATED=no`; actual HMI bootclasspath does NOT include tracer jars. `traceConfig.properties` contains commented candidates for six interfaces and `use.appender=client`, port 1800, external control port 1797. Port-1800 handshake and even active endpoint remain UNVALIDATED.
- New `mibr-dsi-rx` is a SEPARATE receive-only loopback TCP probe of `127.0.0.1:1800`. It writes verbatim `dsi-client-original.bin` (16 MiB cap), `dsi-chunks.tsv` (monotonic timestamp, offset, receive size), `dsi-report.txt` in an existing approved SD directory. It **never sends any network bytes**. No proprietary client-protocol decoder is claimed. Zero bytes, refused connect or peer close is INCONCLUSIVE.

```
physical keys / wheels -> OEM Java -> DebugSPI :15001 -> existing native keypanel logger
                                         |                NOTES + HK + 0xf902 raw
                                         |
HU DSI calls + callbacks -> OEM DSITracer -> client :1800 -> new native raw collector
                                         |                binary bytes + recv clock
                                         +------ offline correlation --------+
```

## Scope and activation (staged only)

`tools/prepare_vc_trace_r2.py ORIGINAL_lsd.sh ORIGINAL_traceConfig.properties NEW_EMPTY_OUTPUT_DIR` operates **only on downloaded ORIGINAL files on a PC**; produces `lsd.sh.STAGED_NOT_FOR_INSTALL`, `traceConfig.properties.STAGED_NOT_FOR_INSTALL`, `original-sha256.txt`, and `review.diff`. Hard checks demand the existing `MIBR-NavIgnore.jar` and `MIBR-Most20FPS.jar` bootclasspath additions, original OEM tracer clauses, client appender, normal control extension and disabled KeyPanel emulator. Staged diff flips the existing `DSITRACER_ACTIVATED=no` to yes and uncomments ONLY these six full-scope rows:

```properties
org.dsi.ifc.carkombi.DSICarKombi=full
org.dsi.ifc.bap.DSIBAP=full
org.dsi.ifc.kombifastlist.DSIFastListScrollingAudio=full
org.dsi.ifc.kombifastlist.DSIFastListScrollingNavigation=full
org.dsi.ifc.kombifastlist.DSIFastListScrollingTelephone=full
org.dsi.ifc.kombipictureserver.DSIKombiPictureServer=full
```

Do not enable all DSI scopes globally. **DO NOT install the staged files on the car yet.** The OEM script says `Do not change manually. Used by GEM.` GEM-controlled enablement / reversible vehicle method must be verified, alongside correct client protocol, before bench use. Do not connect to control port 1797 or turn on `DSIKeyPanelEx`. Backup/restore the complete active production files and their hashes before any approved test; preserve NavIgnore/Most20FPS and source-111/Parity state. Parked testing only.

## Build + host regression

```sh
cc -std=c99 -Wall -Wextra -Werror -O2 src/native/vc_trace/mibr_dsi_rx.c -o tests/vc-trace/mibr-dsi-rx-host
python3 tests/vc-trace/test_r2.py
```

Host test verifies receive-only, exact raw payload across multiple socket sends, per-recv monotonic index, no overwrite, staging hard guards and chronology. Offline host PASS in initial draft. For actual QNX ARMv7 run `sh tools/build_vc_dsi_rx.sh` **in the same pinned QNX 6.5 toolchain container** as `tools/build_keypanel_native.sh`. Linux host executable must never be deployed. QNX compiler/ELF + physical port-1800 test still PENDING.

When both collectors run on the same QNX kernel, `tools/merge_vc_r2_timeline.py combined.log dsi-chunks.tsv --out R2_TIMELINE.tsv` interleaves `KEYPANEL_NOTE/EVENT/RELATED` and `DSI_RECV_CHUNK` using `CLOCK_MONOTONIC`. A socket recv is NOT a DSI event boundary; TCP may split/merge messages and transport delays mean chronology is coarse until client protocol decoded. Keep raw/phone/media/location logs private, publish sanitized findings only.

## Remaining gates

1. Verify stock originals and reviewed diff, vehicle rollback and approved GEM-controlled tracer activation path; no automatic script installer.
2. Build new QNX ARMv7 binary with pinned CI image and inspect ELF.
3. Establish port 1800 appender semantics offline (does no-send receive work, is a handshake required?). If not, inspect OEM jar/protocol or validated alternate passive output route, never invent/send protocol commands.
4. Instrument six services simultaneously and observe cold HMI start, VC FPK settings, Audio, Nav, Phone, VIEW and manual notes without changing OEM inputs; bound volume and abort on instability.
5. Run `decode_keypanel_f902.py` over new private DebugSPI raw. Only if its five-int evidence is insufficient, plan a separate passive `DSIKeyPanelDispatcher.updateEncoder2` observer before ASL validity filtering, maintaining every OEM listener. This is NOT part of current binary.

**Status:** WIP source + synthetic host PASS only. No QNX artifact, on-vehicle activation, DSI-client decode, J285 menu injection or confirmed semantic wheel-to-CarPlay zoom.
