# 09. Detailed native Wireless CarPlay architecture and implementation boundaries

**Scope:** Wireless connection, secure session and control-plane integration only. Target: classic MHI2 ER SKG13 P4526/MU1440, QNX 6.5 ARM32. **Frozen research, 9 October 2026.** This is a reconstruction of *interfaces and missing integration*, not a vehicle-proven complete implementation. No video, instrument-cluster, MOST or alternate-display data is used as evidence.

## 1. Three complementary architectures must not be conflated

1. **The installed MU1440 firmware:** stock Bluetooth/SDP/RFCOMM primitives, generic Bluetooth servicegraph without the earlier iAP service node, stock iAP2/Type-3 loader and MFi interface, access-point and receiver infrastructure, and the existing generic AirPlay Control route.
2. **The project's experimental A-side:** added iAP service node + RFCOMM/QNX endpoint + stock Type-3 transport bridge, bounded activation/recovery, an A3 credentials reader and B0 DNS-SD observer. Original control design was blocked despite green CI; revised offline candidate was conditionally approved for a single limited *future* diagnostic attempt, not a successful vehicle connection.
3. **The still-unimplemented full Wireless session:** stable controller/peer ownership, trustworthy discovery, controller Connect, target-side secure Pair Setup/Verify, encrypted Control session, bidirectional iAP-over-Control, Bluetooth-to-WLAN ownership transition, reconnect and coexistence. The existing wired CarPlay/receiver plumbing is only a potential integration substrate.

## 2. Component topology (MU1440-side, with phone boundary)

```text
  iPHONE / iOS                                      CLASSIC MHI2 / QNX 6.5
  ----------------------------                     ----------------------------------
  Bluetooth discovery / pairing                    bluetooth policy + BluetoothServices
  iAP2 accessory connection           RFCOMM        btstack SDP/RFCOMM
               <--------------------------------->  [missing stock node] iAP host 0x4000
                                                      |
                                                      v
                                             [prototype] RFCOMM provider
                                             borrowed RX / async-complete TX
                                                      |
                                              QNX owned raw endpoint
                                                      |
                                              Type-3 transport v2
                                                      |
                                              stock mm-ipod + iAP2 driver
  iAP2 identification + stock MFi    <------------>  stock ACP/MFi authentication
  iAP2 0x5702 request                ------------->  stock active AP producer
  iAP2 0x5703 reply                  <-------------  active WLAN credentials/channel
               
  Wi-Fi client association           <============>  existing access point / DHCP
                 |
                 | Classic service-discovery route (NOT the only possible route)
  phone Controller service           --DNS-SD---->  [prototype] B0 observer
  current trusted Controller         <---TCP----->  [missing] long-lived owner/peer state
                 |
  Controller Connect / verification  <----------->  [missing] target secure session wiring
  encrypted Control / iAP relay      <----------->  stock receiver generic /command
                                                      + stock SendCommand
                                                      + [missing] specific iAP consumer
                 |
             ACTIVE WIRELESS CONTROL SESSION (NOT END-TO-END PROVEN HERE)
```

A modern **simplified IP/port handoff** can replace the Bonjour *discovery segment* with information exchanged over existing iAP2. It does **not** eliminate secure CarPlay Controller/session requirements. That newer handoff mechanism has not been identified as implemented by this MU1440 research prototype; see [11_CONNECTION_FLOW_VARIANTS.md](11_CONNECTION_FLOW_VARIANTS.md).

## 3. Detailed stage table: real stock, reconstructed, missing

| Stage | Initiator / transport | MU1440 owner or component | What our research establishes | Complete hardware proof? |
|---|---|---|---|---|
| P0 Bluetooth policy | head-unit BluetoothServices | stock `bluetooth` + `btstack` | servicegraph exists, iAP type `0x4000` survives, absent node in target constructor; config `enableIap=false` | NO for new node |
| P1 SDP/RFCOMM | phone and btstack | added native node/provider | event and lifecycle ABI reconstructed; RX borrowed, TX completion-owned | NO |
| P2 iAP2 physical transport | peer RFCOMM bytes | QNX endpoint + project Type-3 adapter + stock mm-ipod | loader/transport v2 seam and offline candidate source identified | NO |
| P3 accessory identification/MFi | both, over iAP2 | stock iAP2/ACP | stock code path exists; no new keys/crypto replacement | NO complete wireless identification |
| P4 AP request/credentials | phone requests, unit responds over iAP2 | existing WLAN/AP producer, `0x5702` / `0x5703` | actual producer formats; known A3 security parse defect | NO live current-AP exchange |
| P5 Wi-Fi association | phone over WLAN | existing AP, DHCP/IP | compatible infrastructure exists | NO associated target session |
| P6 Controller endpoint location | classic DNS-SD *or* newer iAP2 IP/port exchange | B0 observer only; full Controller owner MISSING | `_carplay-ctrl._tcp` observed in research model; B0 lacks robust identity/add/remove | NO |
| P7 Controller Connect | head unit to current phone Controller | session owner MISSING | distinct `/ctrl-int/1/connect` operation in compared implementation | NO |
| P8 secure setup and verification | receiver-side server | target Pair Setup/Verify and trusted peer store MISSING | expected server-side role and completion-before-encryption order reconstructed from a *different* stock firmware | NO |
| P9 bidirectional iAP over Control | receiver / phone | stock `/command` + `SendCommand`, target iAP consumer MISSING | exact MU1440 generic route and typed delegate statically mapped | NO |
| P10 steady-state/reconnect | both | shared peer/controller/transport owner MISSING | proposed generation/cancel/error contracts; no production state machine | NO |

These stages are **not all necessarily serialized**. iAP2 and network/controller operations may overlap, and the Bluetooth iAP2 transport must not be closed just because Wi-Fi association has succeeded. Transport handover is its own negotiated lifecycle. Do not infer exact runtime order from this decomposition without real traces.

## 4. MU1440 Bluetooth servicegraph: the first true missing physical seam

The earlier MHI2 family built an `IapServices` object as one normal service in the `BluetoothServices` owner graph. The target retains ordinary type-based connectability dispatch (`serviceType == requestedService`, followed by the service hook), but no longer builds the known dedicated iAP node. The service identifier `0x4000` remains in the target's vocabulary. A new service node must observe native registration/deregistration, owner identity, stop/detach and event thread lifetime; a Boolean config change alone does not prove registration.

Our candidate provider owns one active RFCOMM peer, bounded RX/TX memory, cancellation and generations. Incoming event bytes are borrowed; outgoing buffers survive submission until completion. Its QNX Resource Manager endpoint is not a substitute for the downstream stock Type-3 protocol ABI. The short provider `.c` file **includes six `.inc` implementation units**: `prelude`, `setup`, `lifecycle`, `streams`, `events` and `qnx`; any future rights-cleared release must preserve those dependencies and their tests.

## 5. Receiver/session seam: why generic commands are not enough

Exact MU1440 includes a route for an existing-session `POST /command` carrying an Apple binary property list with typed `type`/`params`. Unknown commands can reach its Session PlatformControl delegate and DIO queue. The outbound `AirPlayReceiverSessionSendCommand` path uses the active session HTTP client and optionally completes asynchronously. A statically recovered `0x38`-byte/14-word ARM32 delegate contains ten mapped callbacks.

**But** the inspected stock DIO event consumer does not implement the specific `iAPSendMessage` operation. An accepted generic HTTP command or a socket write therefore does not demonstrate that the current stock iAP2 owner consumed the data or sent a response back. A correct adapter must bind one trusted peer and owner generation, a typed iAP payload, response completion, byte/queue limits, teardown and a reverse path. Independently, the target still needs working secure session setup/verification/peer storage and any required receiver-side extension.

## 6. Failure containment and observed gaps

- **Service exists, no iAP link:** check actual SDP registration, selected RFCOMM channel, current owner, raw endpoint, Type-3 attach and stock identification, in that order.
- **WLAN credentials inconsistent:** the prototype A3 parser ignores a stock `Protocol=2`/WEP producer field and may report unsupported security as open; reject that. Also bind current AP security, channel, interface and snapshot generation rather than concatenating stale fields.
- **Controller found, not trusted:** B0 read-only DNS-SD observation currently picks an early resolved candidate, with inadequate typed device-ID validation, Add/Remove handling and scoped IPv6. Presence of DNS-SD is not authentication.
- **Pairing/reconnect failure:** compare Connect vs Pair Setup vs Pair Verify roles and the ordering of Verify-response completion and encrypted transport activation. Scope any stored peer identity to the current runtime generation.
- **Transport owner goes stale:** pending native TX callbacks, selected Controller endpoint, WLAN AP state and iAP owner must invalidate together on disconnect/teardown; do not reuse stale addresses or buffer pointers.

## 7. Evidence classes / limits

**EXACT TARGET STATIC:** original firmware servicegraph, stock transport/API, receiver route/delegate and known absence in inspected functions. **OFFLINE PROJECT TEST:** original iAP/RFCOMM prototype and candidate recovery tests. **COMPARATIVE STATIC:** receiver Pair Setup/Verify implementation in a different stock firmware. **OPEN / NOT VEHICLE PROVEN:** actual complete native Wireless session, secure pairing/identity, IP handoff and reconnection. No claim that an external developer's photographs validate this prototype.

Source details were independently consolidated from private reports dated 1–7 October 2026; original OEM binary bodies and unrelated third-party code are intentionally not reproduced. Related: [01 Bluetooth](01_BLUETOOTH_RFCOMM.md), [02 iAP2](02_IAP2_MFI_WIFI.md), [03 Receiver](03_RECEIVER_PAIRING_CONTROL.md), [10 iOS review](10_IOS_SENDER_BINARY_FINDINGS.md).
