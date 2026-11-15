# PerkTheFox research tracker — Component Protection, ECU security, MST2

**Source snapshot:** 2026-11-16. **Audience:** public technical research comparison. **Scope:** repository/release capabilities, evidence boundaries and safety. No unlocking procedure, keys, offsets, personal messages, firmware dumps, adaptation payloads or instructions to circumvent a vehicle security function are reproduced here.

## Distinct workstreams

| Track / public source | Publicly verified | Does not establish |
| --- | --- | --- |
| [`perkthefox/mqb_contitool`](https://github.com/perkthefox/mqb_contitool) — [v2.1.2, 2026-11-15](https://github.com/perkthefox/mqb_contitool/releases/tag/v2.1.2) | **ContiTool** GUI/CLI for Continental **J533 MQB gateway**, Renesas RH850/F1L. Source documents CAN diagnostic/backup, memory analysis, engineering tools, CP-related records, firmware operations, SWaP/FEC handling, D-PDU/J2534 interface support and variant-specific safeguards. **v2.1.0** (Nov 13) added EEPROM/OPBT inspection and driving-profile editor; **v2.1.1** (Nov 14) added processor hardware-ID inspection; **v2.1.2** (Nov 15) fixes flash-programming compatibility and error diagnostics on newer Vitesco/Continental revisions. These are real **public releases**, not just group claims. | Does **not** prove generic offline Component Protection elimination on every MQB ECU, AID firmware decryption, cross-generation compatibility, or safe in-car programming of all revisions. Flasher support requires exact hardware/firmware and recovery evidence. |
| [`perkthefox/mqb-kshutz-kaput`](https://github.com/perkthefox/mqb-kshutz-kaput) — [source README](https://github.com/perkthefox/mqb-kshutz-kaput/blob/main/README.en.md) | **Schutz-Kaput** is a separate modular **local firmware-file preparation/inspection** project. Current public target list specifically names **Valeo MFK3/A5 front-camera `2Q0 980 653`, SW 13xx/14xx**; it advertises component-protection and FeC/SWaP patch support and stock restoration of generated files. Source and self-tests are inspectable. | Not interchangeable with ContiTool's gateway role. It does **not** establish support for every radar, AID generation, 5F, A5 firmware train, or other cameras. An output file or internal self-test does not prove a vehicle-safe firmware flash. |
| [`perkthefox/mst2-cluster-nav`](https://github.com/perkthefox/mst2-cluster-nav) — [v1.0.0](https://github.com/perkthefox/mst2-cluster-nav/releases/tag/v1.0.0) | Separate **MIB2 Standard / TechniSat** CarPlay/Android Auto → AID project: cluster map, native maneuver arrows, lanes, route guidance and media display. Public v1.0.0 was released Oct 26. The project is **not** a Component Protection tool. | **v1.1.0 of Nov 9 was withdrawn by the author after a reported head-unit reset loop. Do not install v1.1.0.** [Release warning](https://github.com/perkthefox/mst2-cluster-nav/releases/tag/v1.1.0). Do not confuse platform MST2 with Harman MHI2/MU1440. |
| Claimed complete **MST2 QEMU lab** | The forum discussed a full multi-processor MST2 emulation with QNX, J5/i.MX6 and companion services, in October, including Component Protection research conducted inside the virtual environment. | **No independently verified public self-contained MST2 QEMU release** from this author was identified in the inspected repository set. A Telegram demonstration is not a distributable emulator or proof of complete physical-security behavior. |
| Proposed **AID firmware / CP / radar expansion** | Firmware formats, signing, cluster migration and additional ECUs appear as active research topics, distinct from publicly released J533 and MFK3 tools. | No universal AID/cluster CP adapter or public all-MQB decryption release is established. Some statements are experiments, compatibility hypotheses or test plans; treat as **unverified** until pinned public source and reproducible bench evidence appear. |

## Component Protection: what is being researched

- **Not merely encryption removal.** Volkswagen's Component Protection concerns vehicle-bound authentication, the gateway's role, per-module key material and response/state checks. Firmware packaging/compression, code signing, a component-protection session and immobilizer authorization are **different layers**.
- **J533 vs protected slave module:** The gateway may participate in a protection handshake, but the slave ECU also decides whether it enters a protected state. A generic gateway-side setting therefore cannot be assumed to unlock every independent unit. Actual support depends on module generation, cryptographic engine, memory organization and OEM firmware.
- **Offline bench vs installed car:** Reading ECU data, running a firmware-file patcher, emulating state transitions, exchanging a complete CP handshake on a bench and achieving an accepted installed vehicle are progressively stronger evidence levels. Source or screenshots alone are not last-stage proof.
- **Immo and AID:** Immobilizer generations and cluster part-number families introduce different authentication/provisioning constraints; successful MFK3 or J533 work must not be generalized to AID 790/791, anti-theft enrollment or all MQB/MLB variants.
- **Safety and legal boundaries:** These topics can affect anti-theft controls, diagnostics, ADAS and vehicle homologation. Some community testing discussed firmware mismatches, non-booting modules and recovery needs. For the Atlas, keep documentation analytical, not an instruction manual for defeating security; prefer owner-authorized bench testing and stock/verified recovery plans.

## Dated public checkpoints and decision ledger

| Date (2026) | Evidence | Classification |
| --- | --- | --- |
| Oct 26 | `mst2-cluster-nav` v1.0.0 | Public packaged software; project-stated feature support |
| Oct 28–29 | `mqb-kshutz-kaput` source and camera-target discussion | Public targeted patcher; **not** universal CP release |
| Nov 8–11 | ContiTool 2.0 series / D-PDU and repair releases | Public tool release and adapter-specific fixes; readiness differs by driver |
| Nov 9 | `mst2-cluster-nav` v1.1.0 | **Withdrawn — known reset-loop report; do not install** |
| Nov 13 | [ContiTool v2.1.0](https://github.com/perkthefox/mqb_contitool/releases/tag/v2.1.0) | EEPROM/OPBT inspection and profile tooling added |
| Nov 14 | [ContiTool v2.1.1](https://github.com/perkthefox/mqb_contitool/releases/tag/v2.1.1) | RH850 hardware IDs and validation |
| Nov 15 | [ContiTool v2.1.2](https://github.com/perkthefox/mqb_contitool/releases/tag/v2.1.2) | Flash/write reliability fix on identified new J533 hardware |
| Nov 16 | New Atlas status audit | Source verified, **not** a hardware acceptance test |

## Adjacent projects — do not misattribute

- [`OneB1t/Laertes`](https://github.com/OneB1t/Laertes) is an **independent** ODIS web interface / offline VCI gateway simulation. It can serve as a diagnostics lab reference, but simulated backend responses do **not** demonstrate a real-car CP bypass. It is **not PerkTheFox's project**.
- [`iscle/qemu-mhi2`](https://github.com/iscle/qemu-mhi2) is a different, public **classic MHI2** full-firmware QEMU line; neither this nor Perk's MST2 experiment is a proven public all-model MHI2Q emulator.

## Questions to track

1. Which **exact gateway hardware and firmware revisions** have physically verified ContiTool backups, restore and safe flash, including negative cases?
2. Does the next MFK3 release expand its explicitly listed target compatibility? Track support via files/releases and tests, not chat promises.
3. Is a standalone MST2 QEMU tree published with toolchain, verified firmware profile, guest boot and independent reproduction?
4. Does a documented AID-specific firmware or Component Protection result emerge with isolated bench evidence and authorized ownership safeguards?
5. Does `mst2-cluster-nav` get a confirmed v1.1.0 successor with reset-loop root cause and tested recovery path?

**Publication rule:** never include raw third-party messages, uploaded chat exports, personal/VIN/FAZIT identifiers, plaintext keys, donor ECU dumps, exploit payloads or sensitive bypass instructions in this publicly hosted Atlas. Cite the author's public releases and documentation only.
