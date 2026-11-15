# Additional public repository leads (deduplicated) — 2026-11-16

The recent community link corpus contained **92 distinct GitHub owner/repository names in 9,520 extracted messages**, including unrelated tools, derivatives, aliases, forks and previously indexed projects. **This is a discovery count, not 92 vetted projects, and not a replacement for the 58 scored rows of the Atlas.** The private chat export, message authors and message IDs are not published or linked here.

## Emulator, virtual lab, diagnostics

| Public lead | Classification | Current audit boundary |
| --- | --- | --- |
| [iscle/qemu-mhi2](https://github.com/iscle/qemu-mhi2) | MHI2 full QNX/Tegra3 QEMU | Audi, VW and Porsche train profiles documented; not an MHI2Q general emulator |
| [harman-f/qemu-mhi2](https://github.com/harman-f/qemu-mhi2) | Related fork | Do not count as new independently invented emulator |
| [luka-dev CarPlay lab](https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/docs/carplay-lab/README.md) | MHI2Q iOS sender ↔ QNX receiver test harness | Not full production firmware boot |
| [mlb-evo/qemu](https://github.com/mlb-evo/qemu) | QEMU source lead | Existing public repo, platform/relationship needs independent examination |
| [OneB1t/Laertes](https://github.com/OneB1t/Laertes) | ODIS/offline VCI diagnostic web environment | Emulates diagnostics; not direct CP hardware acceptance or head-unit QNX boot |
| [iscle/mib-link](https://github.com/iscle/mib-link) | Pico W / ESP32-S3 USB network bridge | Not an emulator; network/service access only |
| [NumberOneBot/ChairPlay](https://github.com/NumberOneBot/ChairPlay) | Host CarPlay fixture | Separate from MHI2 firmware; deduplicate forks and newer maintained branches |

## CarPlay / Android Auto / Wireless / cluster

| Public lead | Classification | Current audit boundary |
| --- | --- | --- |
| [perkthefox/mst2-cluster-nav](https://github.com/perkthefox/mst2-cluster-nav) | MST2 → cluster navigation | v1.0.0 reference; **v1.1.0 withdrawn** |
| [korhojoa/mib2-extenders](https://github.com/korhojoa/mib2-extenders) | MHI2 wireless Android Auto and iAP/cluster extension | CarPlay VC not released as vehicle accepted in current README |
| [kkrvch/mib-std2-wirelessbridge](https://github.com/kkrvch/mib-std2-wirelessbridge) | Standard-unit wireless bridge lead | Exact model and source status to recheck |
| [ludwig-v/wireless-carplay-dongle-reverse-engineering](https://github.com/ludwig-v/wireless-carplay-dongle-reverse-engineering) | Dongle protocol reverse engineering | Not by itself a complete MHI2 second-screen implementation |
| [OMKE/wireless-carplay-virtual-cockpit](https://github.com/OMKE/wireless-carplay-virtual-cockpit) | AX1800M 111 relay | Adapter/firmware/vehicle specific, one reported Audi test |
| [zakklmv/wireless-carplay-altscreen-dongles](https://github.com/zakklmv/wireless-carplay-altscreen-dongles) | Dongle second-screen research | New source candidate to verify |
| [f-io/LIVI](https://github.com/f-io/LIVI) | CarPlay dongle protocol source | Not identical to an AX1800M-compatible full firmware port |
| [jjff2/JF-AI_Box-Bridge](https://github.com/jjff2/JF-AI_Box-Bridge) | AI-box bridge lead | Hardware, freshness and compatibility unverified |
| [Matze89x/mst2d-carplay-aid](https://github.com/Matze89x/mst2d-carplay-aid) | Delphi MST2 cluster CarPlay | Firmware-specific beta; public README says not vehicle-tested |
| [perkthefox/mqb_contitool](https://github.com/perkthefox/mqb_contitool) | J533 gateway/CP research | **Not** a CarPlay implementation |
| [perkthefox/mqb-kshutz-kaput](https://github.com/perkthefox/mqb-kshutz-kaput) | Valeo MFK3 camera CP tool | Not universal CP or MHI2 CarPlay |

## Vehicle / hardware / Home Assistant adjacent

| Public lead | Classification | Current audit boundary |
| --- | --- | --- |
| [WARMW00D/esp32-CAN-sniffer-logger-screener](https://github.com/WARMW00D/esp32-CAN-sniffer-logger-screener) | CAN data and hardware logger | Hardware accessory, not a CarPlay receiver |
| [WARMW00D/HUD-Audi-A4-B9-MLB-Evo-ESP32-S3-SuperMini-LCD-2.79-NV3007-BLE](https://github.com/WARMW00D/HUD-Audi-A4-B9-MLB-Evo-ESP32-S3-SuperMini-LCD-2.79-NV3007-BLE) | ESP32 external HUD project | Not OEM Virtual Cockpit/MOST AltScreen |
| [Matze89x/mib2q-ambient-fx](https://github.com/Matze89x/mib2q-ambient-fx) | MHI2Q vehicle-reactive lighting | Adjacent infotainment-extension category |
| [Pulpyyyy/carconnectivity-addon](https://github.com/Pulpyyyy/carconnectivity-addon) | Home Assistant vehicle cloud data addon | Not QNX/MHI2 local plug-in |
| [home-assistant/iOS](https://github.com/home-assistant/iOS) | Official CarPlay app for Home Assistant | iPhone UI; no native Type111 or MCU gateway access proven |

## Research triage policy

For each candidate, resolve the canonical repository/fork first. Then record exact platform (MST2/MHI2/MHI2Q/MH2P), firmware train and hardware profile, implemented feature, release date, latest actual source, reproducibility and independent vehicle proof. Keep `UNVERIFIED` distinct from `NO`; preserve author-reported results without inferring stock compatibility.

**Two non-public leads should remain unscored:** privately demonstrated full-MHI2 firmware emulators, and an announced HA/Docker/QNX JAR automotive bridge. The community messages are useful pointers but do not establish public repository availability.

Raw chat messages, names, identity data, keys, device IDs, proprietary archives and security bypass steps are deliberately not present here.
