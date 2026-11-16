# Telegram-backed emulator inventory and community roadmap — methodology

**Research status · 2026-11-16.** These are **source-attributed observations**, not independently tested firmware implementations. The companion [HTML Atlas](../index.html) has two browsable sections:

1. **Emulators & labs:** 14 distinct source leads, with Telegram display author, dates/message IDs, host operating system, emulated guest / brand / firmware and availability of source code.
2. **Community roadmap:** 25 selected announced or released projects across wireless projection, Home Assistant, MIB infrastructure, diagnostics, audio, media and security.

## Original source boundaries

The user's 11-part Telegram HTML export was examined locally, yielding **9,520 parseable messages** spanning August through 15 November 2026. The public GitHub repository intentionally does **not** include the HTML files, chat IDs, raw messages, private media, account identifiers or encryption keys. The Atlas uses attributed **display names** and **message numbers** to permit traceability in the user's local export; a reader who does not have that export cannot independently verify a chat-only claim.

A Telegram report is classified separately from a linked public source. **Public-source existence, simulator/bench test, published binary and in-car acceptance are not equivalent.** Host and guest OS fields are `not stated` where the chat did not identify them. A QNX target is not evidence that the host itself runs QNX. GitHub forks do not count as wholly independent emulator inventions without a code-lineage check.

## Public source anchors for independently checkable items

| Domain | Link | Supported claim |
| --- | --- | --- |
| Full MHI2 QEMU | [iscle/qemu-mhi2](https://github.com/iscle/qemu-mhi2) | Public QNX/Tegra emulator for exact Audi/VW/Porsche profiles |
| MHI2Q CarPlay lab | [luka-dev/mib2q-carplay-rgi/docs/carplay-lab](https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/docs/carplay-lab/README.md) | Virtual iPhone sender / QNX AirPlay receiver tests, **not** an entire consumer MHI2Q firmware emulator |
| MHI2 QEMU fork | [harman-f/qemu-mhi2](https://github.com/harman-f/qemu-mhi2) | Fork of iscle; separate experimental MU1440 progress is not generalized |
| Gateway diagnostics | [OneB1t/Laertes v0.9.12](https://github.com/OneB1t/Laertes/releases/tag/v0.9.12) | Windows ODIS web tool/offline VCI public; separate QEMU CAN connection not proven complete |
| MST2 CarPlay VC | [xPaiiN v2.0](https://github.com/xPaiiN/mst2-carplay-vc/releases/tag/v2.0) | New PQ/non-VC and HMI range from public 15 Nov release |
| Native wireless Android Auto | [korhojoa/mib2-extenders](https://github.com/korhojoa/mib2-extenders) | Firmware- and receiver-specific Harman MHI2 package; no general universal receiver |
| Local headunit bridge | [iscle/mib-link](https://github.com/iscle/mib-link) | Pico W/ESP32-S3 USB network bridge; not a firmware emulator or CarPlay unlocker |
| Continental CP research | [Perk ContiTool v2.1.2](https://github.com/perkthefox/mqb_contitool/releases/tag/v2.1.2) | Public J533-specific diagnostics/engineering release; not a general ECU unlock |
| Targeted camera firmware | [Perk Schutz-Kaput](https://github.com/perkthefox/mqb-kshutz-kaput) | Valeo MFK3/A5 scope; does not establish support on every camera/cluster |
| MST2 safety warning | [Perk MST2 Cluster Navigation withdrawn v1.1.0](https://github.com/perkthefox/mst2-cluster-nav/releases/tag/v1.1.0) | Author withdrew release after reported startup-loop failure |
| Home Assistant iOS | [Official HA CarPlay](https://companion.home-assistant.io/docs/carplay/) | iPhone app frontend, not a native MIB/HA middleware |
| Emerging features | [Matze AmbientFX](https://github.com/Matze89x/mib2q-ambient-fx) | Public source; exact hardware/vehicle acceptance still must be scoped |
| MHI2Q released development | [kamgurgul 1.5](https://github.com/kamgurgul/mib2q-carplay/releases/tag/v1.5) | Current public v1.5 source release, exact platform limits |

## Chat-only claims not to promote into validated releases

- **therubiksman**, MHI2 MU1367/P4521 multi-CPU QEMU, Google Earth and AID emulation: messages `#10642`, `#12927`, `#17728`, `#18533`. Host CPU reported but **host OS unknown**.
- **PerkTheFox**, multi-CPU MST2 QEMU/Continental AID and CP-state studies: `#12904`, `#13085`, `#13211`, `#13677`, `#13684`. Distinct from his public ECU-specific tools.
- **omonob**, VW MU1102 QEMU via WSL, separate AID and proposed native Wireless CarPlay: `#14130`, `#18664`, `#18401`, `#18720`, `#18728`. **No native wireless receiver release confirmed**.
- **Tomas**, AU57x/K3663 virtual HMI, MFi and multichannel audio: `#16929`, `#16933`, `#17605`, `#17658`. Audio test is an emulator result.
- **Matze**, car-side JAR/eSIM to HA with Docker/web API: `#18384`, `#18637`, `#18675`. No matching complete release.
- **korho**, vendor-channel MQTT to Home Assistant: `#8736`, `#18648`; separate from public wireless Android Auto modules.
- **OneB1t**, broader openMIB project and universal OTA direction: `#18661`, `#18663`. Concept only.

## Public site and safety requirements

Document security and component-protection research without CAN payloads, bypass scripts, keys, ECU memory offsets, flashing commands or undocumented protected-data handling. Do not present an experimental vehicle modification as install-ready. Keep raw exports strictly out of `main` and the GitHub Pages artifact.

This research snapshot is static; it is **not** a live Telegram monitor and does not claim to be current past the source cutoff.
