# Atlas discovery watch: MHI2/MHI2Q emulators, QNX labs and Home Assistant

**Research snapshot:** 2026-11-16. **Status:** supplementary source discovery, NOT a release, compatibility claim, head-unit validation or completed 58-repository re-audit. This file is intentionally separate from the original 58×22 scored matrix until the exact capability class and lineage have been reviewed. Future chat-export source leads should be independently verified, de-duplicated and privacy-screened before inclusion.

## Scope distinction: three emulator classes

1. **Full firmware / head-unit emulator:** QEMU executes original MHI2/QNX firmware with simulated SoC, companion services and GUI. This is substantially stronger than a Java menu or graphics mockup, but does not automatically include a usable cockpit, audio, NAV, USB CarPlay or genuine MFi service.
2. **CarPlay sender / receiver lab:** emulated/simulated iPhone and a stock or adapted QNX AirPlay receiver test Type110/Type111 negotiation, native decoding, iAP2/MFi and timing. This tests the CarPlay path, not a complete vehicle or consumer MMI.
3. **HMI/cluster mockup:** browser, Windows or custom-rendered instrument cluster geometry/layout. Useful for view modes, safe areas and controls but neither firmware boot nor physical MOST acceptance.

### Emulation source inventory (new/current)

| Project | Type | Source-evidenced status | Proof gap and Atlas handling |
| --- | --- | --- | --- |
| [iscle/qemu-mhi2](https://github.com/iscle/qemu-mhi2) | Full classic MHI2 Tegra3 QNX QEMU, with companion RCC/IOC, graphics/audio/MOST bridges | Main public README lists **Audi AU37x P5089 / MU1326**, **VW VWG11 K3342 / MU1427**, **Porsche POG11 K5126 / MU1394**. macOS Apple Silicon is locally tested for specific workflows. Requires user's own legal, exact-train firmware and captured bootstrap. | Skoda SKG13/MU1440 is **not** listed as supported by public upstream; a cluster window or renderer exists without automatically proving actual video/CarPlay on a firmware variant. Consider one independent scored external software-repo entry if needed. |
| [harman-f/qemu-mhi2](https://github.com/harman-f/qemu-mhi2) | Public fork / shared code lineage from iscle | Public README currently documents the same Audi/VW/Porsche profiles and experimental QEMU code. | Do not count as an independently invented emulator; record fork lineage and actual differing commits before separate capability scoring. |
| [luka-dev/mib2q-carplay-rgi CarPlay Lab](https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/docs/carplay-lab/README.md) | QNX/QEMU receiver + simulated native iOS sender `vphone`, software MFi, tests | Stock210 AirPlay receiver with iOS 26.6.2 vphone, Type110/111 decode, PCM/audio, input/lifecycle and SI/J9 test profiles. Test guides explicitly label simulated peripherals and independent acceptance levels. | **Not** a production MHI2Q full-firmware emulator and not a fully accepted wireless CarPlay vehicle. Track as a feature of Luka's existing repository rather than double-counting a repo. |
| [omonob/MHI2-Carplay-Maps](https://github.com/omonob/MHI2-Carplay-Maps/releases) | Firmware QNX VMs / native HMI validation | 2.1.0-rc.7 describes brand/firmware-specific menu interactions, offline QNX checks and separate native screens. Reported long SEAT G11 sessions include unresolved kernel stops and a media-start fault. | VM HMI acceptance is **not** sustained vehicle runtime, audio, 111 MOST display or native wireless. This is a capability of the already indexed omonob repo. |
| [harman-f/ChairPlay](https://github.com/harman-f/ChairPlay) | External Windows CarPlay/cluster visualization fixture | DiPlay Type111, 3 Škoda views, safe areas and host screenshots. | Reference simulation, **not** booting MHI2 firmware, not native MHI2Q and no proof of real-car Type111 lifecycle. Score in a lab category if catalogued. |

**Existing internal project checkpoint (not public Atlas source):** a separate Oct 10 2026 Research Windows/Skoda MU1440 QEMU run demonstrated native 1280×640 Škoda HMI input/menu and QNX startup. Navigation startup, audio/MOST video sender, real Cockpit output and CarPlay were **not** accepted; no claim that this work is released as a generic public Skoda emulator. Keep internal evidence references only in the private research tracker, not this public document.

**MHI2Q full firmware:** the source survey identifies a QNX/QEMU *AirPlay laboratory* and toolchain tests, not a proven, general-purpose public MHI2Q firmware emulator equivalent to iscle's classic MHI2 machine. Mark `UNCONFIRMED` until an exact repository, original firmware boot and guest HMI/MOST proof are documented.

## Home Assistant / adapter: avoid confusing three meanings

| Source | Architecture | Capability and relevance | Exclusion / proof boundary |
| --- | --- | --- | --- |
| [home-assistant/iOS](https://github.com/home-assistant/iOS) (2026.7 CarPlay configuration improvements) | **Official iPhone Home Assistant Companion app in Apple CarPlay**, CarPlay UI templates and entities/Assist controls | CarPlay display interface can expose supported home controls; this is relevant to testing ordinary CarPlay interaction on an MHI2 HU and future voice/steering compatibility. [2026.7 release feature description](https://github.com/home-assistant/iOS/releases). | Not an MHI2 QNX plug-in, firmware modification, cluster video provider or direct vehicle telematics data adapter. Do not assume Type111 on the car cluster. |
| [Pulpyyyy/carconnectivity-addon](https://github.com/Pulpyyyy/carconnectivity-addon) | Home Assistant addon backed by manufacturer/cloud CarConnectivity vehicle connectors and MQTT | Connected-car telemetry via supported brands and online accounts, subject to changed VAG API access. | Not a local MHI2/MHI2Q TCP/MOST/DSI adapter; 2026 VAG cloud restrictions and EU Data Act read-only alternatives affect this route. |
| [its-me-prash/vwgroup-connect-ha](https://github.com/its-me-prash/vwgroup-connect-ha) | HA integration for VAG brands using remote APIs/available Data Act sources | Audi/VW/Škoda etc vehicle entity status; relevant for wider Home Assistant integrations, not CarPlay cluster graphics. | Do not mark as direct infotainment integration. |
| [boesec/vag2mqtt](https://github.com/boesec/vag2mqtt) | Audi EU Data Act cloud → MQTT read-only | Conceptual telemetry bridge to Home Assistant, early development; updates approx. every 15 minutes. | Not a live CarPlay/MHI2 signal source; Škoda and other brands planned in README, not confirmed supported at snapshot. |
| [TA2k/ioBroker.vw-connect](https://github.com/TA2k/ioBroker.vw-connect) | **ioBroker** VAG account adapter | German-speaking users may describe this as an “Adapter”, but it connects vehicle cloud data to ioBroker rather than Home Assistant directly. | Context candidate only; no evidence that this is the specific user-recalled adapter. |

**No direct QNX MHI2↔Home Assistant bridge identified in this initial search.** Keep this as an *open lead*, not a categorical absence claim. A possible future integration architecture would need a proven local HU network API/event source (QNX/DSI/vehicle diagnostics) → externally authenticated local bridge → MQTT/HA; commercial vehicle telemetry restrictions and control safety must be respected. Do not invent such a tested implementation.

## Next pass when user-provided current chat export arrives

- Extract URLs, repository owner/name, version/tag/commit, exact message timestamp and the neighboring technical claim.
- Check duplicate aliases, upstream fork/derivative relationship, platform `MHI2` vs `MHI2Q` vs `MST2`, firmware/SoC/QNX compatibility.
- Compare external project **evidence** and not only activity: exact original firmware boot, QNX HMI, CarPlay 110/111, wireless, Android Auto, MOST/VC outputs, scope of true vehicle acceptance.
- For any “Home Assistant adapter”, establish which of the three routes is meant: HA iPhone CarPlay frontend, VAG vehicle-cloud backend/MQTT, or *local headunit-to-HA bridge*. Require exact repo/link before asserting the last.
- Do not publish raw chat export, account names/IDs, personal messages, passwords, device identifiers or non-public attachments in the public Atlas; publish only independently verified public links and conclusions.
- Carry verified entrants forward into the revised comparison matrix once browser regression and full source checklist are complete.

## Noted evidence references

- [iscle full QNX emulator](https://github.com/iscle/qemu-mhi2)
- [LuKa MHI2Q CarPlay Lab](https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/docs/carplay-lab/README.md)
- [omonob 2.1 experimental release](https://github.com/omonob/MHI2-Carplay-Maps/releases)
- [Home Assistant iOS release history](https://github.com/home-assistant/iOS/releases)
- [VAG CarConnectivity addon](https://github.com/Pulpyyyy/carconnectivity-addon)
