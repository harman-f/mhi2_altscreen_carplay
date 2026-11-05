# MIB Runtime feature and evidence matrix

**Documentation checkpoint: 5 November 2026.** This page reports what is supported by public source and documented vehicle observations. It does **not** certify the integrated source as installed or approved for driving. Update alongside source, release and acceptance changes; retain the original dates of evidence reports.

## Evidence terminology

| Level | What it proves | What it does not prove |
| --- | --- | --- |
| **SOURCE** | Code, bindings, profile and/or integration tooling exist in public source | Successful compilation or installation |
| **BUILD / HOST** | Native/Java build or isolated tests passed for an identified revision | Real-unit functionality or safe recovery |
| **PACKAGE** | One fully staged ZIP passed its actual package/manifest checks | Installation or vehicle acceptance |
| **UNIT / VEHICLE** | Observed behavior on a named firmware/cluster and exact tested build | Universal support or a later source branch's behavior |
| **RELEASE** | A separately identified downloadable package with stated support scope | Features added to source after that package |

The same feature can have **UNIT evidence for an older candidate** and only **SOURCE evidence for the newest integration**. These are not contradictory.

## Target-level status

| Exact profile | Source/integration | Vehicle evidence | Remaining acceptance |
| --- | --- | --- | --- |
| [Škoda MU1440 P4526](../../modules/profiles/skoda-mu1440-p4526/) | Shared modules, broker, Java adapter, profile, installer tooling | Earlier AID10-class reference runs showed live auxiliary maps, native menu candidates and video handback | New unified MIBR installer and J9 artifacts, menu APPLY/ACTIVE and recovery on actual unit |
| [SEAT MU1409 P4708](../../modules/profiles/seat-mu1409-p4708/) | Exact JXE fingerprint, source Java adapter and shared multi-profile assembly paths | Independent project-specific vehicle approval **not recorded**; community reports are third-party evidence | Exact J9 build and OEM widget/skin rendering, focus/back, arrows, input, video and rollback |
| [SEAT MU1447 P4709](../../modules/profiles/seat-mu1447-p4709/) | Exact JXE fingerprint, own adapter lineage, `image_index_offset=6` in profile configuration | No complete project-specific vehicle acceptance | J9/menu build, firmware-specific offsets and complete end-to-end vehicle verification |

All three profile selectors are enabled in [profile data](../../modules/profiles/) for the planned beta. **Selector enabled ≠ tested, installed or released.** `P4708_1` is an unknown separate fingerprint unless measured and explicitly added. [Full compatibility matrix](../testing/COMPATIBILITY_MATRIX.md).

## Feature-level status

| Feature | Implemented or demonstrated | Critical limit |
| --- | --- | --- |
| Auxiliary CarPlay maps (Apple Maps, Google Maps, Waze) | Exact Škoda reference vehicle demonstrated moving video via Stream 111 and MOST | Other firmware/cluster combinations and current integrated builds remain unqualified |
| Main + cockpit/secondary projection | Media and control components have source, host and historical vehicle evidence | Reconnect/ownership/failover must be verified on the actual final build |
| OEM HOME and Settings | Common Java menu, native broker, firm-ware adapters and menu editor are present | Java 1.2/J9 rebuild with exact external API inputs and OEM visual/ACTIVE effects remain separate acceptance gates |
| ViewArea, SafeArea, screen zoom and presentation | Configurable source and some development vehicle observations | Persisted configuration is **not** proof of displayed geometry or zoom on every app |
| Navigation overlay/composition (ETA, speed limit, compass, maneuver layout) | Stream URL and registry settings, menu and navigation configuration exist | UI display and phone-side acceptance are dependent on exact session and app |
| **Turn-by-turn arrows / phone route guidance** | Broker switches for `carplay_nav`, source/line/night/display and navigation/RGI sources exist | `carplay_nav=off` is compiled fallback; selecting a menu option is not proof that real phone arrows reached the VC |
| Original navigation and STOCK handback | Guarded exclusive writer and historical reference-vehicle handback | New installer/recovery and all input transitions need current-run proof |
| Vehicle telemetry (speed/status) | Source hooks and bounded integration experiments exist | Valid provider data, phone subscription and visible acceptance remain open |
| Native wireless, further brands, other cockpit dimensions | Research and candidate paths exist | Not a general supported/installed feature |

**Three distinct navigation concepts:** (1) CarPlay map *video* rendered inside type 111, (2) ETA/compass/maneuver *composition* requested inside that UI, and (3) phone/native route-*arrow data* and corresponding broker/RGI integration. Do not mark all three vehicle-tested because one moving map was shown.

## Package distinction

The [frozen MU1440 developer ZIP](../../release/CURRENT.md) covers a limited older seven-payload reference. The newer [three-profile builder and installer](../packages/README.md) are published as source; a completed final ZIP with all external J9 inputs and a qualified vehicle test is a separate milestone. See [public source coverage](PUBLISHED_SOURCE_COVERAGE.md).

## Evidence and maintenance

Source of truth for profile identity is `modules/profiles/*/profile.json`, not this prose. Source/settings behavior belongs to [registry](../../settings/registry.json) and [package contract](../build/PACKAGE_LAYOUT.md). Vehicle claims must cite a dated test result: [moving maps](../media/mu1440-stream111-poc-2026-09-29/README.md), [October evidence](../findings/OCTOBER_2026_VEHICLE_AND_TIMING_EVIDENCE.md), [October HMI status](INTEGRATION_STATUS_2026-10-21.md). Mark new evidence with the tested SHA, target and timestamp before upgrading any classification.
