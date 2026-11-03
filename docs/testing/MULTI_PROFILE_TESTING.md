**Beta policy (2026-11-03):** All three profiles are part of the same normal beta installer and release; no special SEAT vehicle approval is required before including software in beta tests. Final combined system/vehicle testing remains open. Existing software/static tests are the current baseline. Missing exact MU1409 identity and genuine compiled Java adapters remain concrete build/installer inputs, not a reason to exclude SEAT from the release graph.

# Multi-profile research and tester reports

The distribution contract separates common CarPlay/video, broker/input, menu,
and navigation modules from symmetric firmware profiles. The shared default
menu is deployed with the package; the editor changes menu structure, labels,
order and visibility. It does not select the firmware adapter.

| Profile candidate | Firmware | Evidence and remaining acceptance |
| --- | --- | --- |
| `skoda-mu1440-p4526` | `MHI2_ER_SKG13_P4526_MU1440` | Existing reference-vehicle observations concern pinned earlier configurations. A reorganized package still needs its own installation/runtime acceptance. |
| `seat-mu1409-p4708` | `MHI2_ER_SEG11_P4708_MU1409` | Target Java build and static integration candidate; native HOME/menu, icon, wheel behavior, geometry and actual CarPlay output await vehicle acceptance. |
| `seat-mu1447-p4709` | `MHI2_ER_SEG11_P4709_MU1447` | Target Java build and focused firmware delta candidate; independent vehicle acceptance remains open. |

These are exact firmware candidates, not support for every car with the same
MU number. The profile selector uses the SHA-256 of the original `/ifs/lsd.jxe`
and requires exactly one match. Unknown or ambiguous identities must refuse
before persistent writes. A matching fingerprint identifies firmware, not the
installed cluster hardware or a successful vehicle test.

## What testers can contribute

Use the existing [vehicle-test report](https://github.com/harman-f/mhi2_altscreen_carplay/issues/new?template=vehicle-test.yml)
for reproducible external observations. Record exact firmware train/MU, car
model/year, cluster hardware if known, package/source identity, phone/iOS and
navigation app. Distinguish a stored selection, a requested setting, received
video and the actual visible result.

Useful observations include first connection/cold start, original main CarPlay,
cockpit video/reconnect, native menu entry/Back/focus, first icon appearance and
pressed/day/night states, wheel behavior, Wide/Full/Center geometry, settings
persistence and recovery. Preserve the original behavior and an independent
recovery route. Follow the [vehicle-test protocol](VEHICLE_TEST_PROTOCOL.md).

For SEAT visual preview work, redacted photos of the native HOME screen, setup
list, dropdown, selected item and day/night states are particularly useful.
The current menu editor has a Škoda-styled preview and a deliberately neutral
SEAT preview. Static widget geometry is not an authenticated visual skin.

## Package and source availability

The [package layout contract](../build/PACKAGE_LAYOUT.md) requires one shared
menu and editor, platform-owned JARs/icons/display/input/integration information,
and project source/build inputs in the same ZIP with a separate source inventory.
RGI route-guidance source is already published under `modules/navigation/source`;
album-art is not part of this candidate.

This documentation does not yet publish a complete three-platform installer or
OEM-derived files. A distributable package requires provenance-cleared contents,
accurate per-component source/build coverage and its own checks. Retained helper
JARs or binaries without a closed build chain must remain identified as gaps.
See [the current source build](../build/MU1440_MENU_RGI_SOURCE.md) for what can be
built from the public tree today.
