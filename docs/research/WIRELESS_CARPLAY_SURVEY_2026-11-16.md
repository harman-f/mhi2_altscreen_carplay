# AltScreen Cluster Atlas — wireless CarPlay / Android Auto evidence refresh

**Snapshot:** 2026-11-16 (Europe/Berlin)  
**Scope:** public source/release/issue verification; no vehicle test or firmware installation performed in this survey.  
**Base:** the 58-repository, 22-capability Atlas edition in `docs/index.html` (2026-11-04). The existing matrix is **not** represented as revalidated for every one of its 58 entries. This addendum records reviewed changes and explicit source gaps.

## Terminology and evidence policy

Four different implementations must not be collapsed into a single "wireless" checkbox:

1. **Native wireless receiver in the head unit:** iPhone Bluetooth/iAP2/MFi bootstrap followed by Wi-Fi/AirPlay directly with the MHI2/MHI2Q receiver, with no USB CarPlay dongle.
2. **USB wireless adapter:** iPhone communicates over Bluetooth/Wi-Fi to an adapter that presents a USB-side CarPlay session to the car. A working central display does not establish cluster video.
3. **Wireless AltScreen relay:** adapter must negotiate a secondary display, establish Type-111 video, transcode/relay encrypted frames and preserve controls/commands across independent phone/car sessions. Car-side software must already accept the secondary stream.
4. **Wireless Android Auto:** related connectivity but a different projection/control/video protocol, with independent cluster-map and decoder requirements.

Evidence tiers: `SOURCE_ONLY` (documented implementation) → `OFFLINE_TEST` → `RELEASED` → `TARGET_RUNTIME` → `VEHICLE_VISUAL` → `END_TO_END_ACCEPTED`. Each feature must name the exact firmware, phone/adapter, build, OS/app and evidence tier. An HTTP updater acknowledgment or build PASS is **not** target runtime or visible output. Different dongle chipsets and firmware generations are not binary-compatible merely because the marketing name says AX1800M or smartBox.

## External source delta reviewed on 2026-11-16

| Repository / primary dated evidence | Platform and route | Latest substantiated result | Remaining proof boundary |
| --- | --- | --- | --- |
| [luka-dev/mib2q-carplay-rgi — wireless architecture](https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/docs/wireless-carplay/README.md), [release MHI2Q-2026-11-04](https://github.com/luka-dev/mib2q-carplay-rgi/releases/tag/MHI2Q-2026-11-04) | MHI2Q / native receiver | Stock AirPlay 210.81 retained; smartphone_integrator is single CarPlay child owner, Rust daemon handles iAP2/MFi/Wi-Fi bootstrap, Bluetooth graft supplies RFCOMM. Main video/input/AltScreen partly observed in a vehicle, wider lab suite covers audio/microphone/reconnect. Nov 5 release refines AltScreen start/reconnect and VC placement. | Native wireless **not fully accepted**: MainHigh control/RTCP, connection policy, HMI audio focus and sustained combined vehicle sessions remain in completion ledger. Do not read the cluster release notes as proof of full wireless. |
| [luka-dev #81](https://github.com/luka-dev/mib2q-carplay-rgi/issues/81) (opened 2026-10-28) | MHI2Q / third-party Carlinkit AutoKit over USB | Vehicle reports on P5152/MU1329 and iOS 27, plus adapter detection and visual/control refinements. | Adapter route is not equivalent to Luka's native wireless receiver and field observations are specific to the reported setup. |
| [joeyQuery/MHI2-wirelessCarPlay](https://github.com/joeyQuery/MHI2-wirelessCarPlay) | Classic Harman MHI2 / native-receiver RE, tested source family MU0678 | Marvell 8787, uap0, Bluetooth iAP, iAP2 resources, Bonjour, AirPlay and USB CarPlay network components identified. Runtime endpoint reaches `CIapBTChannel::open64()`. | Endpoint → DIO resource-manager path and AirPlay/multicast interface selection unresolved; **not working end-to-end**. Classic MHI2 is not interchangeable with MHI2Q/Cinemo. This is a **new Atlas candidate absent from the 58 rows**. |
| [OMKE/wireless-carplay-virtual-cockpit](https://github.com/OMKE/wireless-carplay-virtual-cockpit) | Suding AX1800M USB adapter to Audi MHI2Q cluster | 2026-10-19 vehicle report: wireless Google Maps cluster stream 111 and steering-wheel zoom. The custom adapter app advertises cluster geometry, receives encrypted 111, relays the car-side 111. Original car-side AltScreen implementation is a prerequisite. | One reported vehicle/adapter/firmware; control requests in car→phone direction (e.g. view-area changes) not forwarded. Fixed Audi geometry is not a Skoda MU1440 profile. Already in Atlas; evidence detail needs updated annotation. |
| [kamgurgul/mib2q-carplay](https://github.com/kamgurgul/mib2q-carplay), [v1.4](https://github.com/kamgurgul/mib2q-carplay/releases/tag/v1.4), [v1.4.1](https://github.com/kamgurgul/mib2q-carplay/releases/tag/v1.4.1) | MHI2Q / wired CP + Android Auto, external adapters | v1.4 (2026-11-04) documents HW301 v1176: second screen, HU cluster controls, Type-111 route-guidance proxy including HUD/lanes, adapter-specific firmware. v1.4.1 (2026-11-07) changes AA hardware-decoder startup and the 2-minute reconnect; published bench tests pass. Other documented reports: Baseus, Carlinkit 5.0/2Air, Ottocast Mini, AAWireless TWO+ **test firmware**. | v1.4.1 fresh AA scenarios expressly await in-car validation; OEM AAWireless firmware may not yet contain the tested fix. HW301 ARM images are not Suding AX1800M/MIPS images. Supported adapters must be listed by precise firmware. |
| [catplay-labs/catplay](https://github.com/catplay-labs/catplay), [v0.29.0](https://github.com/catplay-labs/catplay/releases/tag/v0.29.0) (2026-11-11) | Third-party dongle replacement stack, protocol library, multiple hardware ports | Oct 27 source work introduced AltScreen, view-area/controller negotiation, forceKeyFrame/display UUID/zoom and proxy support. v0.23/0.24 fixed MHI2 audio and negotiation paths; v0.26 made audio proxy event-driven; v0.28 adjusted Bonjour IPv4 selection; v0.29 is latest inspected firmware-packaging release. | MHI2 vehicle-specific Type-111 output and exact Suding board compatibility must be verified. The stable Ingenic AX1800M **marketing family** must not be equated with every vendor's SoC/flash, NOR layout or OTA image. **New Atlas candidate absent from 58 rows.** |
| [omonob/MHI2-Carplay-Maps](https://github.com/omonob/MHI2-Carplay-Maps/releases) | Classic MHI2 / native cluster wired, separate wireless work | Stable 2.0.1 and experimental 2.1.0-rc.7 cover VC rendering/information features. Wireless appears as a test/read switch, not a shipped native wireless service. | No evidence here of complete native wireless MHI2 reception; firmware/cluster support and test-only switches must not be scored as released wireless. |
| [harman-f/harman-ax1800m-adapter-checker](https://github.com/harman-f/harman-ax1800m-adapter-checker), [RC2](https://github.com/harman-f/harman-ax1800m-adapter-checker/releases/tag/ax1800m-miniultra-v0.5-rc2) | Suding AX1800M-specific experimental stream-111 relay | Public source and host/MIPS build checks for v0.5 RC2, including corrected car→phone control ingress and stock-first delayed fallback. A firmware update acknowledgment was reported; source/release presence is verifiable. | **No documented target-runtime and visible-VC acceptance of RC2**; keepalive/session lifecycle and menu-driven dynamic UI commands need observed verification. No automatic compatibility claim for any stock adapter. |

### Dated watch anchors

- **2026-10-19:** OMKE adapter-specific Audi MHI2Q vehicle success (Type111, wireless VC).
- **2026-10-28/29:** Luka #81 Carlinkit field report; Luka's native architecture report marks acceptance incomplete.
- **2026-11-04/05:** Kamgurgul 1.4 (HW301 v1176), Luka MHI2Q-2026-11-04 cluster refinements.
- **2026-11-07:** Kamgurgul 1.4.1 Android Auto decoder start/reconnect change; some scenarios bench-only.
- **2026-11-11:** CatPlay v0.29.0 release; v0.28 Bonjour and v0.26 audio proxy changes remain relevant.

## Engineering relevance: native Harman MHI2 vs adapter

**Native MHI2 receiver research:** investigate Bluetooth RFCOMM/iAP2 ownership, how the current DIO transport is selected, Wi-Fi/Bonjour address/interface routing, MFi session identity and production lifecycle. Do not transplant MHI2Q/Cinemo or MH2P binaries into QNX 6.5 Tegra-based classic MHI2 without ABI proof. A stock WLAN AP is not itself a working wireless CarPlay implementation.

**Adapter stream 111:** keep transport 110 (main video/audio) and stream 111 (cluster) separately alive. Require phone/car session-generation tags, exact HU 111 display descriptor, car-originated `showUI/stopUI/updateViewArea/forceKeyFrame` relay and preservation of route/ETA/zoom/VC layouts. Distinguish 110-only selective teardown from full AirPlay teardown, and keepalive expiry from an idle video socket. Do not synthesize keepalives or ignore real teardown without evidence.

**Android Auto:** track native AA secondary display separately from CarPlay. Relevant comparison is the MHI2Q AA receiver/hardware-decoder and independent cluster routing; successful CarPlay Type111 is not evidence of AA cluster display support.

## Proposed matrix improvement (not yet silently applied)

Keep the currently 58 reviewed row IDs and 22 original capabilities until per-row regression review. In a follow-up, add dedicated public entries for **joeyQuery/MHI2-wirelessCarPlay** and **catplay-labs/catplay** with `SOURCE_ONLY` or `PARTIAL` status. The current binary wireless column should be split for new editions into: `native-wireless`, `USB-adapter-compatible`, `adapter-secondary-video`, `HU→phone-control-relay`, `wireless-RGI/HUD`, `wireless-AA`, `confirmed-vehicle`; source evidence must identify hardware, firmware, phone/iOS and version. An unknown status must remain unknown, not "No".

## Consolidation / next source-only gates

1. Treat the **58-row HTML on the November 4 branch as the Atlas working source**, preserving its existing dark responsive layout, sorting/filtering, technical cards, lineage graph and timeline. Do not auto-publish or merge it before browser review.
2. Keep dated external source anchors and release tags in this document. Review change deltas rather than cloning speculative forks or bundling third-party binaries.
3. Recheck Luka's wireless completion ledger and HMI2-specific Joey trace; record whether the **actual end-to-end native blocker** moved, not only code activity.
4. Recheck Kamgurgul's specific HW301, Baseus, Carlinkit and AAWireless/Ottocast evidence separately from Android Auto's bench results.
5. Recheck CatPlay's exact *supported chipsets and vendor IDs* against the actual board before treating a firmware port as usable.
6. For the AX1800M experimental relay, next safe steps are source/ABI/test audit and non-destructive logging plan. Do not execute OTA, SSH exploit, app rollback or vehicle operation as a side effect of a catalogue refresh.
7. Separate source/host pass from vehicle acceptance; publish only after technical and manual browser review.

**Editorial rule:** public repository comparison only. Do not import private issue threads, third-party firmware packages, credentials, raw device logs, proprietary OEM binaries or identity-bearing samples into the public Atlas.
