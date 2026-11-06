# HMI, Java J9, menus and input research

[Research library](../README.md) · [Current menu module](../../../modules/menu/) · [Current navigation source](../../../modules/navigation/)

These notes concern OEM APIs, J9 build constraints, input events and media-control interfaces. **A proven API symbol, a source-only adapter or a saved setting is not the same as a visibly applied HMI result.**

## Source and API investigations

- **[P1-P5 media/telephone/navigation comparison](MEDIA_PHONE_P3_P5_DELTA_2026-11-04.md)** — P1/P2 source and P3/P5 overlap, ABI/vehicle evidence limits.

- **[IBM J9 / Java build notes](JAVA_J9_BUILD_NOTES.md)** — J9 API inputs, compilation constraints and build reproducibility; review together with current [Java source build](../../build/MU1440_MENU_RGI_SOURCE.md).
- **[MU1440 button input API](MU1440_BUTTON_INPUT_API.md)** — native key and button event reference and outstanding mappings.
- **[Now Playing path](NOW_PLAYING_PATH.md)** — media metadata/control-plane reference, not a finished album-art release.

## Input experiments and measured controls

- **[Keypanel / steering-wheel study library](../keypanel/README.md)** — measured F902 encoder values, Omonob/MHI2 and MHI2Q comparisons, proposed input integration.
- [Current exact physical mapping](../../testing/MU1440_MFW_RAW_KEY_MAPPING.md) · [Vehicle input test procedure](../../testing/VEHICLE_TEST_PROTOCOL.md).

Current authoritative menu state: [HMI and broker architecture](../../architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md), [feature and vehicle evidence](../../status/FEATURE_STATUS.md) and [Java/source coverage](../../status/PUBLISHED_SOURCE_COVERAGE.md).

[Research/archival rules](../AGENTS.md).
