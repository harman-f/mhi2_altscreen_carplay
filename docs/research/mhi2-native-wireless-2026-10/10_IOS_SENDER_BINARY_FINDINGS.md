# 10. iOS AirPlaySender/CarKit binary findings relevant to *Wireless* CarPlay

**Scope:** phone-side capability/compatibility decisions, negotiated secure Control session, accessory version identity and `iAPChannel`. No auxiliary screen, display geometry, video, cluster or Stream111 analysis is imported into this document. This is a dated **static analysis snapshot (October 2026)**, not an Apple specification or a phone-to-MU1440 live trace.

## 1. Exactly which iOS evidence was used

- **iOS 26.1 / CarKit and AirPlaySender public reverse-analysis material:** recovered CarKit feature conversion and SETUP `enabledFeatures` proposal/intersection semantics.
- **iOS 27.2 beta 2, build `24B5089g`, `iPhone14,2`, arm64e AirPlaySender:** exact software slice had AirPlaySender `LC_SOURCE_VERSION` **`1005.8.1.0.0`**. The historical extraction records multiple different standalone Mach-O SHA-256 values from **the same** dyld cache image depending on ObjC slide/rebase mode; only representation-qualified hashes should be compared. Later software may differ.
- **MU1440 exact stock receiver `libairplay.so`:** the advertising receiver-side `sourceVersion` is **`210.81`**; inbound phone `sourceVersion` is parsed/stored. No later compatibility branch reading its parsed clientVersion was recovered in the audited target binary. Absence of a recovered path is bounded static evidence, not a proof that all conceivable indirect behaviors are absent.

The evidence was obtained from reverse-engineering reports and rebuilds; **no Apple binary, private framework dump, firmware image, signing material or decompiled proprietary function body** is included here.

## 2. Three distinct identifiers; never mix them

| Property or feature | Meaning | What it can establish | What it cannot establish |
|---|---|---|---|
| AirPlay **global** feature bit 37, `CarPlayControl` | receiver advertises a protocol capability to initialize CarPlay Control | the *advertisement* is present | an authenticated Controller is connected |
| Global feature bit 38, pairing/control encryption | receiver advertises a pairing/encrypted-Control capability | a declared capability | Pair Setup/Verify is implemented and successful |
| Global feature bit 26, MFi-SAPv1 audio AES | legacy AirPlay/MFi-SAP audio security capability | advertised audio/keying path | a complete Wireless CarPlay session or valid accessory identity |
| CarKit feature `0x200` → SETUP `iAPChannel` | a separately negotiated modern logical iAP-over-AirPlay capability | accepted logical feature *if included in response* | the pre-WLAN Bluetooth iAP2 link, MFi authentication or complete bidirectional iAP relay |
| SETUP `enabledFeatures` | explicitly returned negotiated feature set (intersection of proposed/accepted) | a capability actually accepted for that session | downstream consumer implementation or persistence |
| Receiver `/info` `sourceVersion` / DNS-SD `srcvers` | compatibility generation advertised by head unit | input to sender's numeric compatibility gates | a magic unlock, proof of authentication, or guaranteed Wireless feature |

The numeric value `0x200` (CarKit capability mask) is **not** the same namespace as AirPlay global `1 << 37`. The iOS 26.1 recovered SETUP vocabulary includes independent tokens `iAPChannel`, `sessionManagement` and others. The original audit also tracked many display-specific tokens; those are intentionally omitted as unrelated to Wireless bootstrap.

## 3. What the sender actually does with SETUP feature negotiation

The audited iOS 26.1 sender constructs a proposed feature-key list, receives the accessory's `enabledFeatures` in SETUP, and tests individual tokens against the returned list. A requested feature need not have been accepted. It is wrong to conclude that a receiver supports a protocol operation merely because its **request** included a token. A modern `iAPChannel` check is potentially relevant to subsequent iAP-over-AirPlay handling; it is **not established** as a universal prerequisite for a Classic Wireless CarPlay connection.

Practical diagnostics for a working implementation: record **sanitized** (a) proposed feature keys, (b) accepted keys, (c) the stage at which Controller authentication completes, and (d) which actual typed iAP consumer receives and returns the first application message. Distinguish these from the earlier Bluetooth/iAP2 identification exchange.

## 4. Sender/receiver `sourceVersion` directions and exact gates

```text
Head unit  -> iPhone: receiver /info sourceVersion = "210.81" (stock MU1440)
iPhone     -> head unit: sender SETUP sourceVersion = "1005.8.1"
                          (only the researched iOS 27.2 beta-2 build)
```

Those are two **different peers' identities**. The exact iOS 27.2 beta-2 AirPlaySender static scan recovered **21** direct `isSourceVersionAtLeast` callsites, **3** older-than callsites and **3** direct copy-version calls. They govern generic endpoint, audio, remote-control, authentication compatibility and other behaviors. The highest directly recovered receiver-version threshold in that inventory was `800.1.0`. The comparative `950.7.1` persona and `1005.8.1` lie on the same side of all those direct numeric thresholds, but that does not mean their overall implementations are identical.

**Engineering conclusion:** spoofing the iPhone's newer sender version as the head unit's receiver version is not a justified step toward Wireless CarPlay. The receiver's actual capabilities and enabled session features remain authoritative. Whether a different persona affects a specific native Wireless path requires isolated testing; no such target vehicle experiment was completed here.

## 5. Secure session and iAP ownership boundary

The iOS-side findings support the need to distinguish multiple steps:

1. Bluetooth transport and iAP2 identification / existing MFi authentication (physical accessory channel).
2. WLAN credential request/reply and phone's network association.
3. Current Controller location (classic Bonjour or a newer iAP2-delivered endpoint; see [11](11_CONNECTION_FLOW_VARIANTS.md)).
4. Controller Connect, receiver-side Pair Setup/Verify, trusted-peer binding and encrypted Control transport.
5. iAP data routed over the active Control/AirPlay-side channel, with a matching inbound target consumer, return path and completion ownership; then eventual Bluetooth transport release according to protocol.

Exact MU1440 generic `POST /command` plus `AirPlayReceiverSessionSendCommand` is a valuable hook for step 5, **but its audited DIO event consumer lacks the particular `iAPSendMessage` implementation**. Nothing in the sender-side analysis closes that native gap or supplies a substitute MFi key.

## 6. What was intentionally excluded from this contribution

Do **not** transfer research on `altScreen`, `viewAreas`, instrument clusters, additional displays, CarPlay Ultra visual composition, screen type 111, video/UI transport, FPS, animation or timing. Those findings may be technically valid for a different project but do not help prove Wireless connection/session correctness. The independent scope boundary avoids reintroducing the unrelated media transport track.

## 7. Provenance and public verification

Internal primary authorities (titles supplied as research lineage only; **no private repository link**): *CarPlay negotiation and iOS sender audit* (2 October 2026), *sourceVersion compatibility gates* (2–3 October 2026), *iOS 27.2 AirPlaySender provenance closure* (3 October 2026), and *MU1440 Receiver/DIO Control contract* (7 October 2026). Exact firmware version and iOS build are essential qualifiers; numeric fields here come from static reconstruction.

Public standards/background: [Apple WWDC 2017: Developing Wireless CarPlay Systems](https://developer.apple.com/videos/play/wwdc2017/717/), [Apple WWDC 2023: Optimize CarPlay for vehicle systems](https://developer.apple.com/videos/play/wwdc2023/10150/), and the publicly documented DNS-SD specifications. Apple developer presentations describe intended system behavior; they do not verify an unobserved MU1440 implementation.
