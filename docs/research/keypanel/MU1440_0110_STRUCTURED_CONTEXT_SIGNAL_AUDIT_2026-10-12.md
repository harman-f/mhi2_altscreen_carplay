# MU1440 DebugSPI inner 0x0110: broader structured-message census and wheel downstream correlation (2026-10-12)

Status: **passive offline analysis of private existing 240-second vehicle capture**, not a decoded VC menu/BAP signal, no firmware patch, no port-1800 dependency. Raw binary, identifiers and full OEM logs stay private. No claim that a method tag numerically equals an exact DSI method.

## Source and framing

The private user-supplied `debugspi-original(1).bin` has 4,432,325 bytes, 13,135 valid complete original MLP outer frames, 264 inner `ff 01 04` OEM texts, and **12,871 inner `ff 01 10` records**. The 0x0110 records break down by their bytes at inner offset [5:7]:

| 0x0110 subtype | Count | What can now be read safely |
| --- | ---: | --- |
| `f9 02` | 2,299 | Numeric message-tag grouping; twelve exact wheel-five-int tuples among these |
| `f9 03` | 10,278 | At inner offset 35: 32-bit BE UTF-16 character count, followed at offset 39 by readable UTF-16BE **Java class name**; further typed fields still require schema |
| `f9 04` | 32 | Numeric tag and typed payload; wheel-dependent pattern, semantics unproven |
| `f9 05` | 262 | Numeric tag and typed payload; wheel-dependent pattern and background periodic records |

The 10,278 f903 records resolve to only **15 distinct fully readable Java class-name strings**. About 1,993–2,001 each mention five high-frequency `de.vw.mib.asl.internal.car.*` / `...system.AslTargetSystemVehicleStates` classes; thus counting them as ten thousand independent unknown VC events would be misleading. One recurring class `ASLTargetCarParkHeater` appears 240 times. Several sparse named classes genuinely relate to navigation, e.g. `de.vw.mib.asl.internal.navigation.bap.HsmTargetBap` **six occurrences**, plus `navigation.api.impl.has.StateWork` (3), `navigation.splitscreen.SplitscreenStateWork` (3), and `navigation.waypointmode.StateDefault` (3). In THIS capture their observed timestamps precede the user's roller detents, so they are not a demonstrated per-detent VC response or MapScale call.

## One-to-one wheel downstream correlation (new)

Operator's single NOTE at monotonic 2030916 ms specified four serial blocks, three physical detents per direction, right then left. Previously decoded `f902` tag `0x002e` (numeric 46) yielded twelve signed vectors:

- right first direction: `(4,40,+1,0,1)` at 2045783, 2046323, 2046862 ms;
- right opposite: `(4,40,-1,0,1)` at 2048725, 2049343, 2050003 ms;
- left first direction: `(4,44,+1,0,1)` at 2051262, 2051802, 2052322 ms;
- left opposite: `(4,44,-1,0,1)` at 2054062, 2054602, 2055222 ms.

Within **0–25 milliseconds AFTER EACH** of six left wheel events, exactly one occurrence each of these observed binary patterns is present:

| Inner subtype | Observed four-byte numeric tag (offset 35) | Per-left-detent appearances |
| --- | ---: | ---: |
| `f9 04` | 6 | 6 / 6 |
| `f9 04` | 7 | 6 / 6 |
| `f9 05` | 7 | 6 / 6 |

**None** of these three per-detent patterns appears within the same 25ms post-event windows for the six right wheel events. A `de.vw.mib.asl.internal.sound.HsmSoundDPHandling$StateSoundDPHandlingHandling` f903 class record is also timestamped 2051276 ms (14ms after the first left detent). These are strong **temporal correlations with distinct downstream processing**, NOT yet proof that the f904/f905 tag numbers denote particular OEM volume method/ACK semantics.

Separately, the six right pulses were followed by the six OEM `wrong DDS Encoder` text warnings. This confirms raw text/HK decoder coverage is very incomplete while the inner structured channel contains useful discriminating data.

## What this capture cannot yet establish

- Its NOTE describes roller rotations only; there is **no independently annotated, synchronous** VC-menu open/close, native-map page switch, STOCK/DIRECT transition or video trace. Without separate context blocks, even a complete message decoder cannot label a record conclusively `vc_map_focus` merely from coincidence.
- A readable HU-side Java class name `...navigation.bap.HsmTargetBap` is NOT a verified reply *from the AID/VC*. Need trace direction and actual BAP/DSI method fields before claiming bidirectional cluster visibility/MapScale telemetry.
- Neither active AirPlay source111 nor its showUI acknowledgment independently proves actual VC map focus or current DIRECT payload owner. Do not turn on an automatic wheel takeover on this evidence alone.

## Next offline/vehicle experiment — avoid blind port-1800 retry

1. Extend the read-only, original-framing decoder to inventory the **full** f902/f903/f904/f905 records: subtype, safe numeric tag, monotonic timestamp, typed-field patterns and f903 Java class, without publishing unfiltered payloads or serial/phone/location fields. Use strict length checks; for unknown schema emit *unknown*, not invented DSI names.
2. Subtract periodic/background families (especially f902/31, five repeated f903 class families and f905/94) to isolate transitions.
3. One short **parked** DebugSPI v1.4 capture with a separate operator NOTE **before each** isolated block: (a) native map right +/-; (b) visible CarPlay map DIRECT right +/-; (c) open VC menu while 111 stays connected, right +/-; (d) switch back to STOCK, right +/-; plus notes for VIEW/layout if desired. Synchronize actual observed screen and logger clocks. Retain logs privately.
4. Diff structured record families/tags and Java-class names between those state transitions, then cross-reference exact MU1440 firmware code (DSI, `NavigationMapAdapter`, NavSD `MapScale`, VC focus events). Only if this remains ambiguous add a narrowly scoped **passive** semantic MapScale trace.
5. For the existing draft zoom PR, wire one authoritative proven semantic interception route, never globally block `updateEncoder2` or claim that port 1800 provides an event stream.

See earlier [12-encoder record proof](https://github.com/harman-f/mhi2_altscreen_carplay/blob/main/docs/research/keypanel/MU1440_F902_FIVE_INT_ENCODER_CAPTURE_2026-10-11.md) and [read-only narrow decoder](https://github.com/harman-f/mhi2_altscreen_carplay/blob/main/tools/decode_keypanel_f902.py). Primary upstream comparison remains **omonob/MHI2-Carplay-Maps** (owner omonob/QCDWJ), not Audi MHI2Q.
