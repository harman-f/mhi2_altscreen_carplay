# Optional classic vehicle-data integration — design overview

The project-authored [vehicle-data adapters](../../src/native/vehicle-data/) are included in the [R38 GEN2 source baseline](../build/MU1440_R50_SOURCE.md). Their inclusion and native build do not establish phone acceptance of every optional field; validity and current-session evidence remain required.

**Status (21 October 2026):** independent feature research and host-built candidates, NOT a currently installed or end-to-end vehicle-validated part of the public developer release.

## Scope

The current reference design preserves the original OEM GPS/GNSS service and the existing authenticated CarPlay/iAP2 session. It investigates optional transmission of *actual*, validity-checked car data. The planned feature surface is: VehicleSpeed, a classic vehicle-status report for range and ambient temperature, and a genuine reserve-warning state. Engine/powertrain capabilities must describe the fitted vehicle accurately. EV, fuel percentage and unsupported warning content are not synthesized.

## Separate components

```text
Existing OEM DSI vehicle state
       |
Optional target-specific thin Java/J9 adapter
       |
Bounded native snapshot with validity, unit, generation and source time
       |
Existing authenticated DIO/iAP2 service owner
       |                         |
stock GNSS / optional speed     separate optional vehicle status
       |                         |
       +--------- current CarPlay session --------+
```

This is one **logical optional feature** with two distinct language/build artifacts: a J9-compatible original-data adapter and a native QNX module. They are not a replacement OEM DIO binary, a competing iAP2 owner, or an additional ScreenAlt stream. Exact native loader attachment, same-owner session/queue and final target ABI have not been approved; without such evidence the feature remains disabled.

## Interface discipline

| Function family | Original source / feature responsibility | Development boundary |
| --- | --- | --- |
| GPS/GNSS | Existing NMEA output and original session lifecycle | Preserve stock output unchanged |
| VehicleSpeed | Existing OEM high-frequency vehicle state, actual signed direction/standstill and unit validity | Own bounded versioned sample records and stale-source suppression |
| Speed forwarding | Optional interoperable speed message through the existing original location-data worker | Must honor the phone's accepted capability/request and prevent duplicate original speed delivery |
| Vehicle status | Actual OEM range, temperature and reserve warning only | Separate typed current-session status path; never disguised as GPS text |
| Shared session coordination | Authenticated owner, accepted feature subscription and ordered Stop/teardown | No stale samples or queued send after a subscription stops |

Synthetic host test vectors can validate our own sample conversions and state machines. They cannot demonstrate that the iPhone accepted the feature, that a current DSI source was read, or that a visual navigation application displayed any field.

## Pending qualification

1. Prove the exact fitted vehicle's DSI units, lifecycle and current validity values without changing OEM services.
2. Identify a supported way to attach the optional adapters to the **already existing** worker/owner; do not infer an integration ABI from an exported name.
3. Check active feature negotiation, session generation, request/stop and original GNSS coexistence.
4. Perform separate host/QNX/Java tests and authorized passive vehicle-plus-phone acceptance before making an installer or advertising an enabled UI toggle.

This public summary contains original project architecture and research goals only. It does not incorporate extracted platform binaries, original code analyses or private phone/session captures. See [module architecture](MODULE_BOUNDARIES_AND_PORTABILITY.md) and [integration status](../status/INTEGRATION_STATUS_2026-10-21.md).
