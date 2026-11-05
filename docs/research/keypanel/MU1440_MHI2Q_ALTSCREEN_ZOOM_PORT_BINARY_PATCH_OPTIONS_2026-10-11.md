# MU1440: real rotary input to CarPlay zoom — MHI2Q AltScreen / Audi comparator audit (2026-10-11)

> **Research status · 2026-11-05:** **CROSS-PLATFORM COMPARATOR.** Audi/MHI2Q behavior is not a compatible MU1440 binary or tested integration. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


**Scope:** This is the separate Audi comparison: `yuedizhibo/MHI2Q-CarPlay-AltScreen` (owner: yuedizhibo). The requested MHI2 implementation is `omonob/MHI2-Carplay-Maps` (owner: omonob/QCDWJ); see [the dedicated MHI2 input study](MU1440_OMONOB_MHI2_WHEEL_ENCODER_BINARY_PATCH_OPTIONS_2026-10-11.md).\n\nStatus: **sanitized evidence + implementation design, NOT a compiled vehicle patch**. Target Škoda MHI2_ER_SKG13_P4526_MU1440, not Audi MHI2Q/AUG22. Preserve the frozen four-core MIBR video/ownership architecture and 48 setting registry. No new J9/LSD/CarPlay/Parity patch authorized or installed by this document.

## 1. New physical input evidence

The private v1.4 capture (13,135 MLP frames, 4,432,325 bytes, no resync/truncation, 264 OEM text, no HK) retains twelve structured **inner 0x0110, subtype f9 02, tag 0x002e, five signed int32** records. User stated each physical direction 3x, in sequence right UP, right DOWN, left UP, left DOWN:

| Physical block (user order) | Observed five-int vector | Repeats |
| --- | --- | ---: |
| Right first direction (UP) | (4,40,+1,0,1) | 3 |
| Right second direction (DOWN) | (4,40,-1,0,1) | 3 |
| Left first direction (UP) | (4,44,+1,0,1) | 3 |
| Left second direction (DOWN) | (4,44,-1,0,1) | 3 |

Exactly six right-wheel records precede exactly six ASL `A wrong DDS Encoder was recognized` messages; no such warning accompanies left six. This is strong empirical conformity with `updateEncoder2(kbd,encoderId,signedIncrement,extra,validity)`, **not independent proof that record tag 0x002e equals a specific DSI method ID**. Physical UP/DOWN ↔ CarPlay zoom IN/OUT polarity needs a separate native map scale observation. `KEY40` physical press in an `updateKey2` event is distinct from encoderId40 rotation; never synthesize KEY38/39.

Evidence + reproducible read-only decoder:
- [Twelve-record analysis](MU1440_F902_FIVE_INT_ENCODER_CAPTURE_2026-10-11.md)
- [Offline f902 decoder](../../../tools/decode_keypanel_f902.py)
- Earlier [KeyPanel / Omonob audit](MU1440_WHEEL_DSI_AND_OMONOB_2026-10-11.md) is an earlier checkpoint; its statement that numeric values remained unknown is now superseded by this capture. Raw user files stay private.

## 2. What yuedizhibo/MHI2Q-CarPlay-AltScreen and Allemon's Audi code provide

**yuedizhibo/MHI2Q-CarPlay-AltScreen, V3.7/V3.7Fix3, GPL-3.0:** The author's README expressly supports **Audi MHI2Q/AUG22**, states MHI2 is unsupported, and warns not to bypass installer firmware checks. Do **not** install/repackage its MHI2Q preload, HMI JAR or display runtime as a compatible MU1440 binary.

Its Java `Toolbox/carplay_alt_screen/hmi/src/com/luka/carplay/cluster/WheelZoomBridge.java` receives an already interpreted absolute `onMagnificationChanged(int)` callback. It seeds the first absolute reading, calculates signed delta, gates on `ClusterStateController.isClusterOwned()`, drops zero and absolute delta >16, and writes a bounded epoch/seq/commit `OEM_STEPS_V1` event to `/tmp/mmi-mirror-wheel-zoom.events`. A search of the yuedizhibo repository found **no `updateEncoder2` implementation or direct `WheelZoomBridge.onMagnificationChanged` callsite in the indexed source files**; the stated ClusterService callback caller must be verified against the actual shipping HMI/JAR before claiming a byte-level hook site.

Its native `p1404_cockpit_native.c` reads only validated queue records (`direction` 0/1, `delta` -16..16, abs matches steps and sign), maintains **desired target versus already submitted** relative zoom, reversals retarget, outstanding error cap 12, and paces one-step `alt_send_cluster_zoom(...)` via current retained AirPlay session and decoded-frame progress/fallback timers. The BUILD_INFO documents `changeMapZoomLevel` direction **0=in, 1=out**, and Java 1.2/major46 compilation. Decoded-video progress is a liveness heuristic, **not an iOS semantic acceptance/zoom completion ACK**. The repository's installer checks compiled-JAR identity (`jar_size`, `jar_cksum`, `jar_sha256`): byte changes without rebuilding matching metadata are not a viable installation process.

**Allemon Audi:** `ScreenCombiBAPListener.setMapScale(steps)` calls CarPlay handler *then* `super.setMapScale(steps)`, so the stock map zoom continues. Its separate extra `DSIKeyPanel` KEY2 listener documents the feasibility of observing raw wheel press without wholesale dispatcher replacement. `de.audi.tghu.*` classes are not drop-in Škoda `de.vw.mib.*` classes.

**Omonob MU1440 Free790 (different third-party lineage):** bytecode-audited `DSIKeyPanelDispatcher.updateKey2` bridges only KBD4 KEY38/39 to loopback UDP7032; `updateEncoder2` only forwards OEM listeners. Its extant AirPlay command semantics are useful, but neither its KEY38/39 nor the MHI2Q AltScreen absolute magnification callback identifies the physical Škoda roller.

Source links:
- https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen/blob/main/README_EN.md
- https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen/blob/main/Toolbox/carplay_alt_screen/hmi/src/com/luka/carplay/cluster/WheelZoomBridge.java
- https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen/blob/main/Toolbox/carplay_alt_screen/src/p1404_cockpit_native.c
- https://github.com/Allemon/mib2-carplay-rgi-altscreen/blob/main/java_patch/de/audi/tghu/navi/app/cluster/ScreenCombiBAPListener.java

## 3. Earliest sensible receiving seam: DSI encoder notification, but not global consumption

Recovered cross-firmware QEMU path: `DSIKeyPanelReplyService` reply method30 reads five int32, calls `updateEncoder2`; dispatcher notification **23** serves `updateEncoder2`, notification **25** serves `updateKey2`. Exact stock ASL registers `{25,23,20}`; callback accepts effective validity=1, ID44 volume, ID16 DDS, but ID40 produces its warning. The dispatcher's raw fifth-argument flag 0x80 is an OEM listener-confirmation bit; preserve its original mask, confirmation order and fan-out if modifying dispatcher. The observed logged fifth argument is 1, not 0x81.

**Preferred approach:** add a separate, read-only `DSIKeyPanelListener` for attribute 23 (validate instance/service/registration on target); the callback receives real `(4,40,steps,0,1)` with signed steps, independent of `updateKey2`. It never fabricates an HK event, does not edit ID16/17/44, and forwards/does not interfere with stock listeners. Put only validated small intents into a bounded nonblocking queue; no disk/network IO on OEM callback thread. A separate worker relays asynchronously to *our existing MIBR libaltscreen111 source/control plane* and its live retained AirPlay session; do **not** hand it to an unrelated third-party core.so or second source111 owner. Protect by exact context: confirmed source111 **visible**, actual VC navigation map focus/page, session generation and current Parity ownership. Unknown context: stock only; no queued CarPlay command. Do not equate merely `source111 negotiated` with `map focused`.

Conceptual callback filter, **not deployable source**:

```text
on updateEncoder2(kbd,id,increment,extra,validity):
    observe tuple; preserve OEM notifications
    if (kbd != 4 || id != 40 || extra != 0 || validity != 1): return
    if (increment < -16 || increment > 16 || increment == 0): return
    if (!confirmedVCMapFocus || !source111ActuallyVisible || !currentSessionOwner): return
    enqueueBounded(sessionGeneration, signedIncrement) // asynchronous
```

Before enabling output, isolate first-direction versus *actual OEM map scale IN/OUT*. Do not copy Audi's magnification-to-direction sign directly. When converting to the repository's OEM_STEPS_V1 queue semantics, **one detent signed +/-1** is already a delta, not an absolute magnification; bypass its first-absolute-seed logic. Maintain queue epoch and seq, validate generation, collapse/rebase opposite backlog rather than blindly replay.

## 4. Where to stop native zoom / avoid breaking menu operation

A globally swallowed `updateEncoder2(4,40,...)` would also kill normal VC menu scroll. **Do not suppress it there**. Observe at DSI; investigate an additional, *separately proven* semantic OEM map-scale request/action immediately before it changes the native map. Suppress **only the stock zoom side effect** when CarPlay is visually active and native VC map focus is confirmed, while preserving protocol ACK/status and non-map consumers. Neither donor NavSD BAP function45 nor native-looking scale overlay alone proves which exact MU1440 method owns this action. First test mirrored CarPlay zoom with original OEM forwarding and watch for overlay/double zoom; defer any selective stock suppression to a host/QEMU-tested narrow hook. If OEM wheel is in VC menu, allow exact stock event and no CarPlay zoom.

## 5. Verified AirPlay command shape in yuedizhibo/MHI2Q-CarPlay-AltScreen

The exact MHI2Q AltScreen C function is `alt_send_cluster_zoom(receiver,stream,generation,event_seq,direction)` in `Toolbox/carplay_alt_screen/src/p1404_airplay.c`. It first checks non-null *retained* receiver/stream, current generation, sequence and the cluster display UUID; resolves `AirPlayReceiverSessionSendCommand`, and constructs this conceptual CFDictionary (shown here in readable notation, **not** a literal JSON/network packet):

```json
{"type":"changeMapZoomLevel","params":{"uuid":"<negotiated cluster display UUID>","zoomDirection":0}}
```

Direction 0 = zoom in, direction 1 = zoom out. Submission uses the current AirPlay receiver and guarded source-111 command acquisition, with an asynchronous response context; submit success is **not** proof of completed visible iPhone map zoom. The repository's native scheduler (in `p1404_cockpit_native.c`) uses a 50ms monitor tick, dynamic paced single-step sends, target-vs-sent relative steps with a bounded outstanding target (12) and reverse-direction retargeting. It does not directly apply pixel scaling to the entire video.

For **our MU1440**, source111 is already owned by `libaltscreen111.so`; the new input adapter must submit a typed intent to **that existing owner**. A second unrelated MHI2Q AltScreen or Omonob AirPlay worker would create competing ownership and is not an acceptable transplant. The MIBR source111 tree presently contains research on `changeMapZoomLevel`, but this document does not assert that an equivalent *working sender* has already been linked into the current MU1440 production binary.

## 6. Patch options and vehicle release gate

| Option | Feasibility | Scope |
| --- | --- | --- |
| Separate listener/adapter rebuilt for exact MU1440 | **Preferred** | Additional listener to attribute23, bounded async queue, exact focus/owner, no stock listener changes |
| Exact-target JAR/bytecode patch in existing MU1440 `DSIKeyPanelDispatcher.updateEncoder2` | **Possible, conditional** | Add a bridge call before exact OEM forwarding; catch exceptions; preserve raw 0x80 confirmation; matched JAR SHA, class ABI, Java/J9 version, packaging, restore |
| Hex-edit an Audi MHI2Q/AUG22 release/preload for MU1440 | **Not substantiated/unsafe** | Cross-family native ABI, Audi class owner, Context80 display/video and AirPlay integration differ. Do not bypass installer guard |
| Change only the MHI2Q AltScreen `WheelZoomBridge` input callback | **Not sufficient alone** | It expects Audi absolute magnification; there is no verified Škoda caller or native source111 bridge. Port its pacing model, not its binary |

Release gate: pin exact current binaries + hashes and restore copies; replicate real DSI five-int callbacks and 0x81->1 confirmation path in host/QEMU; verify two listeners get each event once, original order/exceptions unchanged, logger/relay failure fails open; verify map vs VC menu vs stock vs source111-not-visible, opposite bursts, reconnect and long wheel press; check one and only one retained AirPlay zoom and sole MOST isoTX2 payload owner; only then independent, reversible, user-authorized parked vehicle trial. Do not patch existing parity/live source111 in the diagnostic iteration. No user-approved physical key binding yet for SafeArea/source switch; retain the three approved capability requirements without inventing assignments.

Licensing: this is an independent factual cross-project analysis referencing yuedizhibo/MHI2Q-CarPlay-AltScreen (GPL-3.0), not a copied/redistributed third-party binary or ported derivative; if reusing their actual source, retain proper GPL-3.0 terms/notices and corresponding source.
