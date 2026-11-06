# CarPlay protocols, iOS sender and presentation research

[Research library](../README.md) · [Documentation home](../../README.md) · [Current features](../../status/FEATURE_STATUS.md)

**Scope:** How the phone negotiates an auxiliary screen, sends Stream 111, changes navigation ownership and responds to UI/geometry requests. These documents are dated findings; the authoritative receiver source is in [CarPlay module](../../../modules/carplay/).

## Protocol and observed sender behavior

- **[Stream-111 protocol contract](STREAM111_PROTOCOL.md)** — transport endpoint, configuration, firewall/port ownership and session boundaries; read together with the [current vehicle test protocol](../../testing/VEHICLE_TEST_PROTOCOL.md).
- **[iOS 27 sender lifecycle](IOS27_SENDER_LIFECYCLE.md)** — sender ownership, connect/disconnect, suggested UI and endpoint transitions. Research evidence, not a new installed release claim.
- **[PlatformControl flight recorder](PLATFORMCONTROL_FLIGHT_RECORDER.md)** — capture/diagnostic design and event interpretation.

## Cluster capabilities and interface effects

- **[CarPlay cluster configuration index](CARPLAY_CLUSTER_CONFIGURATION_INDEX_IOS26_7_1_2026-10-01.md)** — keys, display contexts and source-era defaults.
- **[Function/frontend-effect matrix](CARPLAY_CLUSTER_FUNCTION_FRONTEND_MATRIX_IOS26_7_1_2026-10-01.md)** — which settings have a source implementation, UI surface or observed effect; distinguish these layers.
- **[ViewArea state model](VC_VIEWAREA_STATE.md)** — negotiated ViewArea state, runtime selection and SafeArea relationship.
- **[Cluster Ultra research closeout](CARPLAY_CLUSTER_ULTRA_CLOSEOUT_2026-10-03.md)** — scope of the October investigation and exclusions, not a product certification.

## Current outcome

The [reference vehicle](../../media/mu1440-stream111-poc-2026-09-29/README.md) demonstrated moving CarPlay auxiliary maps on **Škoda MU1440/AID10**. Current Java, settings and firmware-profile implementation must be assessed separately in the [feature matrix](../../status/FEATURE_STATUS.md). Actual phone route-arrow data is distinct from CarPlay map video and composited ETA/compass controls.

[Media/MOST research](../media/README.md) · [Current navigation composition architecture](../../architecture/NAVIGATION_COMPOSITION_AND_SAFEAREA.md) · [Research and archival rules](../AGENTS.md).
