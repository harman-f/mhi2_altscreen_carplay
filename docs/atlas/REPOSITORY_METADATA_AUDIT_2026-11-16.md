# All 58 Atlas entries: public repository metadata audit

**Research status · 2026-11-16.** 58 GitHub REST repository identity lookups were attempted. This is a **full identity / reachability / fork-lineage pass** on all 58 existing entries, **not** a complete independent re-test of each of the 22 functionality columns. Last-push timestamps are Git metadata, not release, vehicle, feature or compatibility proofs.

## Verification outcome

- **58** Atlas entries inspected for GitHub identity, activity and provenance.
- **56** old paths returned public repository metadata directly; **1** old `omonob/MHI2-Carplay-Maps` path redirected to canonical [`omonob/VW-MHI2-Carplay-Maps`](https://github.com/omonob/VW-MHI2-Carplay-Maps), which is accessible; **1** historical Tiguan fork `ALeXXBody/mib-cluster-map-tiguan` returned 404 and search did not identify a replacement.
- **57** public repositories are currently resolvable (56 direct + 1 canonical redirect); **1** is a retained historical, unavailable record. Do not call all 58 currently accessible.
- **14 explicitly identified GitHub forks** have exact parents (listed below). Fork status is a lineage fact, **not** a judgment that the fork contains no new code.
- The original `58×22` capability matrix and 58 technical cards are retained. Unknown, missing repository and fork-only proof must **not** be promoted to vehicle proof without specific evidence.

## Current public release deltas (separate from 4 Nov capability scores)

| Project | Current source anchor | Status / precise scope |
| --- | --- | --- |
| [kamgurgul/mib2q-carplay](https://github.com/kamgurgul/mib2q-carplay/releases/tag/v1.5) | v1.5 released **15 Nov 2026** | Baidu/AMap/Yandex roundabouts, 111 lifecycle/end-of-session fix, Android Auto Q7/Yandex safe areas, faster software decoder; exact adapter and AA vehicle proof must still be checked |
| [MacsInSpace/mib-cluster-map](https://github.com/MacsInSpace/mib-cluster-map/releases/tag/v1.2.4) | v1.2.4 released **14 Nov 2026** | Accelerated NEON decoding revised after v1.2.2 crash and v1.2.3 rollback. **v1.2.4 acceleration is not yet tested in car** per the release |
| [ProManiFest2122/mhi2-k3346-carplay-vc](https://github.com/ProManiFest2122/mhi2-k3346-carplay-vc/releases/tag/v2.0.1-rc1) | Stable 2.0.0 **14 Nov**; test HUD rc1 **15 Nov** | HUD third-option switch remains an unaccepted vehicle test; MU1438/K3346 only |
| [chefranov/mhi2-au37x-carplay](https://github.com/chefranov/mhi2-au37x-carplay/releases/tag/v1.1.12) | v1.1.12 released **14 Nov** | Arrow fill and lane-clearing change; older AU37x P3242 EU installs blocked by v1.1.11 |
| [perkthefox/mst2-cluster-nav](https://github.com/perkthefox/mst2-cluster-nav/releases/tag/v1.1.0) | v1.1.0 **9 Nov** | **Withdrawn for head-unit reset-loop report**; v1.0.0 remains author-directed reference |
| [omonob/VW-MHI2-Carplay-Maps](https://github.com/omonob/VW-MHI2-Carplay-Maps/releases/tag/toolbox-plaintext-v2.1.0-rc.7) | Stable v2.0.1 Oct 27; experimental rc.7 Nov 4 | New canonical repo path, no full real-phone/cluster acceptance of info-module and no released native wireless receiver |
| [perkthefox/mqb_contitool](https://github.com/perkthefox/mqb_contitool/releases/tag/v2.1.2) | v2.1.2 **15 Nov** | Distinct Continental/Vitesco J533/CP research; not a CarPlay/VC video repo |

## Full source roster

| # | Original canonical entry / source | GitHub availability | Fork parent (if recorded) | Last public push (UTC date) |
| ---: | --- | --- | --- | --- |
| 1 | [perkthefox/mst2-cluster-nav](https://github.com/perkthefox/mst2-cluster-nav) | Public API OK | — | 2026-11-09 |
| 2 | [ekuka86/audi-mhi2-carplay-hud](https://github.com/ekuka86/audi-mhi2-carplay-hud) | Public API OK | — | 2026-10-26 |
| 3 | [zakklmv/MHI2-Carplay-Maps](https://github.com/zakklmv/MHI2-Carplay-Maps) | Public API OK | Fork of [omonob/VW-MHI2-Carplay-Maps](https://github.com/omonob/VW-MHI2-Carplay-Maps) | 2026-10-25 |
| 4 | [ProManiFest2122/mhi2-k3346-carplay-vc](https://github.com/ProManiFest2122/mhi2-k3346-carplay-vc) | Public API OK | — | 2026-11-15 |
| 5 | [korhojoa/mib2-extenders](https://github.com/korhojoa/mib2-extenders) | Public API OK | — | 2026-10-31 |
| 6 | [eupn/audi_tt_8s_mu1339_altscreen111_carplay](https://github.com/eupn/audi_tt_8s_mu1339_altscreen111_carplay) | Public API OK | — | 2026-10-16 |
| 7 | [1mikew/mst2-altscreen-carplay](https://github.com/1mikew/mst2-altscreen-carplay) | Public API OK | — | 2026-11-10 |
| 8 | [MacsInSpace/mib-cluster-map](https://github.com/MacsInSpace/mib-cluster-map) | Public API OK | — | 2026-11-14 |
| 9 | [stevenzhr/MU1320-CarPlay-RGI](https://github.com/stevenzhr/MU1320-CarPlay-RGI) | Public API OK | — | 2026-10-03 |
| 10 | [aberbic/Audi-MHI2-Virtual-Cockpit-Altscreen-CarPlay-AndroidAuto](https://github.com/aberbic/Audi-MHI2-Virtual-Cockpit-Altscreen-CarPlay-AndroidAuto) | Public API OK | — | 2026-10-03 |
| 11 | [kamgurgul/mib2q-carplay](https://github.com/kamgurgul/mib2q-carplay) | Public API OK | — | 2026-11-15 |
| 12 | [joeyQuery/MHI2-altScreen](https://github.com/joeyQuery/MHI2-altScreen) | Public API OK | — | 2026-11-01 |
| 13 | [wasimlhr/mib2q-android-auto-cluster](https://github.com/wasimlhr/mib2q-android-auto-cluster) | Public API OK | Fork of [luka-dev/mib2q-carplay-rgi](https://github.com/luka-dev/mib2q-carplay-rgi) | 2026-10-30 |
| 14 | [ipaifix/mst2-carplay-scale](https://github.com/ipaifix/mst2-carplay-scale) | Public API OK | — | 2026-10-02 |
| 15 | [waterfalldev/mib2q-carplay-enhanced-nonfpk](https://github.com/waterfalldev/mib2q-carplay-enhanced-nonfpk) | Public API OK | Fork of [luka-dev/mib2q-carplay-rgi](https://github.com/luka-dev/mib2q-carplay-rgi) | 2026-11-08 |
| 16 | [harman-f/mhi2_altscreen_carplay](https://github.com/harman-f/mhi2_altscreen_carplay) | Public API OK | — | 2026-11-16 |
| 17 | [yuedizhibo/MHI2Q-CarPlay-AltScreen](https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen) | Public API OK | — | 2026-10-21 |
| 18 | [edzenis/mib2high-carplay-altscreen-rgi](https://github.com/edzenis/mib2high-carplay-altscreen-rgi) | Public API OK | — | 2026-10-14 |
| 19 | [chopinwong01/mhi2-android-auto-video-vc](https://github.com/chopinwong01/mhi2-android-auto-video-vc) | Public API OK | — | 2026-09-24 |
| 20 | [omonob/VW-MHI2-Carplay-Maps](https://github.com/omonob/VW-MHI2-Carplay-Maps) | **Renamed canonical repo** | — | 2026-11-04 |
| 21 | [Lanye-z/MHI2Q-CarPlay-MMI-Mirror](https://github.com/Lanye-z/MHI2Q-CarPlay-MMI-Mirror) | Public API OK | — | 2026-10-09 |
| 22 | [chefranov/mhi2-au37x-carplay](https://github.com/chefranov/mhi2-au37x-carplay) | Public API OK | — | 2026-11-14 |
| 23 | [xPaiiN/mst2-carplay-vc](https://github.com/xPaiiN/mst2-carplay-vc) | Public API OK | — | 2026-11-15 |
| 24 | [kkrvch/mib-std2-kombibridge](https://github.com/kkrvch/mib-std2-kombibridge) | Public API OK | — | 2026-10-30 |
| 25 | [luka-dev/mib2q-carplay-rgi](https://github.com/luka-dev/mib2q-carplay-rgi) | Public API OK | — | 2026-11-12 |
| 26 | [adi961/mib2-android-auto-vc](https://github.com/adi961/mib2-android-auto-vc) | Public API OK | — | 2026-10-12 |
| 27 | [grajen3/mib2-lsd-patching](https://github.com/grajen3/mib2-lsd-patching) | Public API OK | — | 2024-01-08 |
| 28 | [OneB1t/VcMOSTRenderMqb](https://github.com/OneB1t/VcMOSTRenderMqb) | Public API OK | — | 2026-06-07 |
| 29 | [OMKE/wireless-carplay-virtual-cockpit](https://github.com/OMKE/wireless-carplay-virtual-cockpit) | Public API OK | — | 2026-10-19 |
| 30 | [tehfalcon-vw/mhi2-nar-carplay-maps](https://github.com/tehfalcon-vw/mhi2-nar-carplay-maps) | Public API OK | — | 2026-11-02 |
| 31 | [tehfalcon-vw/mhi2q-nar-carplay-maps](https://github.com/tehfalcon-vw/mhi2q-nar-carplay-maps) | Public API OK | — | 2026-11-02 |
| 32 | [MrGame11/mib-std2-AAtoKombi](https://github.com/MrGame11/mib-std2-AAtoKombi) | Public API OK | — | 2026-10-31 |
| 33 | [Matze89x/mst2d-carplay-aid](https://github.com/Matze89x/mst2d-carplay-aid) | Public API OK | Fork of [tehfalcon-vw/mst2-nar-carplay-maps](https://github.com/tehfalcon-vw/mst2-nar-carplay-maps) | 2026-11-12 |
| 34 | [evanj495/mib2-carplay-rgi-altscreen](https://github.com/evanj495/mib2-carplay-rgi-altscreen) | Public API OK | Fork of [Allemon/mib2-carplay-rgi-altscreen](https://github.com/Allemon/mib2-carplay-rgi-altscreen) | 2026-10-02 |
| 35 | [yety-ua/mhi2-k3346-carplay-audio-upmix](https://github.com/yety-ua/mhi2-k3346-carplay-audio-upmix) | Public API OK | Fork of [ProManiFest2122/mhi2-k3346-carplay-vc](https://github.com/ProManiFest2122/mhi2-k3346-carplay-vc) | 2026-11-03 |
| 36 | [ALeXXBody/mib-cluster-map-tiguan](https://github.com/ALeXXBody/mib-cluster-map-tiguan) | **404 — historical only** | — | unknown |
| 37 | [maxim-smirnov/mhi2-carplay-cluster](https://github.com/maxim-smirnov/mhi2-carplay-cluster) | Public API OK | Fork of [luka-dev/mib2q-carplay-rgi](https://github.com/luka-dev/mib2q-carplay-rgi) | 2026-10-17 |
| 38 | [harman-f/harman-ax1800m-adapter-checker](https://github.com/harman-f/harman-ax1800m-adapter-checker) | Public API OK | Fork of [RandomGenerated543/harman-ax1800m-adapter-checker](https://github.com/RandomGenerated543/harman-ax1800m-adapter-checker) | 2026-11-03 |
| 39 | [harman-f/qemu-mhi2](https://github.com/harman-f/qemu-mhi2) | Public API OK | Fork of [iscle/qemu-mhi2](https://github.com/iscle/qemu-mhi2) | 2026-10-10 |
| 40 | [harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit) | Public API OK | — | 2026-11-13 |
| 41 | [mathsls/MHI2-Carplay-Maps](https://github.com/mathsls/MHI2-Carplay-Maps) | Public API OK | Fork of [ZzYunOvO/MHI2-Carplay-Maps](https://github.com/ZzYunOvO/MHI2-Carplay-Maps) | 2026-10-19 |
| 42 | [RandomGenerated543/seat-cupra-mu1409-carplay](https://github.com/RandomGenerated543/seat-cupra-mu1409-carplay) | Public API OK | — | 2026-10-30 |
| 43 | [octacon84/carplay-vc-dongle](https://github.com/octacon84/carplay-vc-dongle) | Public API OK | — | 2026-11-02 |
| 44 | [maxafanasiev/mib2q-carplay-wireless-cockpit](https://github.com/maxafanasiev/mib2q-carplay-wireless-cockpit) | Public API OK | Fork of [lindayi/mib2-carplay-rgi-altscreen](https://github.com/lindayi/mib2-carplay-rgi-altscreen) | 2026-10-09 |
| 45 | [KleinDevEur/mst2-eu-carplay-maps](https://github.com/KleinDevEur/mst2-eu-carplay-maps) | Public API OK | Fork of [tehfalcon-vw/mst2-nar-carplay-maps](https://github.com/tehfalcon-vw/mst2-nar-carplay-maps) | 2026-11-03 |
| 46 | [tehfalcon-vw/mst2-nar-carplay-maps](https://github.com/tehfalcon-vw/mst2-nar-carplay-maps) | Public API OK | — | 2026-11-02 |
| 47 | [tehfalcon-vw/mst2-zr-nar-carplay-maps](https://github.com/tehfalcon-vw/mst2-zr-nar-carplay-maps) | Public API OK | — | 2026-11-02 |
| 48 | [Mr-MIBonk/mhi2-android-auto-cluster-map](https://github.com/Mr-MIBonk/mhi2-android-auto-cluster-map) | Public API OK | Fork of [MacsInSpace/mib-cluster-map](https://github.com/MacsInSpace/mib-cluster-map) | 2026-10-12 |
| 49 | [cartellone99/delphi-carplay-cluster-bridge](https://github.com/cartellone99/delphi-carplay-cluster-bridge) | Public API OK | — | 2026-10-30 |
| 50 | [tehfalcon-vw/mhs2-nar-carplay-maps](https://github.com/tehfalcon-vw/mhs2-nar-carplay-maps) | Public API OK | — | 2026-11-02 |
| 51 | [tehfalcon-vw/moi3-nar-carplay-maps](https://github.com/tehfalcon-vw/moi3-nar-carplay-maps) | Public API OK | — | 2026-11-03 |
| 52 | [aftmostheart2/mst2-carplay-vc2](https://github.com/aftmostheart2/mst2-carplay-vc2) | Public API OK | — | 2026-08-21 |
| 53 | [realshaunoneill/audi-mhi2q-carplay-cockpit](https://github.com/realshaunoneill/audi-mhi2q-carplay-cockpit) | Public API OK | — | 2026-10-21 |
| 54 | [harman-f/MHI2_navignore](https://github.com/harman-f/MHI2_navignore) | Public API OK | — | 2026-09-28 |
| 55 | [harman-f/mib2-toolbox](https://github.com/harman-f/mib2-toolbox) | Public API OK | Fork of [jilleb/mib2-toolbox](https://github.com/jilleb/mib2-toolbox) | 2022-08-30 |
| 56 | [harman-f/MHI2_MIB2_AIO_FW_Update_Template](https://github.com/harman-f/MHI2_MIB2_AIO_FW_Update_Template) | Public API OK | — | 2026-09-28 |
| 57 | [tehfalcon-vw/mh2p-nar-carplay-maps](https://github.com/tehfalcon-vw/mh2p-nar-carplay-maps) | Public API OK | — | 2026-11-02 |
| 58 | [tehfalcon-vw/mst2-pq-nar-phone-nav](https://github.com/tehfalcon-vw/mst2-pq-nar-phone-nav) | Public API OK | — | 2026-11-03 |

## Follow-up acceptance criteria

1. **Matrix audit by feature:** For each row, read the exact README/current release and verify 22 capability source anchors and target platform; do not treat a pushed commit as new functionality.
2. **Fork lineage:** Compare fork-exclusive changes to its parent before grouping as distinct implementation. `wasimlhr`, `waterfalldev`, `maxim-smirnov`, `Matze89x`, `harman-f/qemu-mhi2`, `Mr-MIBonk` and others must keep their actual upstream lineage.
3. **Safety release gating:** Explicitly flag withdrawn or non-car-tested releases; map safe variants to exact firmware trains (MHI2/MHI2Q/MST2) and chipset.
4. **Unavailable source:** Retain the ALeXXBody entry as a historical lead only until a canonical replacement is verified. Do not automatically remove it and reorder rankings.
5. **New candidates:** `joeyQuery/MHI2-wirelessCarPlay`, `catplay-labs/catplay`, `iscle/qemu-mhi2`, `perkthefox/mqb_contitool` and `perkthefox/mqb-kshutz-kaput` are described in topical tabs, but only on-topic CarPlay/cluster implementations should become scored feature-matrix rows after dedicated evidence review.

**Safety and privacy:** No proprietary ECU dumps, unlock keys, raw user-uploaded chat transcripts, device identifiers or per-vehicle secrets are distributed in this report.
