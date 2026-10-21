# MU1440 / Škoda: raw keypanel, wheel encoders, Omonob CarPlay zoom
**Later evidence update:** The 240-second v1.4 capture subsequently resolved the baseline right and left five-int vectors; the earlier statements below saying that numeric encoder IDs are still unknown preserve the historical 300-second capture status only. See [twelve direct wheel events](MU1440_F902_FIVE_INT_ENCODER_CAPTURE_2026-10-11.md) and the [primary omonob/MHI2-Carplay-Maps (owner omonob/QCDWJ) adapter study](MU1440_OMONOB_MHI2_WHEEL_ENCODER_BINARY_PATCH_OPTIONS_2026-10-11.md).\n\nStatus: evidence + research only, 2026-10-11. No vehicle firmware or Java-class modification is made by this document.

## 1. Versions: v1.3 versus v1.4
- Native recorder v1.3 fixes QNX `/tmp` (backed by `/dev/shmem`) `rename()` failure. It stores an exclusive flat session pointer in the project-owned SD directory, no `/tmp` writes, preserves raw MLP bytes, timestamps and operator notes; SD preflight/remount remains in shell wrapper.
- v1.4 retains the same QNX storage, socket, passive receive-only behavior, notes and frame capture. **It only adds decoding of inner VW DebugSPI type `0x0104` within outer MLP type-1 binary frames**. Observed binary message layout: tag 0x07 at inner offset 45, big-endian UTF-16 code-unit count at 46, UTF-16BE text at 50. Messages are written to text log; matching `HK Received` and related encoder warnings enter the joined timeline. It does not intercept/translate wheels, send DSI requests, invoke CarPlay zoom, patch Java, or alter firmware.
- v1.4 built on QNX 6.5 ARMv7; synthetic binary type-1 integration test in CI. The original capture can be decoded offline independently. Live v1.4-on-car event display remains to be validated.

## 2. Sanitized vehicle evidence (one 300-second capture)
Raw 6,096,627 bytes; 18,571 complete MLP frames; 0 outer text frames; 18,571 outer binary frames; zero resync and truncation. Inner types: 524 `0x0104` (VW text), 18,047 `0x0110` (structured). Decoded 524 OEM text messages: 65 `HK Received` and 32 `A wrong DDS Encoder was recognized`. Seventeen operator notes are approximate time anchors, not exact electrically synchronized traces. Raw bytes, serials, vehicle identifiers, complete private logs and proprietary Java source are **not** published. See sibling sanitized TSV.

Positive key/gesture associations: right wheel press KBD4 KEY40, right Back KBD4 KEY41, right Phone 4/53, left upper 4/46, left lower 4/47, left wheel press 4/44, Voice 4/50, Home 13/116, Menu 13/78. Physical assignment is inferred from human-entered labels with immediate subsequent OEM events and needs an isolated confirmation where required. Long right wheel press (4/40): KST `1 -> 3 -> 4 -> 5 -> 0` in two tests (5.080s and 6.056s). Long right Back (4/41) likewise (5.779s). Long Home (13/116) produced only `1 -> 0` over about 5.535s.
Right wheel up/down: 0 `HK Received` in both intervals, but 5/8 respectively of the `wrong DDS Encoder` warnings, time-correlated with the operation. Left wheel rotations also produced no `HK`, and no such warning in their note windows. Right Assist was not visible as `HK` in this log path. This **does not** prove missing electrical/CAN/DSI events.

### Inner 0x0110 inspection limits
Of 18,047 frames, an observed subtype split by bytes 5..6 was `f9 02`: 3,503; `f9 03`: 13,700; `f9 04`: 331; `f9 05`: 513. Many `f9 03` entries carry recurring UTF-16BE ASL Java class names (vehicle-state, bordcomputer, car/service). This is background structured framework logging, **not a demonstrated decoded physical encoder packet**; do not map 0x0110 positions to wheel direction on present evidence. Retain raw stream for offline diff.

## 3. OEM Java path: what the recorder was missing
Reference independently accessible decompilation: [grajen3/mib2-lsd-patching: AslTargetSystemKeyPanelHandling.java](https://github.com/grajen3/mib2-lsd-patching/blob/master/lsd_java/de/vw/mib/asl/internal/system/AslTargetSystemKeyPanelHandling.java).
- `updateKey(...)` and `updateKey2(...)` call `processKeyEvent`, whose NORMAL-level log is `HK Received: KBD[...] KEY[...] KST[...]`. The native v1.4 decoder now recognizes it.
- `updateEncoder(int keyboard,int encoderId,int increment,int validity)` calls `processEncoderEvent(...,0)` only on the relevant validity value (code tests fourth argument ==1).
- `updateEncoder2(int keyboard,int encoderId,int increment,int extra,int validity)` calls `processEncoderEvent(keyboard,encoderId,increment,extra)` only if fifth argument ==1.
- `processEncoderEvent` has a TRACE-level `ENCODER Keyboard: ... keyId: ... incrementCount: ...`. Our observed stock config has `ASL2.KEYPANEL=false` and `ASL_SYSTEM.KEYPANEL=false`, so seeing NORMAL/warnings while missing TRACE is expected.
- This particular ASL handler accepts encoderId 16 for DDS/menu rotary, and 17 or 44 for volume rotary. All other encoderIds produce the NORMAL/WARN `A wrong DDS Encoder was recognized`. **The 32 warnings prove encoder callbacks reached this Java handler and were not recognized by its branch; they do not reveal the actual encoderId, keyboard, sign, increment, or validity.** In particular, do not assume the physical right Škoda wheel equals VW DDS encoder 16. Both a separate OEM cluster consumer and a firmware-specific ID/configuration mismatch are plausible.
- DDS branch: `sendDdsRotaryEvent` -> service observer 614285568 / HMI rotation event 288 or 283; volume branch: `sendVolumeRotaryEvent` -> observer 597508352 / events 296 or 290 for 17, or HMI 232 for 44. Not evidence that the VC map renderer consumes the same branch.
- DSI boundary: `org.dsi.ifc.keypanel.DSIKeyPanelListener.updateEncoder2` is public in retrieved firmware decompilation. `de.esolutions.fw.comm.dsi.keypanel.impl.DSIKeyPanelReplyService` dispatches **method 30** to `updateEncoder2` with five int32 arguments; method 38 to `updateKey2` (5 ints). A separate offline K3342 QEMU comparison documented this behavior. That prototype proves the dispatch contract in its examined firmware; confirm equivalent message/instance on MU1440 before a native observer. Key mapping/keyboard ID may vary across firmware.
- The user observed native-navigation zoom-stage overlay (e.g. 50m/100m/200m) on top of the CarPlay VC image during rotation. This is concrete evidence of an **active OEM consumer of the wheel action**, despite no decoded `HK`. It does not identify which Java/native/BAP/VC route paints that overlay. Audio-volume wheel likewise may have its own consumer.

## 4. Omonob comparison: distinguish input adapter from semantic AirPlay output
Public project: [omonob/MHI2-Carplay-Maps](https://github.com/omonob/MHI2-Carplay-Maps), [MU1440 Škoda / 790 profile](https://github.com/omonob/MHI2-Carplay-Maps/tree/main/MU1440_SKODA/790_AID10.5). Public README claims **short steering-wheel press = zoom** and **long press = map switch**; it does not document confirmed right/left wheel tick operation on MU1440. Reports that a wheel works on VW but not Škoda/SEAT are a useful cross-profile regression hypothesis, not yet an independently validated mapping.
Public profile installation boot-classpath-injects `CarPlayClusterControls.jar` via `lsd.sh`; the relevant Free790 `core.so` is a separate AirPlay-facing producer. A retained offline source comparison identifies the Free790 map-control worker on loopback UDP 7032 and four textual commands `zoom-in`, `zoom-out`, `map-next`, `map-previous`. `send_map_semantic_command` turns zoom into CarPlay `changeMapZoomLevel` (`zoomDirection=0` in, `1` out) and map changes into `requestUI`. Separate prior 791 lineage includes a virtual-HID knob path, not proof of a working MU1440/790 physical wheel adapter.
**The endpoint already exists; the gap is the firmware-specific physical-input-to-command translation.**

### Fresh public JAR bytecode audit (exact MU1440 Škoda / 790 package)
Independently fetched the public 8,431-byte `CarPlayClusterControls.jar` from the profile above (Git blob `289f41b37261fb2263e8dafd06b8b757af86bf22`). Its ZIP contains `de/esolutions/fw/dsi/keypanel/DSIKeyPanelDispatcher.class`, `de/vw/mib/carplay/clustercontrol/Mhi2ClusterControlBridge.class`, `Mhi2ClusterKeyState.class` and `Mhi2ClusterControlBridge$1.class`. Analysis used the extracted class bytecode and `javap -p -c -constants`; no third-party binary/class is redistributed.

**Exact control route:**
- The replacement/precedence `DSIKeyPanelDispatcher.updateKey2(kbd,key,state,extra,validity)` calls `Mhi2ClusterControlBridge.onKey2(...)` **before** forwarding the original `updateKey2` call to all registered OEM listeners. The added call catches `Throwable`; notification listener handling retains the OEM bit-`0x80` confirmation behavior.
- `Mhi2ClusterControlBridge.onKey2` immediately rejects anything except `kbd == 4` and `key == 38 || key == 39`. It passes the key/state to `Mhi2ClusterKeyState`, queues a semantic command in a 16-entry bounded queue and sends UDP ASCII to loopback `127.0.0.1:7032`.
- `KEY=38, KST=1` queues **zoom-in** immediately; `KEY=39, KST=1` queues **zoom-out** immediately. On release (`KST=0`), state resets without a second short-press action. After the class's own 2,500-ms long timer (or a later KST 3/4/5), held KEY38 queues `map-previous` and held KEY39 queues `map-next`, once per press. Thus a long press may first zoom at key-down and subsequently change map; the code does not implement an encoder tick-to-zoom conversion.
- Critically, the same patched `DSIKeyPanelDispatcher.updateEncoder2(...)` **contains no call to `Mhi2ClusterControlBridge`**. It only passes its five arguments to the existing confirmed or regular `DSIKeyPanelListener.updateEncoder2` iterators. The patch does not convert rotational DSI events into KEY38/39, nor provide a `wheel + / wheel -` path.
- The real MU1440 five-minute capture has **no KBD4/KEY38 or KBD4/KEY39 in its 65 HK messages**, and physical wheel turns correlate instead with the encoder handler's 32 `wrong DDS Encoder` warnings. This explains why this exact Omonob Free790 code will not zoom on **those measured physical wheel rotations** without an additional adaptation, while its mapped 38/39 button events may work wherever a vehicle produces them. Whether VW hardware/firmware generates those IDs on its steering controls is a comparison hypothesis, not measured here.
- The separate current Free791 virtual-HID knob lineage and the current Free790 semantic zoom worker are distinct mechanisms; do not conflate them.

**Conclusion from bytecode, not merely README:** this Omonob JAR taps the correct DSI dispatch layer but consumes **only key callbacks**, not encoder callbacks. For this Škoda, the correct next experiment is a passive `updateEncoder2` tuple probe upstream of `AslTargetSystemKeyPanelHandling`, followed by deliberate, source-111-gated semantic conversion if wanted. There is no evidence that globally changing the OEM Java encoder ID table is needed or safe. Avoid installing the separate toolbox in the current parity session.

## 5. Proposed narrow research/implementation sequence (NOT yet deployed)
1. Capture exact raw `updateEncoder2` arguments `keyboard,encoderId,increment,extra,validity` before ASL filtering and also `updateEncoder` if enabled. First prototype in existing QEMU Java/DSI model and log to an independent bounded SD file (no subdirs under /tmp). Preserve OEM calls and avoid intercepting them; no J9 restart or bootclasspath change in live parity test.
2. Less-invasive alternative: carefully enable targeted `ENCODER Keyboard` TRACE for the KeyPanel category after reviewing runtime logger configuration and backup/restore. This yields first three fields for accepted `processEncoderEvent` but not necessarily extra/validity and cannot expose callbacks dropped earlier. Do not modify `logging.properties` blindly during running tests.
3. One wheel, one detent per NOTE: right +/-, left +/-; hold VC native/CarPlay state constant and capture screen overlay. Confirm increments/sign, keyboard+encoder IDs, actual notification/validity and whether a second listener gets the same physical event. Compare VW, Škoda and SEAT key maps and the now-established Omonob KEY38/39 key-only bridge against any separate 791 HID route; do not reuse QEMU K3342 `keyboard=13` as an assumed Škoda MFW ID.
4. Once raw mapping is verified, create an **additive gated** path `observed DSI rotation -> filtered detents -> local semantic zoom-in/out -> retained AirPlay session`, only when CarPlay VC mode/source 111 and desired focus are active. Do not synthesize fake HK codes, permanently remap volume, globally swallow the OEM event or zoom both native and CarPlay inadvertently. OEM native zoom overlay/focus interaction must be explicitly decided and vehicle-tested.
5. Keep passive native DebugSPI v1.4 as the ground-truth logger; no new production JNI/JAR hook or gesture remapping is validated yet.

## Provenance and publication boundary
Evidence: vehicle-provided 2026-10-10 five-minute session (sanitized counts/IDs only), the user-observed native-map overlay, public OEM class decompilation and Omonob public repo, and existing M.I.B. research as linked. Interpret wheel warnings as correlation, not a verified numeric encoder ID. No raw capture, full vehicle log, private file, firmware binary, or third-party JAR is embedded here.

## 6. Additional parked-vehicle video: physical right roller and VC scale overlay

Private 21.03-s, 1024x576, 30-fps video supplied on 2026-10-11. **Only sanitized observation is published here; the recording, its audio, still frames, and identifying context are intentionally not redistributed.** The user visibly operates the right steering-wheel roller while the instrument-cluster map is displayed. Several detents change the displayed map scale and a separate OEM-looking black scale/OK prompt appears over the video near the lower-right part of the cluster. Readable example scales at approximate **video-relative** offsets are ~1 s: 50 m; ~3 s: 30 m; ~5 s: 750 m; ~7-18 s: 100 m. The underlying map view changes in concert. These observations establish a working native wheel-to-cluster-zoom consumer, even though the earlier Java ASL logger did not emit `HK Received` on rotation.

**Important separation:** video time is NOT synchronized to the 300-second MLP capture. A numerical raw encoder tuple, the exact renderer responsible for the scale prompt, and a CarPlay semantic `changeMapZoomLevel` message are NOT proven by this video. OEM scale changes may coexist with CarPlay video rather than representing AirPlay zoom. Do not claim a confirmed VW/Škoda/SEAT compatibility matrix from this single Škoda observation.

### Evidence-supported signal split

```text
physical right MFW roller
    |
    +--> DSIKeyPanel updateEncoder/updateEncoder2  ---> OEM registered consumers
    |       |                                          \-> native VC map zoom/scale overlay
    |       \-> AslTargetSystemKeyPanelHandling
    |              \-> unknown ID -> 'A wrong DDS Encoder was recognized'
    |
    +--> roller *press* is separate updateKey2, captured as KBD=4 KEY=40
            |
            \-> Omonob's MU1440 Free790 key bridge only acts on KEY=38/39
                 (not on KEY=40, and not on updateEncoder2 rotation)
```

The 32 earlier wrong-DDS warnings are time-correlated with operator-tagged wheel movement and show that the ASL handler received encoder callbacks, **not** that the branch controls the visible OEM overlay. The numeric `keyboard,encoderId,increment,extra,validity` remains unresolved. A passive tap before dispatch filtering, or narrowly scoped trace of `processEncoderEvent`, is the next diagnostic, not a global remap of 16/17/44.

### Narrow acceptance criteria for the next experiment

- For each physically isolated right +/- and left volume +/- detent, record all five raw `updateEncoder2` fields (plus legacy `updateEncoder` if present), validity, sign and count, with a monotonic NOTE and optional simultaneous video.
- Keep every existing OEM listener invocation and stock action intact; do not synthesize 38/39 without a proven mapping. The existing public Omonob Free790 dispatcher is `updateKey2`-only and cannot be evidence of rotary tick support.
- Test two independent questions: did OEM native map scale change, and did the actual CarPlay/AirPlay `changeMapZoomLevel` semantic command reach its retained source-111 session? Screen-overlay appearance alone cannot answer the second.
- Only contemplate source-111/focus-gated, additive map zoom translation **after** the exact physical DSI tuple is proven and any unintended double-zoom/native-overlay side effects are evaluated.
