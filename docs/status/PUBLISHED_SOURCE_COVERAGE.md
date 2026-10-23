# Published source coverage

**23 October 2026 — source-only MU1440 R50 baseline, with documented exclusions.** The repository now contains the real OEM-menu adapter, central controller and source-time parity implementation. The [complete build/status guide](../build/MU1440_R50_SOURCE.md) distinguishes source, host checks, QNX/J9 builds, exact artifact reproduction and physical vehicle acceptance.

| Subsystem | Public implementation | Evidence / remaining limit |
| --- | --- | --- |
| Type-111 / GEN2 | [Native source](../../src/native/altscreen111-gen2/) and [build](../build/INSTALLED_GEN2_SOURCE.md) | R38 overlay; installed GEN2 SHA-256 reproduced |
| Shared settings | [Core/CLI](../../src/native/alt111-settings/) and [canonical registry](../../settings/registry.json) | One 48-key registry, installed three-view bounds; installed CLI reproduced |
| Source-time media | [Direct-TS parity](../../src/native/direct-ts-parity/) | Installed binary reproduced; host TS/clock/recovery/EOF and predictive decode regressions |
| Owner / native arbitration | [R50 owner](../../src/native/parity-session/), [native guard](../../src/native/altscreen111-gen2/src/alt111_native_gate.c), [legacy gate](../../src/native/isotx2-gate/) | Original installed outputs reproduced; canonical owner includes a host-tested failed-grace safety correction not yet vehicle-qualified |
| Supervisor / diagnostics | [Parity runtime](../../runtime/parity/) | R49 behavior, same-stream retry/backoff, status/statistics layers, one native owner; curated public comments |
| Native MIBR/3 | [Controller and support source](../../src/native/mibr-control/) | R46 service and installed client/genkey/KEY40 binary hashes reproduced; STORE/TEMP/APPLY/ACTIVE remain distinct |
| OEM-native HOME/settings | [Real R48 Java adapter](../../src/hmi/oem-menu/) | Own adapter/catalog/build/tests published; exact J9 rebuild requires external SDK and OEM API inputs |
| UI assets | [Four owned scroll images](../../src/hmi/oem-menu/assets/scroll/README.md) | Hash-checked first-party artwork; eight OEM tile images excluded |
| Optional speed / status | [Vehicle-data source](../../src/native/vehicle-data/) | Installed GEN2 includes these adapters; experimental sender/phone acceptance remains open |
| Other public modules | [Legacy remux](../../src/native/direct-ts-remux/), [keypanel](../../src/native/keypanel/), [independent HMI model](../../src/experimental/hmi-model/), [MIBR/3 model](../../src/experimental/mibr3/) | Retained reference/tooling; models are not competing runtime services |
| SEAT/CUPRA | [Collaboration](../porting/SEAT_CUPRA_MU1409_COLLABORATION.md) and [local setup](../porting/SEAT_CUPRA_MU1409_LOCAL_ENVIRONMENT.md) | Public source is available as a port starting point; no validated MU1409 installer |

This is **partial vehicle-matched source publication**, not every installed byte. Exact DirectVCPolicy/BootProbe lineage, several legacy shell variants, legacy remux build identity, original OEM startup/config/artwork, and the R48 J9 rebuild have individual blockers or redistribution exclusions. The native source builds without private-repository access; the target Java build legitimately requires externally supplied OEM/SDK inputs. See the build guide for the precise exclusions and hashes.

The switchable lockout requirement remains semantically unresolved; this publication does not silently equate it with pause or claim a complete configuration surface. Physical input, independent ACTIVE/visible route confirmation, source reconnect/recovery, optional phone vehicle-data acceptance and combined vehicle qualification remain separate gates. No new control, default or core-boundary design is introduced by publishing these source snapshots.

The downloadable [reference release](../../release/CURRENT.md) retains its own older scope. CI build artifacts are temporary source-build evidence, not a vehicle-qualified release package.
