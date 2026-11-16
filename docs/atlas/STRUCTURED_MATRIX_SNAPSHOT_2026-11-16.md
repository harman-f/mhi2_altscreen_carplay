# Atlas structured-matrix release snapshot

**Source snapshot:** 2026-11-16. **Scope:** public source review and user-supplied Telegram leads through 2026-11-15; no physical vehicle tests performed in this Atlas maintenance pass. **Status:** research UI / editorial update only. The page and publication policy are in [`docs/index.html`](../index.html) and [`MAINTENANCE_RULES.md`](MAINTENANCE_RULES.md).

## Scope and non-additive inventory counts

| Inventory | Count | What it means |
| --- | ---: | --- |
| Original CarPlay/Android Auto matrix | **58** | 58 existing scored profiles, **22 attributes**; scores based on the **4 November** baseline, not all re-scored on November 16 |
| GitHub links encountered in Telegram HTML | **92** | Distinct owner/repository links in the provided source cutoff; **not 92 independently qualified implementations** |
| Public source reachability from dated audit | **57/58** | 56 direct and one moved to canonical `omonob/VW-MHI2-Carplay-Maps`; one historic Tiguan fork source unavailable; dated verification |
| Native wireless CarPlay receiver leads | **6** | Includes per-platform public research, one README claimant without independent car acceptance, community announcements and an MHI2 prototype |
| Emulator/virtual lab profiles | **14** | Public full QNX host/emulator, private author reports, iPhone/QNX protocol laboratory, and diagnostic VCI are separate categories |
| Home Assistant and related tool profiles | **12** | Includes Matze's unpublished local MIB JAR/eSIM/HA/Docker proposal explicitly marked **announced** |
| PerkTheFox ContiTool support checklist | **18** | Source-documented J533/RH850 functionality and explicit unsupported/unknown scope; **not independent bench validation** |
| Community author release/announcement entries | **25** | Filterable author/date/platform/stage summaries; public-source vs forum-reported distinguished |
| Miscellaneous hardware/adapter profiles | **12** | HUD, CatPlay/CarPlay2Air, AX1800M, V851SE, HW301, DisplayLink, ambient |
| Lineage relationships | **18** | 14 GitHub fork parents identified + 4 documented design/code ancestry relationships, separately classified |

**These counts overlap**. Do not sum them into an invented unique-project count.

## Current native wireless source boundary

- [LuKa native MHI2Q](https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/docs/wireless-carplay/README.md): stock210 receiver on Audi MHI2Q; partial real vehicle main/111 evidence; full combined wireless CarPlay, control/RTCP and audio focus acceptance still open. Compatible MHI2Q family examples in general project docs do not automatically prove each individual wireless train.
- [joeyQuery classic MHI2](https://github.com/joeyQuery/MHI2-wirelessCarPlay): MU0678-class Bluetooth iAP2/uap0/AirPlay reverse engineering; **no end-to-end native wireless session**.
- [congobg MHI2Q_WiFi_CarPlay](https://github.com/congobg/MHI2Q_WiFi_CarPlay): author public installation README claims native wireless for exact Audi software **3638/MU0917**, but no tagged GitHub release or independent physical acceptance was seen in this source pass.
- [omonob wired maps / wireless announcement](https://github.com/omonob/VW-MHI2-Carplay-Maps): MHI2/MST2 no-dongle direction announced in Telegram messages #18401, #18720 and #18728; currently published 2.0.1/2.1-rc.7 wireless menu option **not a native receiver release**.
- [HARMAN-F classic MHI2](https://github.com/harman-f/mhi2_altscreen_carplay): Škoda MU1440 native BT/WLAN bootstrap proof incomplete; no accepted full session. Independent external AX1800M dongle work is under Miscellaneous.

## Dongle / HUD routing

CatPlay and its SoC-specific firmware, OMKE/AX1800M, octacon84/V851SE, HW301, other dongle protocol stacks and HUD feature projects are retained under **Miscellaneous**. This is essential to avoid double-counting wireless-to-wired dongle solutions as native wireless on the head unit. The public [CatPlay README](https://github.com/catplay-labs/catplay) currently documents different CPU/radio variants under similar marketing names.

## Home Assistant native vs iPhone frontend

- [Official HA CarPlay Companion UI](https://companion.home-assistant.io/docs/carplay/): supported iPhone application interface; **not** QNX MIB Java code.
- **Matze**, messages #18384 / #18637 / #18675: proposed unit-side JAR with own eSIM connection and HA/Docker/web integration; **no public package located**, so source status remains **announced**.
- **korho**, #8736 / #18648: reports local MHI2 Android Auto vendor-channel → MQTT → HA; **not independently release-matched** and distinct from [wireless AA extenders](https://github.com/korhojoa/mib2-extenders).
- Cloud-connect telemetry add-ons are separate integration class from local MIB/QNX services.

## PerkTheFox / ContiTool support list

The latest inspected release was [ContiTool v2.1.2, 2026-11-15](https://github.com/perkthefox/mqb_contitool/releases/tag/v2.1.2). The [English README](https://github.com/perkthefox/mqb_contitool/blob/main/README.en.md) claims J533-specific CAN diagnostics, bench backup/read/restore, EEPROM/OPBT inspection, GUI/CLI, adapter types, SWaP/FeC and Component Protection bank work. The Atlas checkbox/checklist represents **author-documented support, not a successful bench test**. 5Q0/Lear or unrelated ECU families are not covered by the same proof. No procedural bypass details or keys are included.

## Structural/release testing

- English-only main navigation with nine tab destinations; no duplicated top-level anchor navigation.
- Persistent local light/dark mode without external CDN or theme dependencies.
- Feature, emulator, native receiver, integrations, security capabilities, community announcements, miscellaneous hardware and lineage data are in filterable/searchable tables with explicit result counts, reset and sort controls.
- Source-specific expandable content is available for HA/tools and many research row notes.
- Existing 58 original scored rows and associated 58 full repository cards remain intact.
- GitHub Pages deploy is configured to publish **only `docs/index.html`** on relevant `main` pushes, not the source audits or archived Telegram HTML.
- This snapshot records structure and source claims, not live browser QA or end-to-end Pages acceptance. Preserve the HTML and current test output to confirm actual deployment before stating success.

For subsequent reviews, read [`MAINTENANCE_RULES.md`](MAINTENANCE_RULES.md) first and publish a new dated snapshot rather than redating this audit.
