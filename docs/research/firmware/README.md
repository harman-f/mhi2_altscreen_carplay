# Firmware, cockpit compatibility and portability research

[Research library](../README.md) · [Exact compatibility matrix](../../testing/COMPATIBILITY_MATRIX.md) · [Current profiles](../../../modules/profiles/)

A shared implementation does not make distinct MHI2 firmware trains, OEM menus or instrument-cluster panel generations interchangeable. **Exact firmware hash**, **Java API input**, **display transport** and **actual vehicle behavior** are independent compatibility dimensions.

## Exact firmware and baseline evidence

- **[MU1440 stock reference](MU1440_STOCK_REFERENCE.md)** — exact tested stock components and their original scope.
- **[MHI2 cross-firmware implementation map](MHI2_FIRMWARE_PROFILE_MAP_2026-09-28.md)** — compared firmware libraries/ABI and portable components.
- **[Patch portability estimate](MHI2_PATCH_PORTABILITY_ESTIMATE_2026-09-28.md)** — estimates for transferring specific Stream-111, navigation and gate changes; **an estimate is not a build or vehicle acceptance**.
- **[MU1438/MU1440 offline comparison](MU1438_MU1440_OFFLINE_COMPARISON_2026-09-28.md)** — exact-target static differences.
- **[Audi B9 MU1438 lead](AUDI_B9_MU1438_COMPATIBILITY_LEAD_2026-09-28.md)** — comparator lead, not supported Audi release.

## Cockpit/FPK and system access

- **[MIB2 cluster/display transport knowledge base](MIB2_CLUSTER_DISPLAY_TRANSPORT_KNOWLEDGE_BASE.md)** — screen families, MOST/LVDS distinctions and reference implementations.
- **[FPK firmware and control access](FPK_FIRMWARE_AND_CONTROL_ACCESS.md)** — access and protocol findings; confirm hardware identity before extrapolating.

## How this links to the present

The current public source includes **three exact firmware profiles** (Škoda MU1440, SEAT MU1409 and MU1447). This does not automatically qualify them for end-user installation. [Current profile source](../../../modules/profiles/README.md) · [Multi-profile acceptance](../../testing/MULTI_PROFILE_TESTING.md) · [Package status](../../packages/README.md).

[Hardware/boot research](../hardware/README.md) · [Research/archival rules](../AGENTS.md).
