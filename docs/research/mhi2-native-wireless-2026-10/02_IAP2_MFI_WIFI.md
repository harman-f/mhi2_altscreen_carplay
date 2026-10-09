# 02. Stock Type-3 iAP2, MFi and WLAN credential handoff

**Evidence:** exact-target static binary/config analysis and project-authored offline transport prototype. Not a vehicle-validated Wireless CarPlay bootstrap.

## Use what stock MU1440 already provides

MU1440 contains `mm-ipod`, `ipod-drvr-iap2.so`, the generic v2 `ipod_transport` plugin mechanism and existing accessory identification/MFi/ACP components. The custom Bluetooth-side research adapter uses a stock-compatible **Type-3 transport** over a native raw RFCOMM byte endpoint; it is not an alternative MFi authentication implementation and provides no authentication-key or commercial-license bypass.

The stock transport loader does not automatically provide a working Bluetooth physical backend just because its generic API exists. In particular, stock USB iAP2 functionality must not be considered evidence that the Type-3/RFCOMM path is connected.

## Intended diagnostic milestones

| Milestone | Evidence to seek | Not sufficient |
|---|---|---|
| Bluetooth iAP endpoint | Accepted, openable RFCOMM channel and owned raw endpoint | SDP, `enableIap`, strings only |
| Type-3 transport | Bidirectional framing through the specific active stock plugin | USB accessory success |
| Accessory identification | Actual target identification and current transport identity | Linked OEM MFi library on disk |
| WLAN credential request | Stock wireless configuration request `0x5702` | AP exists or SSID is broadcast |
| WLAN credential response | Matching, current and internally consistent `0x5703` | Stale or concatenated AP fields |
| Wi-Fi association | Phone connected to intended active AP/interface | Passive DNS-SD or mDNS discovery |

## A concrete A3 parser defect worth testing

The exact stock AP-producer analysis showed an active-format field `Protocol=2` for WEP alongside WPA/WPA2-related representations; a prototype A3 credential parser does **not** interpret the `Protocol` field and can misclassify an unsupported WEP state as open when expected PSK/cipher markers are missing. It also does not prove that all returned properties belong to one current AP configuration generation.

The safe contract for a production implementation is: an atomic AP snapshot, explicit supported security family, coherent channel and interface, credential freshness, and rejection of unknown/conflicting/unsupported combinations. **The prototype's `READY` output is not a security or association proof.** If a network is not demonstrably in a supported mode, do not attempt the bootstrap on the strength of the parser result alone.

Some stock producer channel fields use a compound `Channel=<number>,<suffix>` representation. Rejecting every non-numeric character or assuming a plain integer can be another compatibility error. The correct field grammar and final channel must be validated against the actual producer, not guessed.

## Limits

The project's repaired source was only conditionally reviewed for a narrow A3/B0 vehicle experiment. No successful phone-to-AP handoff and no complete secure Wireless CarPlay session were reported in this frozen research state.

## Endpoint discovery is a separate, potentially version-dependent step

An older classic flow proceeds from WLAN association to Bonjour/DNS-SD Controller discovery. Apple also documents a newer simplified flow that can convey Controller IP address and port over iAP2, without Bonjour. This target prototype has only a B0 Bonjour observer; it does **not** prove support for the simplified route. See [11_CONNECTION_FLOW_VARIANTS.md](11_CONNECTION_FLOW_VARIANTS.md).

## Related published source and stock component mapping

The analyzed stock modules were `mm-ipod`, `ipod-drvr-iap2.so`, the ACP/MFi path and the AP configuration producer; **no OEM binary is published**. Our source counterparts are the [Type-3 transport adapter](prototype/probe/transport-btstream/ipod_transport_btstream.c) / [ABI header](prototype/probe/transport-btstream/ipod_transport_v2.h), [MFi dynamic adapter](prototype/probe/src/mhi2_mfi_airplay.c), [A3 credential parser](prototype/probe/a3-credentials/mhi2_wcp_a3_credentials.c) and [runtime iAP2 config](prototype/probe/runtime-iap2-config/mhi2_wcp_iap2_runtime_config.c). [Complete binary-to-source map](FIRMWARE_SOURCE_CROSS_REFERENCE.md).
