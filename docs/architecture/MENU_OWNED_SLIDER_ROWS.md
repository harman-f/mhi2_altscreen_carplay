# Menu: owned slider rows for safe-area edges and cockpit zoom

**Status:** source-implemented and host-tested; vehicle acceptance of the final build is pending. This page
describes the design of the `modules/menu/source` implementation, not an accepted vehicle result. See
[feature evidence](../status/FEATURE_STATUS.md) for the current acceptance state and
[Navigation composition](NAVIGATION_COMPOSITION_AND_SAFEAREA.md) for what the safe-area values mean.

## What the user sees

- In each safe-area page (Full, Wide, Center) the four edges Left, Top, Right and Bottom are shown as collapsed
  rows "label + value". A tap expands the row and shows a stock-looking slider row below it with minus and plus
  buttons; a second tap collapses it. Only one row is expanded at a time and a page change collapses it.
- The cockpit zoom row on the scaling page works the same way (Skoda profile only). The main-display zoom and the
  physical-size rows remain dropdowns.
- Reset and hint rows are unchanged.

## Rows and storage

| Topic | Design |
| --- | --- |
| Row type | The slider row is an item the menu builds itself from the widget classes the stock tree builder uses (slider, two push buttons, images, container, list item), with init argument lists that match the stock sound-menu row. It has its own clone data; the stock handler of another view is never loaded, so no foreign clone data can reach the settings list. |
| Insertion | The model adds the slider row at render time; no menu file or catalog change is needed, so existing menu files keep working. |
| Safe-area storage | Unchanged `x,y,w,h` (broker, view profile, GEN2, configurator). The edge model converts only in the menu: x = left, y = top, w = right - left, h = bottom - top. |
| Validation | Edges are clamped against the opposite edge. The minimum size stays 100 x 60 px, identical to the broker's rectangle check, so every slider position is a value the broker accepts (host-tested for all positions). |
| Steps | Left/Right 0..1010, Top/Bottom 0..376, slider step 10 px; the minus/plus buttons move one pixel. |
| Zoom slider | 6 discrete positions, slider 0..5, step 1: `AUTO, 70, 85, 100, 125, 150` (same order as the dropdown). The expanded header shows `Auto` or the number. The collapsed preview maps position p to the stock 9-step mini-slider image round(8p/5). |

## Save, debounce and revision

A durable set rewrites a file on the unit's flash, so a drag must not write per pixel.

1. The row and header show every value immediately (local wish).
2. The durable SET is sent only after the value was unchanged for 700 ms (`MibrSafeArea.IDLE_MS`).
3. At most one SET is in flight; while it or a refresh is running the newest wish is kept, and the final value is
   always sent (also on page leave). A wish equal to the stored value is dropped without a SET.
4. Profile-backed switches (safe areas and navigation) share one broker compare-and-swap revision. Entering a
   safe-area page re-reads the value and revision so the first SET carries the current one; a verified SET hands
   its new revision to the sibling switches.
5. On `STALE_REVISION` the menu re-reads once and re-sends the newest wish with the revision just read; if it is
   stale again the wish is dropped and the stored value shown (no retry loop). The scaling zoom uses the same path
   with its own revision.

Host tests: `MibrSafeSliderTest`, `MibrZoomSliderTest`, `MibrSafeRevisionTest` (fake broker).

## Fallback

The slider rows appear only after the slider source resolved on the running firmware profile. Any failure (other
profile, missing class, literal or image, clone or layout failure) marks the source failed and the page shows the
plain rows with their dropdowns instead. A layout failure while slider rows are shown disables them for the rest
of the HMI run (sticky) and the page is re-rendered once with the plain rows; the menu is never left because of
the slider rows. The reason is written to the HMI diagnostic log. Profiles other than the Skoda MU1440 P4526 keep
the plain rows until their widget mapping has been tested.

## Geometry applies only at CarPlay session setup

The safe-area rectangles and the cockpit zoom reach the iPhone only in the answer at CarPlay session setup (later
view-area updates carry index/adjacency only). A change made in the menu is therefore stored at once but takes
effect at the **next CarPlay connect**. The hint rows say "Applies after reconnect".

## Why there is no software USB reconnect

An earlier build offered a menu action that forced a CarPlay reconnect through the unit's USB control path so
geometry changes would apply without unplugging the phone. In a vehicle test this stopped the USB media hub; the
device launcher stayed down until the unit was rebooted. The feature (script, broker verb and the expert flag)
was removed instead of being hardened: a reliable replug needs the phone to be unplugged and plugged in, or an
approach that has been proven not to touch the shared USB hub. The broker therefore answers `INVALID_REQUEST` for
the former verb, and the documentation tells the user to unplug and replug the phone.
