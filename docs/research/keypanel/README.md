# Steering wheel, button and keypanel research

[Research library](../README.md) · [HMI/input overview](../interface/README.md) · [Current key mapping](../../testing/MU1440_MFW_RAW_KEY_MAPPING.md)

This collection separates observed electrical/protocol events from hypotheses about UI focus, zoom and stock-key behavior. The reports date from October 2026; they do **not** by themselves qualify the newest multi-profile Java/menu integration.

## Measured MU1440 evidence

- **[Wheel DSI / Omonob interaction and zoom](MU1440_WHEEL_DSI_AND_OMONOB_2026-10-11.md)** — native interfaces and the difference between key and encoder events.
- **[Actual F902 five-int encoder capture](MU1440_F902_FIVE_INT_ENCODER_CAPTURE_2026-10-11.md)** — **MEASURED FOLLOW-UP:** 4/40 and 4/44 ±1, superseding older uncertainty about those particular recorded event IDs.
- **[Sanitized capture matrix](MU1440_CAPTURE_SANITIZED_MATRIX.tsv)** — reproducible data for the observed events.

## Candidate integration and prior-art comparisons

- **[Omonob MHI2 wheel/encoder patch options](MU1440_OMONOB_MHI2_WHEEL_ENCODER_BINARY_PATCH_OPTIONS_2026-10-11.md)** — design options, not an installed patch.
- **[MHI2Q AltScreen zoom comparator](MU1440_MHI2Q_ALTSCREEN_ZOOM_PORT_BINARY_PATCH_OPTIONS_2026-10-11.md)** — **different platform**, not directly compatible MU1440 binary.
- **[Omonob upstream attribution](MU1440_OMONOB_UPSTREAM_ATTRIBUTION_AUDIT_2026-10-11.md)** — origin and implementation lineage.

**Current implementation and acceptance:** [menu/broker module](../../../modules/broker/) · [menu module](../../../modules/menu/) · [feature evidence](../../status/FEATURE_STATUS.md). A host mock or event capture is not a validated live focus/zoom action.

[Research/archival rules](../AGENTS.md).
