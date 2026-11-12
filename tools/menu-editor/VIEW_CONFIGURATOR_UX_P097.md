# P0.9.7 – Safe Area OEM layering and duplicate-rendering stabilization

Basis P0.9.6 (Draft PR #172), 12.11.2026. No changes to cockpit SVG geometry.

## Verified causes
1. The P0.9.6 renderer cloned all calibration labels to a separate `sa-grid-foreground` group **after** the OEM SVG group. This drew numeric coordinates over opaque gauge faces. The correct paint order is now base grid → original numeric labels → configured Safe Area outline → OEM shell, optional mask and visible native SVG groups. There is no independent coordinate clone; an enabled grid is permitted to be covered by OEM elements.
2. The SVG for Center has `center-left-info` *inside* `center-left-dial`, and `center-speed` *inside* `center-right-dial`. The Safe Area renderer cloned both parents **and** these descendants, causing duplicate `0 km / Ab Start` and `0 km/h`. Source groups now undergo ancestor/descendant filtering before cloning, applied uniformly to all views.

## Explicit non-goals
- No further movement of tubes, trapezoid edges, Full cutouts, shared top/bottom anchors or native road data. All P0.9.5 numeric-grid calibration remains unchanged.
- No changes to the existing source SVG files or inlined view art, except the in-page Safe Area preview logic.
- No changes to Safe Area coordinates, exported project/vehicle formats, menu editor, or QNX runtime.
- The cosmetic perimeter shell remains visual-only and **not** an added blocked region.

## Acceptance
- Center shows one `0 km`, one `Ab Start`, one `km/h`, one `0`; the nested source nodes are not independently cloned.
- The native `sa-grid-numbers` group paints *before* OEM edge/mask/preview; the foreground duplicate group no longer exists.
- All three views pass smoke and Chromium tests on desktop and iPhone-sized viewport, with screenshots in OEM-only and mask/both modes.
- `mibr-menu-editor-nav-views-p097.html` is a dedicated review snapshot. P0.9.6 remains unchanged; PR stays Draft pending visual Safari acceptance.
