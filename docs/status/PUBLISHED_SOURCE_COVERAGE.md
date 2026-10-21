# Published source and current development coverage

**As of 22 October 2026.** A published design/feature summary does not imply that its newest privately developed implementation has been exported. The public project carries real, reviewable project-authored code, along with pinned reference developer binaries. It is not yet a complete standalone source release of every current reference-unit component.

| Subsystem | Public implementation/source | Scope |
| --- | --- | --- |
| CarPlay auxiliary/GEN2 receiver | [GEN2 native C](../../src/native/altscreen111-gen2/) and [development notes](../../src/native/altscreen111-gen2/DEVELOPMENT.md) | Public experimental/reference implementation; newer session/soft-recovery development has separate validation |
| Direct video transport | [Direct-TS remux C](../../src/native/direct-ts-remux/) and [MOST writer C](../../src/native/most-ts-writer/) | Project-owned reference source for H.264 to TS / output boundary |
| Exclusive stock/direct write gate | [Gate C](../../src/native/isotx2-gate/) and [runtime integration](../../runtime/isotx2-gate/) | Public exact-platform source; preserve original owner and fallback |
| Deployment/restore/status | [Reference developer scripts](../../deployment/mu1440/) and [Auto-Direct runtime](../../runtime/auto-direct/) | Exact-platform scripts, NOT an installer for any MHI2 |
| Navigation options / SafeArea tools | [Runtime helpers](../../runtime/navigation/) | Developer control/reference; live active effect depends on current sender/session |
| Input diagnostics | [Native keypanel observer](../../src/native/keypanel/) and [diagnostics](../../runtime/diagnostics/) | Diagnostics, NOT the latest integrated finished HMI/KEY40 input controller |
| Reference developer ZIP / third-party pieces | [Pinned release description](../../release/CURRENT.md), [third-party notices](../../THIRD_PARTY_NOTICES.md) | The older vehicle-tested reference package and license/provenance notes; independent of newer development |
| MIBR/3 public protocol/mailbox slice | [Source and host tests](../../src/experimental/mibr3/README.md) | Independently published, compilable source-only reference; not a production vehicle controller |
| Java HMI protocol/menu-model source | [OEM-independent Java sources and host smoke test](../../src/experimental/hmi-model/README.md) | Published Java 1.2-style protocol and menu projection only; no full OEM widget/J9 install integration |
| Newer source-time parity writer and supervisor | Not yet delivered here as one coherent current-main source/release | Evaluated in development, no silently imported old draft |
| OEM-native HOME/Settings Java/J9 and MIBR/3 central controller | [Architecture/behavior](../architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md), not the full latest integrated public source | Menu and owner API development exists; full tested source package and physical ACTIVE qualification outstanding |
| Integrated Zoom and physical KEY40 stock/direct route control | [Architecture](../architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md); public input diagnostics only | Developer/reference-vehicle milestones are not the same as the packaged/public full feature |
| Vehicle speed, ambient temperature and optional status | [Feature overview](../architecture/OPTIONAL_VEHICLE_DATA_FEATURE_OVERVIEW.md) | Experimental design/adapter candidates; neither the final qualified sender nor complete phone acceptance published |
| Native wireless | [Research index / experimental prototype](../research/mhi2-native-wireless-2026-10/README.md) | Separately experimental; not part of wired video success or public release |

**Next source publication milestone:** review original ownership/license and target ABI, assemble a coherent project-owned GEN2 → source-frame transport → direct/parity writer → stock/route owner → HMI/Java → controller source set with build scripts/tests, and publish source-only or a pin-hashed developer artifact with accurate evidence labels. Do not merge unrelated historical stacked branches or copy original Apple/OEM implementation bytes. Native source availability and a successful physical install/complete feature acceptance are separately tracked outcomes.

[Current integrated status](../status/INTEGRATION_STATUS_2026-10-21.md) · [Architecture](../architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md) · [Release](../../release/CURRENT.md)
