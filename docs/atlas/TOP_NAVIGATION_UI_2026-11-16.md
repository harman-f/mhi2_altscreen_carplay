# MIB Atlas — primary topic navigation positioning and visual hierarchy

**Date:** 2026-11-16. **Reason:** screenshot review found that the topic selector was hidden visually below a large hero introduction and separated from the existing slim header title; it was difficult to locate and its text was too small.

## Changes

- Move the **existing nine radio-controlled topic tabs** directly below the slim top site header and **above the hero / large MIB Atlas title**, without duplicating navigation or changing topic IDs.
- Increase tab label text from 12px to **14px** on desktop (11px to **13px** on narrow screens), increase tab padding and contrast, add a cohesive contrasted background and lower divider, and more clearly emphasize the currently selected topic with a mint/teal filled active state, border, bottom accent and shadow.
- Make both the slim brand header and the topic bar sticky: branding at `top:0`, topic navigation at `top:62px`. Preserve horizontal scrolling on smaller screens and update content/card scroll margins so deep links are not hidden behind stacked sticky bars.
- Preserve dark/light themes; light mode uses its own surface/foreground contrast. Selection still uses the original `:checked ~ .atlas-tabs` **pure CSS radio sibling selectors**; the existing optional JS maintains ARIA selection states and hash-panel activation, and is not required for basic tab switching.

## Acceptance boundaries

This is **presentation-only**. All nine topical panels, nine source-filter matrices, 56 curated 22-attribute comparison rows and source cards, 14 emulator host-OS records, 38 lineage relationships, four static graphs, HUD sections, documentation/feedback links and the Wireless V3.0 classification remain unchanged.

The Pages validation job is required before publication. This audit alone does not prove a cross-browser or physical-device visual QA pass.
