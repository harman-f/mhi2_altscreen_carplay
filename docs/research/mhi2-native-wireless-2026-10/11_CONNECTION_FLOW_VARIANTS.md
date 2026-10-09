# 11. Two Wireless CarPlay connection-flow variants (Apple background vs MU1440 evidence)

**Reason for this separate note:** Apple's public design guidance changed after early classic Wireless CarPlay. A research document that always equates Controller discovery with Bonjour might mislead a developer working on a newer approach. These are **alternative endpoint-discovery modes**, not alternate display paths.

## A. Classic Wireless CarPlay sequence (public Apple overview, 2017)

```text
pair or recognize phone
  -> Bluetooth iAP2 (identification + MFi + device/transport identity)
  -> user consent where required
  -> wireless AP credentials / phone WLAN association
  -> Bonjour service browse/resolve
  -> Controller Connect / secure CarPlay session
  -> iAP2-over-CarPlay handoff + negotiated Bluetooth release
  -> ACTIVE
```

This is the broad route used by our B0 read-only observer (`_carplay-ctrl._tcp`), and by the historical session-owner comparison. Apple explicitly warned that Bluetooth/iAP2 may remain active after WLAN association until the CarPlay/iAP handoff reaches its intended transition. Timing the Bluetooth teardown from IP association alone is unsafe.

## B. Simplified wireless connection flow (Apple WWDC 2023)

```text
existing iAP2 pairing/identification context
  -> exchange the IP endpoint address and TCP port over iAP2
  -> establish Controller/CarPlay session at that endpoint
  -> secure peer/session and transport handoff
  -> ACTIVE
```

Apple calls this preferred for compatible systems: **Bonjour is not needed for endpoint discovery**, and the described flow supports WPA3-only networks and iOS 14+. For older iOS support, Apple advises also retaining the Bonjour method. This **does not establish** that the stock MU1440 driver or our prototype implements that newer message format; the required iAP2 fields and exact target handlers were not validated in our frozen research.

**Different stages still exist in either mode:** underlying iAP2/MFi trust, valid WLAN/AP networking, a known current remote endpoint, Controller/Pair Setup/Verify and a securely owned ongoing session. The simplified route is not a security bypass and does not prove support merely because a modern phone is present.

## C. Which facts apply to this exact MU1440 research?

| Statement | Evidence level | Publication verdict |
|---|---|---|
| Classic B0 code browses `_carplay-ctrl._tcp` | project source, read-only | ESTABLISHED as observer behavior |
| B0 creates an authenticated, production Controller owner | absent | FALSE; implementation gap |
| Apple publicly documents iAP2 IP/port exchange replacing Bonjour | Apple WWDC 2023 | DOCUMENTED platform design |
| MU1440 stock supports that simplified message family | no target-native proof from this research | UNPROVEN; do not claim |
| WPA3-only use on MU1440 active AP is safe with current A3 parser | current parser cannot establish it | UNPROVEN; gate on stock AP capabilities and supported mode |
| No Bluetooth shutdown until negotiated iAP handoff | Apple classic guidance; target runtime untested | REQUIRED LIFECYCLE AUDIT, not an observed target test |

## D. Suggested debug comparison without credentials or personal identifiers

Ask an independent developer to distinguish *which* endpoint discovery mechanism they implemented, whether Controller Connect follows the correct authenticated peer, and whether the transport is transferred after verified session establishment. A small sanitized event-order timeline is useful:

```text
BT_LINK -> IAP2_IDENTIFIED -> MFI_AUTHENTICATED -> AP_CREDENTIALS_READY
        -> WLAN_ASSOCIATED -> (DNS_SD_RESOLVED | IAP2_ENDPOINT_RECEIVED)
        -> CTRL_CONNECT -> PAIR_VERIFIED -> CONTROL_SECURE
        -> IAP_RELAY_ACTIVE -> BT_HANDOFF_COMPLETE
```

**Important:** this is a normative diagnostic checklist, not an exact recovered Apple or MU1440 state enumeration. Reordering/parallel stages is possible and only a real trace can establish exact timing.

## Official source links

- [Apple: Developing Wireless CarPlay Systems (WWDC 2017)](https://developer.apple.com/videos/play/wwdc2017/717/)
- [Apple: Optimize CarPlay for vehicle systems (WWDC 2023), Connectivity section](https://developer.apple.com/videos/play/wwdc2023/10150/?time=600)

No proprietary Apple implementation code, firmware or confidential specification is reproduced in this note.
