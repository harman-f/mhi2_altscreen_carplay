# Module boundaries, HMI and cross-brand portability

**Status: architecture of current public baseline plus later experimental development, 21 October 2026.** This document describes independently developed integration concepts and safe interfaces, not a universal installer. A compatible Škoda/SEAT/VW logo, matching MU number or same-looking menu is never enough to prove binary compatibility.

## One system, separate responsibilities

```text
iPhone (existing authenticated CarPlay / iAP2 connection)
   |                                  |
   | ScreenAlt / type-111 H.264        | optional stock GNSS / vehicle information
   v                                  v
existing MHI2 AirPlay/DIO owner       existing DIO/iAP2 owner (no second login)
   |                                  ^
   v                                  | optional feature, only after ABI proof
GEN2 receiver / ScreenAlt control     OEM DSI --> thin Java J9 adapter
   |                                      --> validated bounded native telemetry
   | complete AU + source timestamp
   v
local tee / M1AU framing --> direct-ts-remux OR experimental parity writer
                                 |
                       one exclusive STOCK/DIRECT owner
                                 |
                   DisplayManager writev gate / isoTX2
                                 |
                       MOST150 -> Virtual Cockpit

OEM HOME / stock Settings view
     |
guarded project Java J9 menu and async MIBR/3 client
     |
authenticated bounded localhost TCP
     |
ONE native mibr-control (canonical settings core, status and action gateway)
     |                         |
durable guarded store        qualified owner ACTION/ACK
                              (NOT implicitly available from a build)
```

The GUI is neither a second settings registry nor a direct AirPlay/MOST writer. High-frequency vehicle samples do not flow through the settings broker. There is one active media writer at a time; stock Type 110 remains independent of private Type 111. GNSS/vehicle-status extension must use the **existing** authenticated iAP2 owner, not another CarPlay session.

## Runtime contracts by module

| Component | Owns | Must not own |
| --- | --- | --- |
| GEN2 / ScreenAlt | Type-111 negotiation, UI URLs, show/stop/forceKeyFrame, codec/AU generation, existing CarPlay zoom sender | Public HMI storage, independent second AirPlay session, MOST output ownership |
| Direct remux / parity candidate | Source-AU to MPEG-TS, source timestamp/PTS, packet counters and bounded writer behavior | OEM UI selection, iAP2 vehicle data, unqualified stock-display suppression |
| STOCK/DIRECT gate and session owner | Exclusive access to /dev/mlb/isoTX2, stop/STOCK and fail-closed handback | Assume DMDT routing alone means exclusive physical writer ownership |
| Native mibr-control | Schema-validated canonical settings, revision/CAS, persistence when qualified, role-scoped HMI/INPUT API, ACTION receipt | Invent successful runtime application from a stored value |
| Java menu | OEM-style presentation and async requests, pending/confirmed feedback | Direct profile writes, hidden arbitrary shell commands, its own video or zoom sender |
| Optional vehicle-data module | Typed, bounded Speed/VehicleStatus, validity, session-coordinated output through stock iAP2 worker | Fake vehicle values, competing iAP2 owner, forwarding vehicle TLV through the NMEA text API |

Settings activation classes must be handled separately: **LIVE**, **PRESENTATION** (current-session show/refresh), **SESSION** (owner transition), **RECONNECT** (actual renegotiation), and momentary **VIEW** action. Stored, materialized, advertised and ACTIVE are not synonyms.

## OEM-native HMI approach

The reference UI enters through an independent HOME/Virtual Cockpit tile and uses guarded OEM settings views. The reference work has investigated original `Ssm_5458` widget families and builds project-owned elements using stock row semantics instead of replacing the whole HMI. OEM CHECK/PLAIN/VALUE rows, Back and re-entry, scroll position and skin-aware icon selection should be preserved. A standalone user-visible menu is preferable to an entry that disappears whenever SmartLink launches active CarPlay.

```text
HOME
  └── Virtual Cockpit / CarPlay settings
        ├── Map presentation
        ├── ETA / speed limit / compass
        ├── Maneuver layout
        ├── View: Full / Center / Wide [only qualified views selectable]
        └── Advanced
              ├── CarPlay-in-cluster preference [not a blind route toggle]
              ├── Frame-rate/source persona [reconnect-gated]
              └── Diagnostics
```

Those labels represent a proposed UI design, **not** proof that all three views or all actions already work on a production unit. Existing reference menus and the developer-created HOME tile icon variants are source-specific visual work; do not extract or redistribute OEM raster skins to demonstrate them. A future visual-assets contribution should include only project-created graphics and verify ownership/provenance.

### Separating appearance, save and effect

1. **UI acceptance:** the tile is visible, selectable and Back/scroll/re-entry work with active CarPlay.
2. **Store acceptance:** a revision-consistent validated value can be saved and read independently.
3. **Apply acceptance:** GEN2/owner sees the right desired revision; a current-session show/reconnect or route action is executed as appropriate.
4. **ACTIVE acceptance:** the qualified owner correlates original request ID, session/generation, visible VC state and actual per-key effect. Pending or unknown must not be presented as a successful switch.
5. **Release acceptance:** exact target, credentials, original hashes, rollback, mount/RO recovery and power-cut tests have their own evidence.

The October 20 reference-vehicle HMI test did not close (3)–(4) for five presentation controls. A source-built scrollbar/third-view candidate cannot close them either.

## Reusing the idea on SEAT and Volkswagen

**Likely portable:** logical menu grouping, controller protocol design, canonical schema, request/ACK semantics, H.264/TS source contracts, testing vocabulary, and a host-tested OEM-widget adapter interface.

**Target-specific until proven otherwise:** firmware/J9/classfile ABI, ViewHandler and widget IDs, stock HOME dispatch/CIO slots, skin and icon resources, source menu geometry, package loader, DSI event and key tuple, AID visible/focus source, Map/FPK display routing, original MOST encoder and installed JAR coexistence. Layout constants must be measured on the actual cluster. A 10.x-inch AID10-class reference does not qualify older 12.3-inch clusters.

A porting sequence should be: read-only compatibility report -> classify exact firmware and fitted display -> obtain original stock HOME/Settings view and target widgets -> build a **UI-only, no-write, no-controller** probe -> test OEM return and scrolling -> qualify canonical controller adapter separately -> qualify video owner and real VC/phone presentation -> only then install with exact backup/rollback. Never paste MU1440 widget IDs into a SEAT/VW build as if they were public cross-brand APIs.

## Public development versus vehicle qualification

The public September media baseline is vehicle-demonstrated; newer GEN2, HMI, controller and telemetry branches remain individually reviewed candidates. Read [integration status](../status/INTEGRATION_STATUS_2026-10-21.md), [research publication policy](../maintainer/ISSUE_AND_PUBLICATION_POLICY.md), and exact target [vehicle tests](../testing/VEHICLE_TEST_PROTOCOL.md) before adopting any experimental component.
