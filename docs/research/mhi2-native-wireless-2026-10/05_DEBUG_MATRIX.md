# 05. Symptom-based debug matrix for a separately working Wireless build

Use stage-specific *non-sensitive* state transitions rather than screenshots or opaque "connected" flags. This table describes **suggested comparisons**, not a claim that this project's native wireless build passed these stages.

| Reported behavior | Inspect first | Common false positive | Best corresponding research |
|---|---|---|---|
| Phone pairs over Bluetooth but no iAP accessory flow | iAP 0x4000 node registration, SDP, channel lifetime | A visible Bluetooth profile/feature flag | Servicegraph and RFCOMM contract |
| First RFCOMM exchange works, then stalls | Borrowed RX lifetime, retained TX until completion, event generation, QNX read/write notify | Queue acceptance treated as send completion | Native provider callback model |
| USB CarPlay works but Wireless does not | Stock Type-3 plugin physical backend and active mm-ipod owner | Existing Type-4/USB handshake presumed equivalent | Type-3 ABI analysis |
| Wi-Fi prompt or AP handoff behaves inconsistently | Actual `0x5702/0x5703` sequence, supported active security, channel/interface and snapshot freshness | AP broadcast or parser READY status | A3 security discrepancy |
| Controller discovered, connection fails | SRV/TXT identity schema, peer matching, correct current interface/address | First DNS-SD result = trusted phone | B0 discovery findings |
| Pairing works once, fails on next attempt | Verify completion order, persisted peer state, stale endpoint and generation | Initial successful UI = correct reconnect | Secure control comparison |
| Visual session opens but commands or Siri behave oddly | Specific inbound/outbound iAP over Control, receiver session delegate, audio input/focus | Generic HTTP `SendCommand` exists | Receiver/DIO audit |
| Stop, ignition, power-cycle or phone switch hangs | Single process owner, callback quiescence, stock rollback, stale Wi-Fi/BT state | CI green or clean nominal shutdown | Control/rollback audit |

## Request only the minimum useful logs

For an independent implementation, a sanitized timeline can describe:

```text
T+0000ms: iAP service registered, current generation established
T+....ms: RFCOMM accepted / Type-3 open / identification started
T+....ms: wireless status request/response family observed
T+....ms: current AP interface and supported security *category* verified
T+....ms: DNS-SD add/resolve + matched peer generation
T+....ms: Controller Connect / Pair Setup / Pair Verify / encrypted ready
T+....ms: inbound iAP command completed / reconnect or stop
```

Do **not** log or request Wi-Fi passwords, SSIDs, MAC addresses, VIN, phone identifiers, pairing keys, certificate bytes, private key material, HTTP secrets or proprietary firmware dumps. Redact addresses and personal data before any public submission.
