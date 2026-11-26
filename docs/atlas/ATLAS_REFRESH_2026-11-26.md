# MIB Atlas source refresh — 26 November 2026

**Public-source review:** 26 Nov 2026, Europe/Berlin. Delta from [25 Nov](ATLAS_REFRESH_2026-11-25.md). Targeted review of public release lists, default-branch commits and recent issue discussions, plus public repository discovery. No independent physical tests, no firmware modifications and no complete catalog re-score. Original 4 Nov 58×22 baseline and 56 active curated entries remain unchanged.

## Native wireless — omonob and tomasz

- [omonob V3.2](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/releases/tag/v3.2) remains the latest experimental tag (17 Nov UTC / release text 18 Nov); default-branch head remains aec37f5 (17 Nov). Release explicitly excludes a separate full implementation-source archive and build tools. Public glue/installer material is not the complete reproducible receiver. The two previously documented Škoda MU1440/P4526 user reports remain the highest positive evidence; no additional MU1440 vehicle acceptance identified in this pass. Exact AID part in #73 and endurance, map centering, audio and touch acceptance remain unresolved.
- [#80](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/issues/80), opened 26 Nov, reports an explicit-migration refusal. Setup and root cause are not established; no supported fix confirmed. Do not bypass migration or fingerprint guards.
- [#54 NAR update](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/issues/54#issuecomment-7194008810), 26 Nov: owner supplies P3662/MU1418 hardware details (5NA035026D, AID 5G1920791B SW4191) and offers a backup. Maintainer had explicitly excluded MU1418 and MU1126/P3659_2 from official V3.2 native profiles; a partial community MU1126 adaptation is not MU1418 evidence. [tomasz #3](https://github.com/tomasz-twardzicki/MHI2-Carplay-Maps/issues/3#issuecomment-7193639104) also gained a test volunteer, not an implemented port.
- [tomasz MU1367-v1.6.7-e](https://github.com/tomasz-twardzicki/MHI2-Carplay-Maps/releases/tag/MU1367-v1.6.7-e) remains latest experimental tag, stable v1.6.1 separate; no new 790 field acceptance found. Do not infer native wireless on other firmware.
- [congobg MHI2Q_WiFi_CarPlay](https://github.com/congobg/MHI2Q_WiFi_CarPlay) has no newer tagged release or default-branch commit in this review. Native head-unit track unchanged.

## USB dongles — two materially relevant deltas

### CatPlay V0.33.0 — 26 Nov

[Release](https://github.com/catplay-labs/catplay/releases/tag/v0.33.0) published 17:19 UTC, [fix e8ecca9](https://github.com/catplay-labs/catplay/commit/e8ecca903fa14021ce1d2cebc0707af24df5a451), [CatPlay #72](https://github.com/catplay-labs/catplay/issues/72), [LuKa #117](https://github.com/luka-dev/mib2q-carplay-rgi/issues/117). An Audi MIB2 AltScreen interoperability report describes successful USB/iAP2 negotiation followed by /info deserialization failure with primaryInputDevice=0. The fix represents zero as Unknown and preserves it during metadata proxying; binary regression tests cover primary and secondary displays. This is a released protocol compatibility fix, not a post-fix car acceptance. Additional changes include audio RTP thread separation, Bluetooth connection profile responses and HID handling when AltScreen is unavailable. No new firmware-tree commits in this release; hardware compatibility/recovery boundary unchanged. Not native MHI2 wireless.

### kamgurgul HW301 v1178 — 25 Nov

[Author documentation commit bf9f487](https://github.com/kamgurgul/mib2q-carplay/commit/bf9f48749b12f63eff0987b24e2fd78d2ba8192a), [#68](https://github.com/kamgurgul/mib2q-carplay/issues/68). HW301 adapter v1178 retains the latest updateViewArea from the head unit and uses the corresponding initialViewArea/adjacentViewAreas for a reconnecting phone within the existing car session. Car test reported passed 25 Nov; no logs saved per findings. v1179 is the logging variant; v1176 is the prior image. Head-unit release tag remains v1.5, and 1.6 changelog is development material. This evidence is MHI2Q/adapter-specific and not proof of equivalent behavior in native Škoda MU1440. Long route/rerouting and Wi-Fi-loss tests remain open per source.

## LuKa MHI2Q — new field evidence, no newer tagged release

[Release list](https://github.com/luka-dev/mib2q-carplay-rgi/releases) still latest MHI2Q-2026-11-04. The default branch includes 24 Nov merges [#109](https://github.com/luka-dev/mib2q-carplay-rgi/pull/109) (console keys) and [#110](https://github.com/luka-dev/mib2q-carplay-rgi/pull/110) (spokenAudio/empty APAP kind); distinguish commits from published release.

- [#118](https://github.com/luka-dev/mib2q-carplay-rgi/issues/118), 26 Nov: 2018 Audi A4 B9 Brazil, internal amp, P5092/MU1329 after P4212/MU1177, wired CarPlay. Reports cockpit map and Google Maps native RGI arrows/lane/distance on original pre-0379 cluster build 1290. Not a universal older-cluster claim; Waze shows map only.
- [#119](https://github.com/luka-dev/mib2q-carplay-rgi/issues/119), 26 Nov: same setup, Waze cards initially centered but shift left after full→compact→full VIEW change. Reporter hypothesizes unchanged URL prevents re-sending showUI after updateViewArea; hypothesis unverified, no released fix. Relevant comparative lead for view/safe-area research, not proof of MU1440 root cause.
- [#120](https://github.com/luka-dev/mib2q-carplay-rgi/issues/120), 26 Nov: Audi B9 B&O, US P5087/MU1316, Ottocast Mini Dot 26090815.6071. Wired works; adapter gives video/cluster map but no audio with buffered type-103 advertised. Reporter restored audio by disabling spatial audio at startup; 5.1/upmix lost. Report-specific workaround, not generalized fix or native wireless evidence.
- [#116](https://github.com/luka-dev/mib2q-carplay-rgi/issues/116), 25 Nov: Baseus BS-CG027 adapter 26031311.2705.1 fails Sport-view scaling/tracking although wired works; unresolved.

## Other tracked sources

chrzanowy v1.9.0 and PerkTheFox ContiTool v2.2.1 remain latest releases; no new AID firmware acceptance established. No additional independently evidenced classic-MHI2 native receiver found in targeted discovery. Source report and topical entries updated; historical scoring, rows, lineage and diagrams unchanged. Public links only; no donor data, private communications or installation bypasses included.
