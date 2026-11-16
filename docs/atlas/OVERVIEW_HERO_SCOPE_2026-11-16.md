# Overview-only MIB Atlas hero

**Date:** 16 November 2026. **Scope:** HTML site presentation only.

## User-requested behavior

- The global **slim upper header** (MIB Atlas logo / issue feedback link / light-dark toggle) remains visible on every topical view.
- The **nine-tab topic selector** also remains globally visible, directly underneath that slim header. Its high-contrast tab labels and sticky behavior are preserved.
- The **large MIB Atlas hero banner** — research review date, large wordmark/title, introductory paragraph, **56 / 22 / 92 / 16 Nov** statistic cards and the issue #187 information banner — now lives as the very first child of the **Overview** panel. It is not a shared header; when any other topic is selected, the entire hero is hidden by existing CSS-only tab visibility.
- The small global `MIB ATLAS` header brand increases from **13px to 16px**, without increasing top-bar height or adding a duplicate title.
- The global logo anchor `#top` targets Overview's hero. Existing hash-navigation script detects that panel and switches to Overview if clicked from another tab.

## Structural checks

`nav < topic-tabs < main < overview-panel < hero < overview-introduction < comparison-panel`; one hero, one statistics grid and one public feedback banner; 56 × 22 original curated rows, 56 cards, nine tab panels and nine filter tables unchanged. There is no source re-scoring or new compatibility claim.

No vehicle data, firmware files or binaries changed.
