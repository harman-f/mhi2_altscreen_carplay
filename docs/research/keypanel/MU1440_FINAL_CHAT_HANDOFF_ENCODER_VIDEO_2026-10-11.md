# MU1440 Keypanel / wheel encoder / VC zoom — final chat handoff (2026-10-11)

**Later evidence update:** The v1.4 on-car run has since yielded twelve direct structured encoder records: right `(4,40,+/-1,0,1)`, left `(4,44,+/-1,0,1)`, three per direction. The earlier pending v1.4-live and raw-ID statements below describe the point in time of this handoff, not the current status. See [new measured evidence](MU1440_F902_FIVE_INT_ENCODER_CAPTURE_2026-10-11.md) and [omonob/MHI2-Carplay-Maps (owner: omonob/QCDWJ) adapter study](MU1440_OMONOB_MHI2_WHEEL_ENCODER_BINARY_PATCH_OPTIONS_2026-10-11.md).\n\n**Status:** Public, sanitized, evidence-based research/handoff. The physical right-roller video and the five-minute vehicle capture are separate tests, not time-synchronized. No Java patch/firmware change/zoom injection has been installed or validated as part of this investigation.

This document preserves the response that could not be displayed in the previous full conversation. Read it alongside [the complete DSI/Omonob/roller audit](MU1440_WHEEL_DSI_AND_OMONOB_2026-10-11.md), [the measurement matrix](MU1440_CAPTURE_SANITIZED_MATRIX.tsv), and [capture/install instructions](../../testing/MU1440_NATIVE_KEYPANEL_CAPTURE.md). Do not restart the research from scratch.

## 1. Actual new binary: v1.3 versus v1.4

* v1.3 fixed QNX memory filesystem behavior (`/tmp` backed by `/dev/shmem`; staging/rename yielded `Improper link`), placed one exclusive flat session pointer on project SD instead, accepted canonical QNX alias `/net/mmx.mibhigh.net/fs/sda0`, and retained SD write preflight with `mount -uw`. It was successfully exercised on vehicle as a receive-only recorder.
* v1.4 keeps the identical capture/two-SSH-commenting/storage/loopback TCP architecture. It adds decoding of **outer MLP binary type 1 / inner 0x0104**: 0x07 tag at inner offset 45, BE UTF-16 code-unit count at 46..49, UTF-16BE text from 50. It surfaces `HK Received` as EVENTs and encoder warnings as RELATED in the joined timeline. Outer stream is still preserved verbatim.
* No native `updateEncoder2` tap, no rewiring of the right or left roller, no `changeMapZoomLevel` emission, no global key map, no modification to LSD/J9/Parity/isoTX2. QNX 6.5 ARMv7 GitHub build and synthetic type-1 CI regression succeeded at [commit 4ab9062b](https://github.com/harman-f/mhi2_altscreen_carplay/commit/4ab9062bb183859ede738d95b43f57524dd25390), [run 38090171136](https://github.com/harman-f/mhi2_altscreen_carplay/actions/runs/38090171136). The previous five-minute capture was on v1.3 and reprocessed offline; v1.4 LIVE automotive decoding has NOT yet been retested.
* Exact new self-test signature: `SELF_TEST=PASS split-MLP, text, HK-event; SD-pointer-v1.3; inner-0104-v1.4`.

## 2. Preserved five-minute vehicle result (offline)

6,096,627 raw bytes; 18,571 complete MLP frames, all outer type-1 binary, no resync/truncation. Inner `0x0104`: 524 OEM text messages, including 65 `HK Received` and 32 `A wrong DDS Encoder was recognized`; `0x0110`: 18,047 structured log records **not** decoded into physical rotary tuples. Seventeen manual notes anchor approximate time intervals.

| Physical/commented input | Correlated input ID / finding |
| --- | --- |
| Right roller PRESS | KBD 4 KEY 40, short 1→0; long 1→3→4→5→0 (twice) |
| Right Back | 4/41, short/long; long 1→3→4→5→0 |
| Right Phone | 4/53 |
| Left upper/lower buttons | 4/46 and 4/47 |
| Left roller PRESS | 4/44 |
| Voice | 4/50 |
| Home / Menu | 13/116 and 13/78 |
| Right roller ROTATION up/down | **no HK**; correlated with 5/8 `wrong DDS Encoder` warnings in operator windows |
| Left volume roller ROTATION | no HK and no matching warning in tagged windows |
| Right Assist | no HK in this capture; physical / OEM routing unresolved |

Right press hold duration ~5.080 and ~6.056 s; right Back ~5.779 s; Home ~5.535 s yielded only 1→0. Numeric key assignments are correlated with human labels; perform isolated rechecks if absolute electrical identity is required. **No** 4/38 or 4/39 occurs among the 65 HK reports. Absence of `HK` is NOT absence of a DSI encoder event.

## 3. Previously hidden final video response, reconstructed in full

The user supplied a 21.03-s, 1024×576, 30-fps video of operating the **physical RIGHT steering-wheel roller** while the navigation image was shown in the Virtual Cockpit, with CarPlay video underneath. Rotation visibly changes map scale and produces a **separate native-looking black scale/OK prompt** on the right, overlaying the display. In representative video-relative frames approximately **1 s: 50 m; 3 s: 30 m; 5 s: 750 m; ~7–18 s: 100 m**. The map view varies too. Video and earlier MLP trace are NOT synchronized. No private video, frames, map/street/location content, microphone/audio or identifying context is redistributed in this public document.

**What this proves:** the physical right-wheel input reaches an operational OEM/native consumer, which can display native VC zoom scale feedback over the CarPlay/video presentation. Therefore the absence of a wheel `HK Received` message is a logger/DSI-path limitation, not evidence that the hardware does nothing.

**What this does not prove:** a precise 5-tuple `updateEncoder2`, the Java/native renderer drawing the scale overlay, or any Apple CarPlay `changeMapZoomLevel` command being sent by rotation. The OEM scale feedback and CarPlay semantic zoom must be evaluated independently. It is inappropriate to patch Java key IDs based solely on the visual overlay.

## 4. Where to intercept: two distinct OEM pathways

Reference OEM decompilation [AslTargetSystemKeyPanelHandling.java](https://github.com/grajen3/mib2-lsd-patching/blob/master/lsd_java/de/vw/mib/asl/internal/system/AslTargetSystemKeyPanelHandling.java):

```text
DSIKeyPanel
  updateKey / updateKey2 --------> processKeyEvent -----> NORMAL 'HK Received'
  updateEncoder / updateEncoder2 -> processEncoderEvent -> TRACE raw fields
                                           |-> ID=16: DDS selection
                                           |-> ID=17/44: volume
                                           \-> other ID: WARN 'A wrong DDS Encoder was recognized'
```

Asl's `updateEncoder2(kbd,encoderId,increment,extra,validity)` invokes `processEncoderEvent` only when `validity == 1`. The TRACE statement (`ENCODER Keyboard: ... keyId: ... incrementCount: ...`) was not enabled in the observed logging config (`ASL2.KEYPANEL=false`, `ASL_SYSTEM.KEYPANEL=false`). The WARN proves arrival to **that ASL handler** but omits numeric fields and cannot rule out simultaneous independent OEM/VC consumers. Accepted ID branches have DDS observer 614285568 / HMI 288,283 and volume observer 597508352 / HMI 296,290 or 232. Do not globally rewrite 16/17/44.

Recovered QEMU Java dispatch: `de.esolutions.fw.comm.dsi.keypanel.impl.DSIKeyPanelReplyService` method **30** calls `updateEncoder2` with five Int32; method **38** calls `updateKey2` with five Int32. QEMU K3342 provenance is not automatic proof of identical MU1440 routing. This dispatcher level is the sensible prospective read-only probe point, **before ASL filters**, preserving all OEM listener forwarding.

## 5. Verified Omonob Free790 MU1440 implementation

Public [Omonob MU1440/790 profile](https://github.com/omonob/MHI2-Carplay-Maps/tree/main/MU1440_SKODA/790_AID10.5) ships the 8,431-byte `CarPlayClusterControls.jar` (Git blob `289f41b37261fb2263e8dafd06b8b757af86bf22`). Bytecode inspection (`javap -p -c -constants`) verifies that `DSIKeyPanelDispatcher.updateKey2()` calls `Mhi2ClusterControlBridge.onKey2()` before forwarding to OEM listeners. The bridge accepts **only KBD=4 KEY=38/39**, not the measured right-wheel PRESS 4/40. On KST=1, 38→`zoom-in`, 39→`zoom-out`; after ~2,500 ms long hold 38→`map-previous`, 39→`map-next`. A long hold may first issue zoom immediately, then map switch. Commands enter a bounded 16-slot queue, then loopback UDP `127.0.0.1:7032` to `core.so`.

The Free790 `core.so` map worker can issue AirPlay `changeMapZoomLevel` (direction 0=in,1=out) and `requestUI` for map changes; this endpoint was independently described in a retained offline source comparison.

**Critical finding:** the same modified `DSIKeyPanelDispatcher.updateEncoder2` merely forwards OEM callbacks and **does not call the CarPlay bridge**. Hence this exact public Škoda Free790 JAR implements key actions, not translation of physical roller detents; no KEY38/39 appears in the measured vehicle HK list. VW/SEAT/Škoda hardware/config variations remain comparison hypotheses, not a verified compatibility matrix. The distinct 791 virtual-HID knob is not proof of Free790 physical wheel integration.

## 6. Next chat: exact task and safety contract

1. Start by reading this document and [complete audit](MU1440_WHEEL_DSI_AND_OMONOB_2026-10-11.md). Verify latest GitHub heads and v1.4 CI artifact; **do not repeat** completed broad repository research as a prerequisite.
2. Investigate a minimal **passive** DSI dispatcher observer for `updateEncoder2` (plus legacy `updateEncoder` if active), capturing all five original int fields: `kbd, encoderId, signed incrementCount, extra, validity` alongside monotonic NOTES, and preserving all OEM listeners and controls. Compare other VC/cluster listener routes. Prototype and test in QEMU/host first. Alternative: narrow TRACE enabling after explicit backup/restore review; this may omit `extra/validity` and earlier-filtered events.
3. A future parked test should isolate one right up/down and one left up/down detent per note. Distinguish three outputs: raw encoder tuple, OEM native zoom/scale overlay, and a real source-111 AirPlay semantic zoom call. Don't assume they are the same.
4. Only after tuple mapping is verified, assess additive source-111/focus-gated `rotary -> semantic zoom-in/out`. Preserve OEM behavior, rollback, and parity/video path. No unvalidated LSD/J9 restart, bootclasspath patch, fake HK 38/39 or global ID remap.

## Scope and data handling

This public handoff contains sanitized findings, sources, commands and counts only. The 6-MB original capture, 21-s video, timestamped full logs, decoder-generated full CSV and original frame selections are privately archived separately with SHA-256 manifest; their actual content is NOT public-committed. `MIBR-MU1440-KEYPANEL-INTERNAL-HANDOFF-EVIDENCE-20261011.zip` can be attached to the new private chat.
