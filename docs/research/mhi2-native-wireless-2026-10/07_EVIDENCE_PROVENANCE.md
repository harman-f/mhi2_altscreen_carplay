# 07. Evidence grades, provenance and unimplemented functions

**Frozen:** 2026-10-09. **Target:** classic MHI2 ER SKG13 P4526, MU1440, QNX6.5/ARM32. The observations are specific to this firmware and must not be generalized across MHI2, MHI2Q, MHI2P or other versions without revalidating symbols, ABI, service ownership and stock credentials.

| Topic | Evidence | Project's completion state |
|---|---|---|
| Bluetooth service type 0x4000 + servicegraph delta | Exact-firmware **STATIC** comparison | Provider architecture characterized; not a working live session |
| RFCOMM callbacks and Resource Manager interface | **STATIC** callback analysis + **OFFLINE** prototype/test | Target runtime integration unproven |
| Stock Type-3 plugin and iAP2/MFi/ACP components | Exact-firmware **STATIC** interface inventory | Component presence and intended interface, not phone-to-AP proof |
| 0x5702/0x5703 WLAN messages, AP producer formats | Exact target **STATIC** inspection | Experimental A3 parser has known security/freshness bug |
| `_carplay-ctrl._tcp` browse/resolve | **OFFLINE** read-only B0 code analysis | No authenticated controller directory |
| Generic MU1440 `/command` / SendCommand | **STATIC** target receiver and DIO audit | An iAPSendMessage target consumer remains missing |
| Controller Connect, Pair Setup/Verify, encrypted channel | **STATIC** semantics from a different stock firmware family | Secure server/session not implemented or target-validated |
| Reconnect, multiple devices, suspension, audio/mic | Static feature/interface evidence only | End-to-end acceptance **OPEN** |
| Full Wireless CarPlay in target vehicle | **NO VERIFIED VEHICLE EVIDENCE** from this research | **NOT COMPLETE** |

## Independent control audit: do not mistake green CI for vehicle acceptance

The initial 2026-10-05 candidate passed CI but received an independent **BLOCK** for teardown/control defects. The corrected 2026-10-06 source revision received a bounded **PASS_WITH_FIXES** review limited to a carefully controlled first A3/B0 diagnostic experiment. That outcome **does not mean the vehicle test was executed** or that full Wireless CarPlay works.

No separate authenticated Pair Setup/Verify server, Controller owner, target DIO iAP command consumer, trusted peerstore or bidirectional end-to-end iAP-over-AirPlay bridge was verified as a working integrated product. No authenticated Wi-Fi session can be inferred from a DNS-SD or AP-ready observation.

## Source audit and attribution rules

All exact-target findings above originate in archived static/offline research conducted on the stated firmware. General protocol references are listed separately; the primary OEM binaries and generated proprietary decompilations are **not distributed**. Reproducibility of private findings requires a legitimately held exact firmware image and independent analysis.

The reviewed project-authored prototype source is now published in [prototype/](prototype/README.md), under this repository's GPL-3.0-or-later terms. Its source commit, per-file source blob IDs, exported SHA-256 values, scope review and one explicitly excluded firmware patch-builder are documented in the prototype directory. The source publication does not include OEM binaries or implementation bodies, MFi certificate/key material, real credentials or private repository history.

Do not distribute device keys, certification material, personal pairing records, confidential firmware, local paths, raw vehicle logs or third-party copyrighted implementation bodies. A clean, new public Git branch should contain only reviewed material; do not copy private repository history.

## Status

This effort is **paused**. There is no promised maintenance, product support, reproducible real-car installer or compatibility guarantee. A separately demonstrated third-party Wireless build may be further along; its specific firmware, internal architecture and outstanding defects have not been independently assessed by this research.
