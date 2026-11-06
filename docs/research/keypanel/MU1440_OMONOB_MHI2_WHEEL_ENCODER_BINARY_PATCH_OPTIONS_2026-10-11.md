# MU1440 steering-wheel adapter — omonob/MHI2-Carplay-Maps

> **Research status · 2026-11-05:** **UNINSTALLED DESIGN OPTIONS.** Preserve source lineage and exact vehicle/event limitations; no installed patch is claimed. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


Date: 2026-10-11. Target project: **[omonob/MHI2-Carplay-Maps](https://github.com/omonob/MHI2-Carplay-Maps)** by **omonob/QCDWJ**, published MHI2 package [MU1440_SKODA/790_AID10.5](https://github.com/omonob/MHI2-Carplay-Maps/tree/main/MU1440_SKODA/790_AID10.5). This is the specific MHI2 steering-control implementation discussed with the user. It is distinct from [yuedizhibo/MHI2Q-CarPlay-AltScreen](https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen), which concerns Audi MHI2Q and is useful only as a separate architectural comparison.

**Status: source/bytecode audit and patch design, not a compiled or installed patch.** Do not run two competing source111/isoTX2 producers. Raw private vehicle logs and third-party binaries are not republished.

## The physical evidence
A 240-second passive MU1440 recorder run includes exactly twelve structured f902/tag002e five-int records in the user's declared order (three per direction):

| Wheel and operator-described direction | Raw vector | Count |
| --- | --- | --- |
| Right, first direction | `(4,40,+1,0,1)` | 3 |
| Right, reverse direction | `(4,40,-1,0,1)` | 3 |
| Left, first direction | `(4,44,+1,0,1)` | 3 |
| Left, reverse direction | `(4,44,-1,0,1)` | 3 |

Six OEM wrong-DDS warnings follow all six right events; none follow the left events. The layout strongly matches `updateEncoder2(kbd,encoderId,signedIncrement,extra,validity)`; the inner record tag has not independently been tied to an exact DSI method number. The physical right wheel **press**, separately measured as `updateKey2` KEY40, is not the same event as encoderId40 rotation. Zoom IN/OUT polarity still requires explicit visible scale calibration. Sources: [sanitized measurements](MU1440_F902_FIVE_INT_ENCODER_CAPTURE_2026-10-11.md), [read-only decoder](../../../tools/decode_keypanel_f902.py).

## What omonob/MHI2-Carplay-Maps actually implements
The common `CarPlayClusterControls.jar` in its published MU1102/MU1367/MU1440 packages is identical (8,431 bytes, Git blob `289f41b37261fb2263e8dafd06b8b757af86bf22`). Our previously retained bytecode audit of this exact artifact shows:

- Patched `DSIKeyPanelDispatcher.updateKey2` invokes `Mhi2ClusterControlBridge.onKey2` before preserving ordinary OEM listener forwarding.
- That bridge accepts only `KBD4, KEY38/39`. Key-down requests zoom-in/out immediately; a long hold may also send map-previous/next.
- Its 16-entry command queue sends commands to UDP loopback 127.0.0.1:7032; the matching published MU1440/790 `core.so` (72,794 bytes, Git blob `5700c9e8d63a3cf1cd4e23c4d6d085a8dab972ba`) has a session-retaining worker translating zoom into AirPlay `changeMapZoomLevel` (0=in, 1=out) and map-provider cycling into `requestUI`.
- **The JAR's `DSIKeyPanelDispatcher.updateEncoder2` only forwards to stock listeners; it does not call the control bridge.** Therefore changing a KEY38/39 constant to 40 would change handling of a *press*, not correctly recognize a rotary detent. Omonob's documented short-press zoom and long-press map switching must not be described as verified Škoda rotary zoom.

The official [MU1440 Škoda installer](https://github.com/omonob/MHI2-Carplay-Maps/blob/main/MU1440_SKODA/790_AID10.5/install.sh) stages the control JAR via the J9 bootclasspath and offers rollback; exact package firmware-size validation is part of its installation contract. Never bypass this with a blind hex edit or use its separate media producer alongside MIBR.

## Specific implementation paths to evaluate
**Preferred:** a separate observing DSIKeyPanel listener for notification 23, if its registration and actual VC focus can be established on this target. Accept only signed `keyboard=4, encoderId=40, extra=0, effectiveValidity=1` events, and put a bounded zoom intent into a nonblocking queue only with confirmed **source111 actually visible + VC map focus + current session owner**. Unknown focus => ordinary OEM behavior, no extra CarPlay command. Left ID44 remains volume and right encoder remains ordinary menu scroll when the VC menu is open.

**Alternative exact-version JAR/bytecode patch:** modify **Omonob's** published `de/esolutions/fw/dsi/keypanel/DSIKeyPanelDispatcher.class` to invoke an additive encoder bridge from `updateEncoder2`, preserving the original unmodified OEM notification fan-out and the validity/confirmation flag (raw `0x80` semantics), listener ordering and exception isolation. Rebuild/verify a complete compatible JAR and rollback, bench-test before any separate vehicle trial. No physical KEY38/39 synthesis, no global DDS/volume remapping.

Omonob-only standalone experiments could use its existing core worker to consume semantic zoom requests, but our actual MIBR implementation must instead route to **the existing** `libaltscreen111.so` session/control owner, not launch Omonob's separate core.so or a second AirPlay producer. The sender must use the negotiated cluster display UUID, not an assumed universal ID. CarPlay map provider cycling (`map-next`/`map-previous`) differs from our approved native Škoda vs CarPlay STOCK/DIRECT screen switch.

**Do not suppress raw wheel input globally.** The exact semantic OEM native map-scale action and VC focus must be correlated separately before attempting to hide native zoom while retaining OEM menu scrolling, protocol status and safe fallback. A donor BAP function number does not by itself prove this MU1440 route.

Bench acceptance: all twelve measured tuples, positive/negative, unrelated ID44, press vs rotation, validity 1 and raw 0x81 confirmation, original listener count/ordering, bridge failure/queue overflow, actual map focus vs menu, hidden/unowned source111, session generation changes, zoom direction and rollback. This report changes no code and installs nothing.

## Reference separation
- **Primary input/zoom upstream:** omonob/MHI2-Carplay-Maps by omonob/QCDWJ.
- [Earlier original JAR bytecode and native MHI2 comparison](MU1440_WHEEL_DSI_AND_OMONOB_2026-10-11.md).
- **Separate Audi/MHI2Q comparison only:** [yuedizhibo/MHI2Q-CarPlay-AltScreen by yuedizhibo](MU1440_MHI2Q_ALTSCREEN_ZOOM_PORT_BINARY_PATCH_OPTIONS_2026-10-11.md).
