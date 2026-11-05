# MU1440 right/left wheel 5-int raw mapping (2026-10-11)

> **Research status · 2026-11-05:** **MEASURED FOLLOW-UP.** Exact 12-detent F902 correlation resolves an earlier input-ID uncertainty for that capture, not all live zoom/focus behavior. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


**Finding: direct offline recovery of all twelve physical wheel detents in previously undecoded inner DebugSPI 0x0110 records.** Passive v1.4 vehicle run; no Java/LSD/J9, CarPlay, Parity or OEM input patch.

## Capture and operator provenance
User stated *each direction 3x*. One operator NOTE at monotonic `2030916 ms`: `rechts rad erst oben dann unten, dann links oben und unten`. These were four serial blocks, right up x3 / right down x3 / left up x3 / left down x3. NOTE was before the full sequence, not before each detent, so direction labels here are **correlated with declared order**, not independent electrical-direction annotation.

Recorder v1.4 reported `13135` complete MLP frames, `4432325` raw bytes, `264` inner 0x0104 text frames, `0` HK messages, `0` resync, no cap/truncation. All outer frames type 1. Offline parsing of raw: `12871` inner 0x0110 structured and `264` inner 0x0104. The **twelve and only twelve** 0x0110 / subtype `f9 02` / record tag `0x002e` / 5-tagged-int payloads match the complete physical test sequence. The v1.4 live text decoder does NOT decode these raw structures; absence of HK is not absence of input.

## Extracted records
The observed structured layout is: inner `ff 01 10`, subtype at bytes 5..6 `f9 02`; event tag at 37..38 `00 2e`; the observed two 32-bit prefix values at 39..42 = 0, 43..46 = 4, 47..50 = 5; at 51..75 five consecutive elements, each `01` + signed big-endian int32. The inner header 11..14 carries the monotonic millisecond time. The exact semantic meaning of **record tag 0x002e is not independently documented**; do not conflate it with DSIKeyPanelReplyService method number 30. The five values conform to the previously recovered `updateEncoder2(keyboard,encoderId,signedIncrement,extra,validity)` signature, with exceptionally strong physical count/order correlation.

| Block (physical order) | Raw 5 integers | Timestamps (monotonic ms) | Count |
| --- | --- | --- | --- |
| Right wheel, first direction (UP per user) | `4,40,+1,0,1` | 2045783 / 2046323 / 2046862 | 3 |
| Right wheel, opposite (DOWN per user) | `4,40,-1,0,1` | 2048725 / 2049343 / 2050003 | 3 |
| Left wheel, first direction (UP per user) | `4,44,+1,0,1` | 2051262 / 2051802 / 2052322 | 3 |
| Left wheel, opposite (DOWN per user) | `4,44,-1,0,1` | 2054062 / 2054602 / 2055222 | 3 |

Source correlates six and only six OEM text warnings `[AslTargetSystemKeyPanelHandling] A wrong DDS Encoder was recognized` at 2045908, 2046492, 2046892, 2048844, 2049437, 2050043 ms: each directly follows one of the six **right** wheel events, delays approx 125/169/30/119/94/40 ms. **No such warning follows the six left wheel events.** This aligns with donor ASL handler's encoder ID 44 volume branch and rejection of encoder ID 40 for that particular DDS consumer. It does not disprove independent OEM native VC map-scale consumption of right wheel or prove a BAP zoom handler.

This makes a stronger mapping than our earlier warning-only correlation, and explains the symbolic physical LEFT/RIGHT mismatch: KBD4 KEY40 is observed both as right-wheel press in the earlier distinct capture and as encoder ID40 in this rotation capture; 44 likewise left. These are **different DSI event types**, not synthesized `HK Received` 38/39. Future CarPlay Zoom direction 0=in/1=out must be correlated against actual map-scale behavior; do not infer it from physical UP/DOWN or int sign alone.

## Implementation/research disposition
- **Resolved for this exact experiment:** candidate raw DSI-equivalent tuple for both physical wheels and signed single-detent direction. The existing 240-second capture is sufficient for this mapping, **no need to repeat solely to find basic encoder IDs**.
- **Still open:** formal mapping of structured record tag `0x002e` to exact OEM callback method and listener, effect of validity `0x80` confirmation flag in other sessions, alternate clusters/VC contexts, native BAP MapScale action/focus and OEM overlay renderer, and actual AirPlay semantic zoom. For future context audit, repeat isolated right +/- in native map, source111-map and VC menu with separate NOTES and/or a bounded dispatcher observer only if required. Never globally swallow `updateEncoder2` events.
- **Near-term code path:** add offline reader for narrowly observed f902/0x002e typed-five-int record, include strict framing, element type/length checks, and no raw data publication. Extend v1.4 live display **only after regression tests**; the 0x0110 raw is already safely saved.
- **Protect the approved trio:** map-only/right-roller semantic zoom; two negotiated ViewArea+SafeArea presets; guarded STOCK/DIRECT native vs CarPlay display, preserving normal VC menu/volume and independent Parity ownership.

Private original .bin and full OEM logs remain with the user; only sanitized counts/tuples/times are published here. Previous v1.3 capture and separate 21.03-second VC overlay video are NOT time-synchronized to this run.
