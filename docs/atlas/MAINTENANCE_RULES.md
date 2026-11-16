# MIB Atlas — recurring maintenance contract

**Applies to:** `docs/index.html`, `docs/atlas/**`, `tools/docs/check_cluster_atlas.py`, `.github/workflows/cluster-atlas-pages.yml`. **Status:** binding editorial and verification policy, 2026-11-16. Read together with [`docs/AGENTS.md`](../AGENTS.md) and the root [`AGENTS.md`](../../AGENTS.md).

## Update trigger and repository workflow

When asked to **"update MIB Atlas"** (including older names "AltScreen Atlas" or "Cluster Atlas"), use the following workflow without needing these rules re-explained:

1. Read `main/docs/index.html`, this contract, `docs/atlas/README.md`, and the last source audits. Respect original message/export cutoff. Check active user-provided Telegram/archive materials available **in the current authorized session**; do not claim to have future or private export access from an older chat. Review new links only with traceable public GitHub sources or clearly marked forum evidence.
2. Verify the public GitHub repository canonical name/redirect, author, fork parent, release/tag/date/commit, exact platform/brand/firmware/SoC, host vs guest, evidence strength, and regression/withdrawal warnings. Treat `not found` as **source unavailable**, not evidence that a feature does not exist.
3. Maintain one canonical entry per implementation; forks may have their own row when they actually add distinct code/target capability, but must reference upstream. **Never inflate 58 scored rows into 92 validated products:** 58 was a 4 Nov scored matrix baseline; 92 were distinct GitHub links seen in a particular Nov export, not 92 independently qualified solutions. Keep those counts separately and date them. Create additional scored rows only with documented scope, evidence and all 22 capability cells.
4. Date the **last source review** (latest inspected public evidence) separately from the **last complete 22-feature scoring** (the matrix baseline). Never label an old matrix as fully re-scored on a newer date merely because thematic material was updated.
5. Keep **all visible text and document UI in English**. Update source links and render no raw Markdown markers (`**bold**`) in raw HTML.
6. The top navigation is the single logo/identity plus a working **Light/Dark toggle**; topic switching lives in the tabs, not duplicated anchor links. Current categories: Overview, CarPlay & Android Auto, Native Wireless CarPlay, Emulators & labs, Home Assistant & tools, PerkTheFox / Component Protection, Community roadmap, Miscellaneous, Lineage & sources. **MIB1 High/MHIG head-unit projection belongs in the ordinary CarPlay & Android Auto tab**, with no inferred Virtual Cockpit support.
7. **Every research table** gets a working search field, platform/status (or topic/category) filters, count and a reset control. For capability matrices distinguish public-source implemented, author-reported/partial, planned, unsupported and unknown. Use `not stated` for missing host OS or firmware. Each table row must link source or expose a clear "no public source" caveat. Where meaningful, offer expandable implementation/evidence/caveat details; do not present nonfunctional checkboxes as interactive.
8. **Native Wireless CarPlay is strictly the receiver on the head unit itself** (BT iAP2, MFi, Wi-Fi AP/Bonjour, AirPlay, DIO, actual phone/vehicle); record **exact model, firmware/MU, main and second-screen status**. Native wireless **Android Auto** is a separate protocol. External wireless USB dongles and their custom firmware, including CatPlay, belong under **Miscellaneous / Dongle firmware** — never in the native receiver matrix, even when they can forward Type 111.
9. **Emulator** comparisons must include author/repo, host operating system and CPU where known, guest platform/brand/firmware/SoC, QNX/HMI, RCC/IOC, MOST/CAN/BAP, VC/AID, CarPlay/AA test, source/release and vehicle-test boundaries. Distinguish full QNX firmware boot, phone/receiver lab, cockpit renderer, and diagnostic VCI/gateway simulation.
10. **Home Assistant & tools** must distinguish official iPhone CarPlay Companion UI, manufacturer-cloud HA telemetry, MHI2 local Android Auto MQTT/vendor channel, and a proposed native head-unit JAR/eSIM/Docker HA bridge. An author-announced prototype (e.g. Matze) must be named and dated but never described as a downloadable/verified release without a confirmed repository.
11. **PerkTheFox** is the canonical public handle (`perkthefox`); spell `ContiTool` and link exact [`perkthefox/mqb_contitool`](https://github.com/perkthefox/mqb_contitool). Keep a source-scoped feature checklist by exact Continental J533 RH850/F1L firmware/hardware and distinguish `source documented` from independently tested; explicitly mark unsupported 5Q0/Lear/other ECUs. Distinguish J533 Component Protection, A5/MFK3 firmware, AID and immobilizer. Do not publish bypass code, credentials, keys, offsets, donor dumps or instructions.
12. **Lineage (not LineageOS):** maintain known actual GitHub parent forks and documented code ports/ideas separately. Graph may be snapshot-based but must be dated and supplemented by a fresh searchable upstream table. No speculative authorship or copy attribution.
13. **Community roadmap** records Telegram display name (only if openly supplied by owner), original message number/date, claim, platform, public independent link where available, and status `released / vehicle-tested / emulator-tested / reported / announced / withdrawn`. Do not publish raw third-party chat text, private chat URLs, phones, account IDs, or private firmware captures. Evidence from a chat remains author-reported even when a matching GitHub repo exists.
14. **Miscellaneous** captures HUD, non-VC overlays, dongle firmware/hardware (CatPlay, Suding, AX1800M, HW301, Carlinkit etc), DisplayLink, sound, lighting and peripherals. Always keep controller/dongle hardware identifiers and firmware compatibility separate from vehicle platform/firmware.
15. Keep the page self-contained (`docs/index.html`): no CDN, external JS, external fonts, analytics, runtime API, credentials or private content. Maintain accessible keyboard navigation and a working offline light/dark toggle and filters.
16. Update `docs/atlas/README.md` and a dated audit on any new snapshot. Keep original reports intact; append a new evidence snapshot rather than rewriting historical measurements. Full re-scores require 22-cell per-repository evidence and test-scoped proof labels.

## Release gates

- Use a **documentation-only branch based on `main`**, never merge unrelated `develop` firmware/runtime changes simply to update the website.
- Run `python3 -B tools/docs/check_cluster_atlas.py docs/index.html`, `python3 tools/docs/check_docs.py --self-test`, `--scope active`, `--scope all`; require publication / Atlas Actions CI to pass and manually inspect browser view when available.
- Exact links in the HTML must be canonical/public and must not require private repo access. Check for broken in-page anchors, 58↔profile ID matching, baseline date in prose, all tabs visible with JavaScript off, and filter/theme functionality with JavaScript on.
- PR to `main` and merge only documentation/Atlas changes after checks. A `main` push matching `docs/index.html` **automatically starts GitHub Pages validation + deploy**. The connected GitHub connector can create/merge PRs but may not expose a manual `workflow_dispatch` call; use Codex/CLI or GitHub Actions UI only when a manual rerun is necessary.
- Do not claim website publication until GitHub API reports Pages enabled and an actual successful Pages deployment is verified. Public URL pattern: `https://harman-f.github.io/mhi2_altscreen_carplay/`. `main` file publication and GitHub Pages deployment are different stages.

## Scoring and UI conventions

- `Implemented`: directly supported by source/documented public package (with exact platform); **not** automatic physical vehicle acceptance.
- `Partial / experiment`: partial code, lab/HU result or limited author vehicle report, with caveat.
- `Announced / planned`: intent or developer claim with no complete public tested source.
- `Unsupported`: explicitly negated for exact platform/firmware/hardware.
- `Unknown / not stated`: absent or unverified evidence. Never coerce to no.
- Checkmarks in technical matrices are **status indicators**, not working enable/disable controls. The actual filter controls are search/selects with result counts.

## Update response to user

Report: dated source cutoff and old/new row counts; new canonical repository additions/redirects/forks; published vs reported findings; regression/withdrawal risks; exact PR/merge, CI outcome and Pages status; remaining unknowns, especially for the user's Škoda MU1440. Do not overstate completed 22-feature audits.
