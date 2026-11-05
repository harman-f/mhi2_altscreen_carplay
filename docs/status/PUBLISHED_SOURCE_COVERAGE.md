# Published source coverage

**Current source inventory checked 5 November 2026.** The earlier 23 October MU1440 R57 source baseline is preserved in the [R57 build/status guide](../build/MU1440_R57_SOURCE.md). Since then, the modular **MIB Runtime** source (three firmware profiles, common Java plus OEM adapter sources, settings registry v3, installer/root migration and three-profile assembler) has been integrated into public `main`. Source or CI availability is not an end-to-end J9 build, final installer ZIP or vehicle acceptance. [Current feature and target matrix](FEATURE_STATUS.md) · [Packages](../packages/README.md).

| Subsystem | Public implementation | Evidence / remaining limit |
| --- | --- | --- |
| Type-111 / GEN2 | [Native source](../../modules/carplay/source/altscreen111-gen2/) and [build](../build/INSTALLED_GEN2_SOURCE.md) | R38 overlay; installed GEN2 SHA-256 reproduced |
| Shared settings | [Core/CLI](../../modules/carplay/source/alt111-settings/) and [canonical registry](../../settings/registry.json) | One 48-key registry, installed three-view bounds; installed CLI reproduced |
| Source-time media | [Direct-TS parity](../../modules/carplay/source/direct-ts-parity/) | Installed binary reproduced; host TS/clock/recovery/EOF and predictive decode regressions |
| Owner / native arbitration | [R52 owner reference](../../modules/carplay/source/parity-session/), [native guard](../../modules/carplay/source/altscreen111-gen2/src/alt111_native_gate.c), [legacy gate](../../modules/carplay/source/isotx2-gate/) | Original installed outputs reproduced; canonical owner includes a host-tested failed-grace safety correction not yet vehicle-qualified |
| Supervisor / diagnostics | [Parity runtime](../../modules/carplay/runtime/parity/) | R49 behavior, same-stream retry/backoff, status/statistics layers, one native owner; curated public comments |
| Native MIBR/3 | [Controller and support source](../../modules/broker/source/mibr-control/) | R57 service and KEY40/KEY44/view helper source; unchanged client/genkey; see current build evidence; STORE/TEMP/APPLY/ACTIVE remain distinct |
| OEM-native HOME/settings | [Real R57 Java adapter](../../modules/menu/source/) | Own adapter/catalog/build/tests published; exact J9 rebuild requires external SDK and OEM API inputs |
| UI assets | [Four owned scroll images](../../modules/menu/source/assets/scroll/README.md) | Hash-checked first-party artwork; eight OEM tile images excluded |
| Optional speed / status | [Vehicle-data source](../../modules/carplay/source/vehicle-data/) | Installed GEN2 includes these adapters; experimental sender/phone acceptance remains open |
| Other public modules | [Legacy remux](../../modules/carplay/source/direct-ts-remux/), [keypanel](../../modules/broker/source/keypanel/), [HMI protocol/model smoke test](../../modules/menu/source/tests/PublicProtocolSmokeTest.java), [MIBR/3 contract model](../../tests/mibr-control/api_v3_contract.py) | Retained reference/tooling; models are not competing runtime services |
| SEAT/CUPRA | [Exact profiles](../../modules/profiles/), [adapter source](../../modules/profiles/seat-mu1409-p4708/hmi/) and [testing matrix](../testing/MULTI_PROFILE_TESTING.md) | MU1409/MU1447 firmware hashes and profile adapters in source; no qualified J9/menu-in-car result or final beta ZIP |

| Shared configuration and storage | [Registry v3](../../settings/registry.json), [MIB Runtime root contract](../architecture/FIRMWARE_PROFILES_AND_CONFIGURATION.md) | Shared settings/13 switches and migration paths implemented in source; unit cutover and writer M2 gates still open |
| Modular package and installer | [Installer](../../installer/), [assembler](../../tools/release/build_modular.py), [package rules](../build/PACKAGE_LAYOUT.md) | Host and native CI evidence; complete validated three-J9-profile ZIP and vehicle installation not claimed |

This is **partial vehicle-matched source publication**, not every installed byte. Exact DirectVCPolicy lineage (the P1 boot probe source is published, byte-exact J9 rebuild open), several legacy shell variants, legacy remux build identity, original OEM startup/config/artwork, and the R57 J9 rebuild have individual blockers or redistribution exclusions. The native source builds without private-repository access; the target Java build legitimately requires externally supplied OEM/SDK inputs. See the build guide for the precise exclusions and hashes.

The switchable lockout requirement remains semantically unresolved; this publication does not silently equate it with pause or claim a complete configuration surface. The R57 view helper's preferences remain outside the canonical layered registry, a documented settings-model gap. Physical input, independent ACTIVE/visible route confirmation, source reconnect/recovery, optional phone vehicle-data acceptance and combined vehicle qualification remain separate gates. No new control, default or core-boundary design is introduced by publishing these source snapshots.

The downloadable [reference release](../../release/CURRENT.md) retains its own older scope. CI build artifacts are temporary source-build evidence, not a vehicle-qualified release package.
