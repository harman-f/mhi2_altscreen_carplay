# 04. DNS-SD Controller discovery, peer binding and reconnect

The experimental project `B0` tool is a **read-only observer** for `_carplay-ctrl._tcp`; it is not a trusted controller directory or a production connection owner. **It covers the classic Bonjour discovery path only.** Apple also documents an iAP2 IP/port handoff that can bypass Bonjour; this was not proven on MU1440. See [11_CONNECTION_FLOW_VARIANTS.md](11_CONNECTION_FLOW_VARIANTS.md).

## Known observer shortcomings

- It selects an early address/resolve candidate; this is not a complete service collection with robust updates/removal.
- Text-based matching against an expected Bluetooth MAC was not demonstrated as a reliable structured `deviceID` match; formatting and key boundaries matter. A positive substring comparison is not a pairing/authentication proof.
- IPv6 address presentation may drop scope information. The interface index and address family matter when the advertised device is link-local.
- DNS-SD Add/Remove, address changes, callback generation, controller stop and multi-device candidate selection need an explicit, long-lived owner.
- The observer uses wall-clock timeout behavior and has narrower file descriptor/error-path robustness than a production daemon would require.

These shortcomings were identified in original source plus exact-firmware comparison. The protocol-level distinction is simple: **advertising a service does not authenticate the advertising peer.** DNS-SD identifies network service candidates; secure pairing and session ownership establish trust separately.

## Suggested peer lifecycle contract

```text
BR_BEFORE: no selected controller
  DISCOVER -> candidate(s), each tagged by interface + generation
  RESOLVE -> validated current address/port and structured service TXT
  MATCH   -> correlate actual Bluetooth identity and allowed trust state
  SELECT  -> exactly one current controller owner
  SECURE  -> pairing/verification and encrypted session completion
  ACTIVE  -> control and iAP messages belong to same owner/generation
  REMOVE/STOP/FAIL -> invalidate candidate, cancel callbacks, release owner
```

This is a **research checklist, not a reverse-engineered complete target state machine**.

## Useful scenarios

1. Two visible phones, only one current RFCOMM peer: ensure discovery cannot select the other peer.
2. Controller service is removed and recreated: stale SRV/TXT and first-result caching must not be reused.
3. IPv6 link-local response arrives: retain interface scope and do not silently substitute a different address.
4. Phone leaves and rejoins the AP: both controller identity and current AP generation need revalidation.
5. BT disconnect occurs during a pending send: discard late callbacks from the previous generation and cleanly detach the QNX endpoint.

See [RFC 6763](https://www.rfc-editor.org/rfc/rfc6763.html) for DNS-SD instance/TXT/SRV semantics and [Apple's DNS-SD programming guide](https://developer.apple.com/library/archive/documentation/Networking/Conceptual/dns_discovery_api/Introduction.html) for browser/resolve APIs; these are public protocol references, not proof of private CarPlay pairing semantics.
