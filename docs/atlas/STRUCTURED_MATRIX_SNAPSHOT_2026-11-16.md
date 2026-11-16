# MIB Atlas structured-matrix release snapshot

**Source snapshot:** 2026-11-16. **Scope:** public source review and user-supplied Telegram leads through 2026-11-15; no physical vehicle tests performed in this Atlas maintenance pass. **Status:** research UI / editorial update only. The page and publication policy are in [`docs/index.html`](../index.html) and [`MAINTENANCE_RULES.md`](MAINTENANCE_RULES.md).

## Scope and non-additive inventory counts

| Inventory | Count | What it means |
| --- | ---: | --- |
| MIB1 High/MHIG CarPlay/Android Auto retrofit | **1 source lead** | Telegram developer korho claims USB H.264 acceleration and App-Connect on MIB1 High; no verified public MHIG source or firmware train, no inferred VC stream |
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

## MIB1 High (MHIG) retrofit provenance

Telegram messages #18572, #18581, #18597–18599 from 13 Nov by **korho** describe CarPlay/Android Auto App-Connect and USB hardware-accelerated decoding; wireless is future/author-reported, not independently accepted. See [MIB1 retrofit audit](MIB1_MHIG_RETROFIT_2026-11-16.md). The legacy M.I.B. activation script explicitly excludes MHIG and is not this new port. There is no 59th public repo until a confirmed implementation source is found.

## Current native wireless source boundary

- [LuKa native MHI2Q](https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/docs/wireless-carplay/README.md): stock210 receiver on Audi MHI2Q; partial real vehicle main/111 evidence; full combined wireless CarPlay, control/RTCP and audio focus acceptance still open. Compatible MHI2Q family examples in general project docs do not automatically prove each individual wireless train.
- [joeyQuery classic MHI2](https://github.com/joeyQuery/MHI2-wirelessCarPlay): MU0678-class Bluetooth iAP2/uap0/AirPlay reverse engineering; **no end-to-end native wireless session**.
- [congobg MHI2Q_WiFi_CarPlay](https://github.com/congobg/MHI2Q_WiFi_CarPlay): author public installation README claims native wireless for exact Audi software **3638/MU0917**, but no tagged GitHub release or independent physical acceptance was seen in this source pass.
- [omonob wired maps / wireless announcement](https://github.com/omonob/VW-MHI2-Carplay-Maps): MHI2/MST2 no-dongle direction announced in Telegram messages #18401, #18720 and #18728; currently published 2.0.1/2.1-rc.7 wireless menu option **not a native receiver release**.
  - **Same-day follow-up (16 Nov, 10:19 CET):** [V3.0 experimental prerelease](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/releases/tag/v3.0) now packages a **native receiver for MU1102/790/791 only**, superseding the earlier announced-only status. Škoda MU1440/MU1433, VW MU1367, SEAT MU1447 remain **wired-only**; full V3.0 vehicle acceptance not demonstrated. See [dated release audit](OMONOB_WIRELESS_V3_2026-11-16.md). Original announcement and 58×22 score dates are preserved.
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

## Later 16 Nov follow-up — branch-aware fork deduplication

The original 58×22 dated scoring remains the **4 Nov historical baseline**. After comparing all 14 recorded fork parents (including their release/feature branches and contribution PRs), two default-branch-only, behind-upstream records were removed from the visible comparison/catalog: `maxim-smirnov/mhi2-carplay-cluster` (0 ahead / 73 behind LuKa) and `Mr-MIBonk/mhi2-android-auto-cluster-map` (0 ahead / 133 behind MacsInSpace). **Curated visible count: 56**; **55 of 56** previously checked public sources reachable, one historical Tiguan source remains 404. This change is deduplication, not a new 22-feature re-score. The two suppressed records are retained outside the page for rescan.

Crucial exceptions: `harman-f/qemu-mhi2` main is identical but its Windows/Škoda branch has four own commits and upstream draft PR #2 is still open; `harman-f/mib2-toolbox` GitHub parent is `jilleb/mib2-toolbox` (original created 2019) and its two contributor PRs #219/#220 were merged into that upstream in 2022. A separate experimental branch has four exclusive commits. `evanj495` main README-only does not invalidate its four-commit MU1320 release branch. See [full branch/PR audit](FORK_DIFF_LINEAGE_AUDIT_2026-11-16.md) and expanded 38-relationship Lineage table/graphs in `docs/index.html`.

## Same-day release follow-up — V3.1, 16 Nov 2026, 12:46 CET

The 10:19 CET V3.0 observation above is historical: [V3.1](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/releases/tag/v3.1) **supersedes** its MU1102-only wireless compatibility. V3.1 packages experimental native wireless for **MU1367/790+791** and **Škoda MU1440/790** alongside MU1102/790+791. MU1440/791 is unsupported; MU1433/MU1447 are wired-only. Its signed SWDL metadata/whole-directory checksum repack is documented, but **no new target in-car acceptance** exists. The [V3.1 date-specific audit](OMONOB_WIRELESS_V31_2026-11-16.md) is canonical for the newer status. Historical baseline scores (58 × 22) and the curated comparison (56 entries) are unchanged.
