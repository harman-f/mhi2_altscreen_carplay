# References and reproducibility boundaries

## Public, independently retrievable references

- [Apple WWDC 2017: Developing Wireless CarPlay Systems](https://developer.apple.com/videos/play/wwdc2017/717/): classic pairing, Bluetooth/iAP2, WLAN credential and Bonjour Controller flow.
- [Apple WWDC 2023: Optimize CarPlay for vehicle systems](https://developer.apple.com/videos/play/wwdc2023/10150/?time=600): simplified iAP2 IP/port endpoint exchange, support for WPA3-only networks, reconnect/interference guidance.

- [IETF RFC 6763 — DNS-Based Service Discovery](https://www.rfc-editor.org/rfc/rfc6763.html): service instance PTR/SRV/TXT representation and browse/update semantics.
- [IETF RFC 6762 — Multicast DNS](https://www.rfc-editor.org/rfc/rfc6762.html): link-local multicast discovery foundations.
- [Apple DNS Service Discovery Programming Guide](https://developer.apple.com/library/archive/documentation/Networking/Conceptual/dns_discovery_api/Introduction.html): browse/resolve/register API behavior.
- [QNX Neutrino Resource Managers](https://qnx.com/developers/docs/6.4.0/neutrino/prog/resmgr.html): resource-manager and dispatch concepts (older public release; not a claim of complete 6.5 ABI identity).
- [QNX `resmgr_io_funcs_t` documentation](https://qdn.qnx.com/developers/docs/7.1/com.qnx.doc.neutrino.lib_ref/topic/r/resmgr_io_funcs_t.html): conceptual IO handler classes (different version; verify exact target signatures).

These references support **generic DNS-SD and QNX concepts**. They do not independently establish reverse-engineered Apple CarPlay pairing fields, secret cryptographic values, private stack method IDs or exact proprietary target ABIs.

## Primary research evidence (not public source dumps)

The original project studied the following exact target component classes: Bluetooth services, `btstack`, `connectionmanager`, `mm-ipod`, `ipod-drvr-iap2.so`, `libairplay.so` and the DIO/control consumer. Key internal report titles include *MU1440 BTSTACK SERVICEGRAPH ACTIVATION CLOSURE* (2026-10-03), *MU1440 GENERIC RFCOMM SERVER ABI* (2026-10-02), *MU1440 STOCK IAP2 TRANSPORT ABI AND CONFIG* (2026-10-01), *MU1440 RECEIVER DIO CONTRACT* (2026-10-07), and the *MH2P/MU1440 TRANSFER AUDIT* (2026-10-07). A separate independent control review and corrected-control validation (2026-10-05/06) establish the limits of the project-built candidate.

A full internal file/commit/blob index is maintained outside this candidate public tree. This public documentation intentionally contains no private repository URLs, private account identifiers, proprietary binaries, log captures, extracted functions or competitor-package names. Relevant source-code licensing notices must be supplied **if and when actual source is legally cleared and included**, rather than erasing mandatory attribution.

The iOS-side targeted research also used the documented title *CarPlay negotiation and iOS 27.2 sender audit* (2026-10-02), *sourceVersion compatibility gates* and *AirPlaySender binary provenance closure* (2026-10-03); see [10_IOS_SENDER_BINARY_FINDINGS.md](10_IOS_SENDER_BINARY_FINDINGS.md) for scope limits.
