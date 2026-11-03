# Development repository layout and release lineage contract

Status: adopted 2026-11-02; active native/HMI module source and primary runtime consolidation reviewed as a staged migration through 2026-11-03. This describes physical source ownership, **not** a complete multi-profile package or vehicle qualification. Read with [module boundaries and portability](MODULE_BOUNDARIES_AND_PORTABILITY.md), [the R3-derived distribution contract](../build/PACKAGE_LAYOUT.md), and [published source coverage](../status/PUBLISHED_SOURCE_COVERAGE.md).

## Scope and distinct layers

1. **Development repository:** one canonical owner per component; co-locate its source, runtime inputs, tests, and build recipe in a functional module. Prefer human-navigable ownership to global source/runtime/test buckets. Move existing paths only with their known callers, scripts, documentation and CI updated and tested.
2. **Build outputs:** record the exact source revision, target/toolchain, build options, inputs, output names and SHA-256. Do not mistake a prebuilt/verified binary for a reproducible source build. Known-source gaps remain explicitly labeled.
3. **Distribution:** generate the separately specified multi-target ZIP (`common/`, `profiles/`, `installer/`, `source/`, `tools/`, `docs/` and manifests) from canonical inputs. The ZIP's `source/` inventory is a publication snapshot, **not** a second owning source tree in the development repository. Unit installation paths and fail-closed profile selection must not change merely because repository paths do.

## Target layout (incremental, not yet fully implemented)

```text
modules/
  carplay/       source/ runtime/ tests/ build/
  broker/        source/ runtime/ tests/ build/
  menu/          source/ runtime/ tests/ build/
  navigation/    source/ runtime/ tests/ build/
  profiles/      skoda-mu1440-p4526/
                 seat-mu1409-p4708/
                 seat-mu1447-p4709/
tools/           menu-editor/ and host build/package/validation tooling
docs/            architecture, source/build, testing and release guidance
deployment/      installation, rollback and target interfaces, as applicable
```

Each logical module owns only its independently developed source, relevant runtime input and validation. Shared code lives once; target-specific Java/HMI adapters, display geometry, input/KEY mapping, OEM integration and compiled target artifacts belong to the applicable profile or a clearly declared target adapter. A JSON profile value is **not** executable configuration if the binary does not consume it. Do not redistribute unlicensed OEM inputs or extracted firmware. Central integration tests, cross-module CI and host tools may remain shared where that is the better ownership boundary. Existing `src/`, `runtime/`, `tests/` or build paths are transitional until their dependency-complete migrations are verified.

## Current module ownership and remaining exceptions (source migration checkpoint)

- `modules/carplay/source/` and `modules/carplay/runtime/`: canonical GEN2/Stream111, direct TS/parity, exclusive writer/gate, shared scaling, vehicle-data and CarPlay runtime inputs. The scaling library is intentionally shared through the existing one-way Broker → CarPlay build dependency; there is no extra broker instance or second media owner.
- `modules/broker/source/` and `modules/broker/runtime/`: canonical MIBR/3 controller, KEY helper and broker runtime.
- `modules/menu/source/`: canonical owned Java/HMI and tests, menu metadata and generator.
- `modules/navigation/{source,runtime}/`: canonical RGI source and navigation runtime.
- `modules/profiles/` currently contains **candidate IDs and portability evidence**, NOT approved fully implemented SEAT/Skoda installation profiles. Exact LSD/JAR fingerprints, actual runtime consumers and vehicle acceptance remain separate work.
- The shared schema/registry (`settings/`), cross-module build/test orchestration (`tools/`, `tests/`), generic diagnostics and deployment interfaces (`runtime/diagnostics/`, `runtime/deployment/`, `deployment/`), and deliberately isolated historical source-only models (`src/experimental/`) are **intentional distinct ownership boundaries**, not second canonical active module trees. Document any future move with its actual consumers and output staging contract.

Installed unit and SD package paths are **not** renamed by these source moves. Project-owned QNX binaries are still built/verified against exact toolchains and target firmware separately; the R3 multi-profile release packager is not implemented merely because the source tree is organized.

## Build/release interface to be implemented

For every buildable module, document or provide machine-readable equivalents for:

- Canonical source and runtime input paths; module owner and required module dependencies.
- Host toolchain/target/ABI, reproducible build invocation, expected outputs and checks.
- Output ownership: shared `common/<module>/bin` or justified `profiles/<target>/...` output in the R3 ZIP, plus supported target IDs.
- Build-input/source commit identity, binary hashes, provenance/license, verification level and explicit missing source coverage.

An automated release pipeline should derive the affected build graph from changes **and declared dependencies**, rebuild and test affected components, compare output hashes, stage only appropriate profile outputs, and emit runtime and independent source manifests. It must validate each final ZIP (including exact hash/profile selection). A green host CI build is not proof of vehicle compatibility; actual unit/vehicle qualification remains a separate gate. A full ZIP can be assembled without requiring a full reinstall for a changed-file deployment.

## Git integration and publication

- `main` is the reviewed public source/release baseline; `develop` is the intended integration branch **for already publication-cleared code only**, not a public experimental dumping ground.
- Public `develop` is now the **canonical integration home for new independently publishable product work**, normally via short-lived PR branches based on it. The previously required bootstrap reconciliation has been completed. A distinct private Research code owner and automatic branch-by-branch promotion are no longer the normal development model.
- Focused publication-ready changes enter `develop` through reviewable PRs with source/provenance gates and relevant CI; then `develop` promotes to `main` by approved fast-forward or ruleset-compliant review. Do not redo unchanged binary builds just because a source path moved; automatically required CI is separate from any extra manual builds.
- Keep private research, internal coordination, proprietary/reference materials, experiments, raw captures and source-incomplete claims out of both **public** branches. A cross-repository integration is a curated path-by-path change, **not** an unconditional branch merge or directory copy.

## Migration gates

For each physical move: inventory inbound/outbound references, perform a single canonical move, update build/CI/tests/docs/install/package callers, run affected tests and package-integrity checks, compare produced runtime bytes when equivalence is intended, and record unresolved outputs. Isolate unrelated behavior fixes in separate changes. Do not remove compatibility paths until consumers have migrated and been verified. The existing R3 POC package is a historical structural reference, not a fresh release acceptance.
