# Native Wireless CarPlay on classic MHI2: research handoff

**Frozen research snapshot — 9 October 2026 — not a release, installer or maintained project.**

This material may be useful to developers who already have Wireless CarPlay connected on a classic MHI2 head unit but are still diagnosing integration and lifecycle problems. It documents exact-target interface observations, independently reviewed defects and explicitly incomplete prototype components. **This project did not demonstrate a complete native Wireless CarPlay session on its target vehicle.** No production support or further implementation work is currently planned.

## Strict scope

**Included:** Bluetooth iAP service activation, SDP/RFCOMM, target-native iAP2/Type-3 transport and existing MFi/ACP, WLAN credential exchange, Bonjour/DNS-SD peer discovery, CarPlayControl receiver and secure-session boundaries, QNX owner lifecycle, reconnect diagnostics and isolated tests.

**Excluded entirely:** Virtual Cockpit, instrument cluster, MOST, auxiliary/alternate displays, Stream111, video decoding/encoding, H.264, MPEG-TS, FPS, clock/PTS/PCR, stutter, navigation maps, RGI, UI feature experiments and unrelated emulation. None of those results is evidence of Wireless CarPlay connectivity and none is part of this contribution.

## Start here

1. [Bluetooth servicegraph and RFCOMM](01_BLUETOOTH_RFCOMM.md) — where native iAP registration and byte ownership happen.
2. [Stock Type-3 iAP2 and Wi-Fi handoff](02_IAP2_MFI_WIFI.md) — reuse the existing accessory stack and verify the active AP.
3. [Receiver, CarPlayControl and pairing](03_RECEIVER_PAIRING_CONTROL.md) — the generic MU1440 command interface and the missing targeted consumer.
4. [Discovery and reconnect](04_DISCOVERY_RECONNECT.md) — known shortcomings in a read-only observer.
5. [Symptom-driven debugging](05_DEBUG_MATRIX.md) — evidence gates to compare with an independently working implementation.
6. [QNX process lifecycle](06_QNX_RECOVERY.md) — only for native Bluetooth/iAP resource management.
7. [Validation, limitations and provenance](07_EVIDENCE_PROVENANCE.md) — which statements are static, offline-tested or actually observed.
8. [Source and test eligibility](08_SOURCE_TEST_CANDIDATES.md) — what could be shared later after clearance.
9. [End-to-end native Wireless architecture](09_END_TO_END_ARCHITECTURE.md) — detailed owners, boundaries, transport handoff and per-stage proof.
10. [iOS sender binary findings](10_IOS_SENDER_BINARY_FINDINGS.md) — independent capability namespaces, `iAPChannel`, CarPlayControl and version gates.
11. [Classic vs simplified Wireless connection](11_CONNECTION_FLOW_VARIANTS.md) — Bonjour and iAP2 endpoint delivery are distinct alternatives.
12. [Regression-test definitions](REGRESSION_CASES.tsv) — 22 diagnostic cases; **not executed as passing tests**.
13. [Public reference sources](REFERENCES.md).

## Short architecture map (research, not a completed feature)

For a full component/owner diagram and step-by-step proof matrix, use [09_END_TO_END_ARCHITECTURE.md](09_END_TO_END_ARCHITECTURE.md); the simplified flow is separately described in [11_CONNECTION_FLOW_VARIANTS.md](11_CONNECTION_FLOW_VARIANTS.md).

```text
Phone Bluetooth / iAP
       |
Service type 0x4000 + SDP/RFCOMM
       |
QNX raw endpoint -> stock Type-3 transport -> stock mm-ipod / iAP2 / MFi
       |
0x5702 / 0x5703 -> stock Wi-Fi access point
       |
Classic: DNS-SD _carplay-ctrl._tcp (or newer iAP2 IP/port handoff)
       |
Current Controller identity / peer state
       |
[INCOMPLETE] Controller Connect, Pair Setup/Verify, encrypted session
       |
[INCOMPLETE] receiver/DIO bidirectional iAP-over-Control consumer
```

The endpoint and servicegraph portions exist as offline research/prototype code; *the lower secure-session portion has not been implemented and validated end to end by this project*. Working UI photos from another implementation do not validate the present code.

**Publication note:** this is a clean documentation draft only. Original C sources and tests have not been cleared or copied into this public staging directory; see `08_SOURCE_TEST_CANDIDATES.md`. No OEM firmware, protected decompiled function bodies, keys, credentials, vehicle identifiers or commercial/third-party binary payloads are included.
