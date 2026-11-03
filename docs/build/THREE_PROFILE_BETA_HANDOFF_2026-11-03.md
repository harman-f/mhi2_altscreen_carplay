# Three-profile beta: agreed design, implementation gates and handoff (2026-11-03)

> **Status: architecture/implementation handoff, not a completed release.** The decisions below were agreed in the product discussion. This document records what needs implementing; it neither changes running vehicle software nor claims that the complete beta pipeline, unified defaults, storage migration, binary versioning or installer ZIP already exists.
>
> **Development policy:** implement and validate on `harman-f/mhi2_altscreen_carplay` `develop` through reviewed PRs; promote to `main` only after the applicable checks. Keep research/test evidence in the research repository as appropriate, but the implementation and its operational documentation live here. Do not update or delete historical public releases/tags as a side effect.

## 1. Decision register and current status

| Topic | Agreed target | Verified repository state at handoff |
| --- | --- | --- |
| Build and publication | **One parameterized build orchestration and one release pipeline**, optional firmware build matrix; one combined beta ZIP | Shared module index, a three-profile *plan* and partial source/QNX build CI exist. The assembled three-profile ZIP and end-to-end release gate do **not** yet exist. |
| Firmware selection | Exactly `skoda-mu1440-p4526`, `seat-mu1409-p4708`, `seat-mu1447-p4709`; exact original `lsd.jxe` SHA-256 selects one; unknown/ambiguous fails closed | All three profiles are indexed; target-specific Java/HMI, icons and acceptance remain incomplete. Do not infer compatibility from name or partial hash. |
| Package contents | All project-owned source, needed tools, common runtime, all three profiles, installer, manifests, README and configuration matrix **in the same ZIP** | Layout is specified in [PACKAGE_LAYOUT](PACKAGE_LAYOUT.md), not yet fully assembled. OEM/J9/OS-derived material must not be silently shipped; state external inputs and reproducibility gaps. |
| Default configuration | One release-level **effective defaults contract** with shared values and explicit per-firmware overrides | 48 CarPlay keys in [registry](../../settings/registry.json), 13 broker durable switches in source, menu layout separate. Inventory and installer documentation are in [PR #108](https://github.com/harman-f/mhi2_altscreen_carplay/pull/108), **open at handoff**. Central generator and ZIP enforcement remain open. |
| Menu | External, editable menu layout with brand-appropriate output; layout/visibility must not imply feature activation | Checked-in [standard menu](../../tools/menu-editor/standard-menu.txt) has `brand=skoda`. SEAT rendering/build/vehicle proof remains profile-specific. |
| Versioning | One product release version and Git commit; independent hashes/identity for every compiled component; on-unit installed receipt and read-only menu page match package identity | Module build-lineage tool covers selected MU1440 outputs. Java [MibrVersionInfo](../../modules/menu/source/java/de/mibr/hmi/MibrVersionInfo.java) reads metadata and component rows but does not prove running binaries' full hashes. [PR #74](https://github.com/harman-f/mhi2_altscreen_carplay/pull/74) remains open/draft; integration incomplete. |
| Storage and names | Consolidate persistent project-owned paths under `/mnt/app/root/altscreen-u2/`, keep volatile data under `/tmp`; coherent naming and explicit file semantics | Current sources use multiple independent persistent roots. Migration design is [PR #109](https://github.com/harman-f/mhi2_altscreen_carplay/pull/109), **open at handoff**, not applied. |
| Operating environment | Installer starts via existing SSH on **MMX**, follows QNX command/mount constraints; RCC only via an explicitly qualified cross-context operation such as `on -f rcc` | MMX/QNX shell auditing is present for known scripts; static checks cannot prove target execution. Future integration into the M.I.B. Bash host needs a separate adapter/contract. |
| Acceptance and publication | Validate staged package and **re-open the final ZIP**, exact profiles/hashes/source receipts, then controlled parked-vehicle testing; publish immutable versioned prereleases only when gates pass | Legacy MU1440 ZIP is CI-internal; three-profile release upload remains disabled. [PR #83](https://github.com/harman-f/mhi2_altscreen_carplay/pull/83) proposes immutable history. |

The **48 CarPlay settings are not 48 files**: they occupy **13 registry file groups**, including ViewArea (22 fields), keyframes (6), navigation (6) and display (5). The **13 broker-owned durable switches** are a different category. Do not collapse their distinct storage protocols into one assumed format.

## 2. One build, one release, three target profiles

Maintain one source/module ownership graph ([module-index](../../modules/module-index.json)). Run the same build logic per target profile only where generated binaries or target ABI/classpath differ:

1. Validate source closure, module dependencies, generated catalog consistency and applicable host tests.
2. Compile shared C/runtime/utility components **once when exact CPU/ABI/toolchain constraints permit**; record source revision, compiler/toolchain, command, platform and SHA-256 per output. Rebuild per target where ABI differs; do not assert binary equivalence merely because source is shared.
3. Compile and verify per-firmware Java/J9/HMI adapters against authorized local exact OEM inputs. Missing required inputs are a build blocker, never a reason to invent stubs or include redistributed OEM files.
4. Assemble **one** package with `common/{carplay,broker,menu,navigation}/`, three symmetric `profiles/` entries, `installer/`, `tools/`, `source/`, documentation, `package.json`, source manifest and package SHA-256.
5. The source manifest covers **all distributable project-authored sources used for this release** and states uncovered/generated or externally supplied build dependencies. Packaging cannot claim full rebuildability if exact compiler/OEM inputs are excluded.
6. Preflight the **actual staged** QNX shell scripts, then validate the **actual final ZIP**. The R3 validator self-test alone is insufficient; compare SHA-256 and manifest contents after re-opening the archive. Only then consider release publication.

Release labels must distinguish `SOURCE_ONLY`, `BUILT_UNQUALIFIED`, `INSTALLER_STAGED`, `HOST_PACKAGE_VALIDATED` and `VEHICLE_QUALIFIED` (names illustrative). No source-only/host-only pass may automatically become a claim of safe installability.

## 3. Defaults, menu and documentation: one effective contract

**Keep the canonical owner of each setting.** Avoid maintaining competing manual copies of defaults:

- **CarPlay:** [`settings/registry.json`](../../settings/registry.json) is the canonical 48-key source, with `temp > persistent > profile > compiled` priority, three distinct *CarPlay presets* and each key's apply boundary. CarPlay preset is **not** one of the three firmware profiles.
- **Broker:** 13 persistent single-writer switches are in [`mibr_durable_switch.c`](../../modules/broker/source/mibr-control/mibr_durable_switch.c). Keep revision/CAS/readback semantics. Exact platform overrides are read from `mibr-platform-defaults.conf`. Consolidating the defaults interface may require a generator or schema that represents these separately; do not silently change their native file grammar.
- **Menu:** [`standard-menu.txt`](../../tools/menu-editor/standard-menu.txt) and [function catalog](../../tools/menu-editor/function-catalog.json) control navigation, labels, visibility and operations—not the effective setting values. Generate appropriate Škoda/SEAT menu outputs, respecting genuine OEM widget differences.
- **Release-level defaults manifest:** new generator/validation glue must reference both owners and capture the selected CarPlay preset, each firmware override, value provenance, whether configurable, initial intent, apply boundary (`live`, `session`, `presentation`, `reconnect`, `unit_reboot`) and migration behavior. A desired default is not the same as a saved value or an **ACTIVE** visual result.
- **Document every option:** the full matrix, including non-setting menu actions, resides in [PR #108](https://github.com/harman-f/mhi2_altscreen_carplay/pull/108), planned at `docs/configuration/DEFAULT_CONFIGURATION_MATRIX.md`. The ZIP's `INSTALLATION-README.md` explains *selected package defaults*, overrides, installation/rollback, supported targets and known gaps. Generate/copy it from the actual build inputs and fail the release if it disagrees with them. Keep the repository README/doc index linked.

**Known source examples (not a new beta default decision):** `carplay.enabled=1` in all three CarPlay presets; `mibr_dual_view` advertises `maxFPS=40`; broker phone-route arrow switch `carplay_nav=off` while arrow source `auto`, placement `side`, side streets and lane guidance `on`. The team still must decide whether beta phone-route arrows remain opt-in. Existing MU1440 developer install sets `map-rich`, prepares persistent Auto-Direct and **enables persistent D2** with 1,000 ms watchdog and 1,000 ms minimum gap. These are **not** independently qualified SEAT defaults.

## 4. On-unit persistent storage, names and format ownership

### As-is (exact paths are compatibility contracts)

| Lifetime / purpose | Currently present code paths |
| --- | --- |
| Volatile per-session overrides, IPC, status and locks | `/tmp/mibr-*`; QNX MMX `/tmp` maps to shmem with special write/rename/fsync behavior |
| CarPlay registry and historical presence switches | `/mnt/app/root/mibr-carplay111-*`, `/mnt/app/root/mibr-carplay-autodirect.enabled`, `/mnt/app/root/mibr-alt111-keyframe-policy.enabled` |
| Menu, platform defaults, scaling, broker navigation switches | `/mnt/app/root/altscreen-u2/config/` |
| Persisted view state | `/mnt/app/root/mibr-view/` |
| Installed-version view | `/mnt/app/root/mibr-kit/` |
| Installed scripts and executables | `/mnt/app/root/altscreen-u2/{bin,scripts}` |

### Agreed target (not yet created by installer)

```text
/mnt/app/root/altscreen-u2/
  bin/
  scripts/
  config/
    carplay/       shared registry groups / video and AirPlay preferences
    navigation/    nav composition and phone-source arrows
    cockpit/       view/safe-area/scaling configuration
    menu/          menu layout and language
    vehicle/       optional vehicle telemetry mode
    platform/      firmware/brand defaults (not mutable user preference)
    features/      explicit enabled/disabled intent
  state/
    cockpit/       persisted operational view state
  version/         installed product, build and component receipts
  backup/          versioned, hashed pre-migration/rollback originals
  logs/            intentionally bounded persistent diagnostic logs
/tmp/mibr-*         leave existing volatile IPC/override names stable initially
```

Names convey the data contract: lowercase kebab-case for new filenames, `.conf` for settings, `.state` for persisted state, `.status` for diagnostic output, `.lock` for transient coordination, `.manifest` for inventories and `.properties` for existing Java-compatible installed identity. The **file content schema and owner matter more than a pretty extension**.

**Group related parameters**, e.g. coherent ViewArea geometry, keyframe policy or display metadata; allow isolated switch files when their independent lifecycle or single-writer CAS requires it. Normalize bare file-presence toggles such as `*.enabled` / `*.disabled` toward positive, explicit values (`enabled=1|0` or semantically specific keys) **only when all boot-time readers and uninstall/rollback consumers are updated together**. Never create two authoritative copies or change existing broker magic/revision formats merely for aesthetic uniformity.

The detailed design and representative mapping are in [PR #109](https://github.com/harman-f/mhi2_altscreen_carplay/pull/109), planned at `docs/architecture/UNIT_STORAGE_AND_NAMING_CONTRACT.md`. This design is **not** proof that every hardcoded file path has already been discovered.

## 5. Safe migration/update/uninstall behavior

Migration is a **dedicated prerelease engineering gate**, not part of a trivial move or search-and-replace.

1. Generate a machine-readable, reviewed **complete path inventory** for C, Java, QNX shell, compiled/generated catalogs, boot integration, installer, key daemon, GEN2, broker and diagnostic/restore paths. For each record: original path, target path, reader(s), **single writer**, type/format/version, state lifetime, precedence, default, migration step, exact rollback.
2. Detect existing user settings, older project installations and foreign/OEM modifications. Fail on ambiguity; never overwrite a user setting with a new release default or delete an unknown file.
3. Check the **exact firmware fingerprint** and MMX/RCC/ABI conditions, ensure required components are present, and archive/hashes of original bytes and metadata on a safe recovery medium before any mutation. Preserve original installation and OEM state.
4. Use the qualified serialized RW lease for `/mnt/app`, format-aware stage/commit/readback and verified RO restoration. On QNX volatile `/tmp`, preserve shmem-compatible lock/journal semantics; do not assume Linux atomic rename behavior.
5. Cut all readers, writers, startup hooks and diagnostic/uninstall paths over at the *same qualified release boundary*. No symlink or dual-active writable store as an unreviewed shortcut.
6. Reboot and verify correct effective values, selected defaults, absence of stale paths, actual CarPlay and cockpit behavior, and idempotent install/upgrade/uninstall. Simulate interrupted migrations/power-loss via host fixtures and then perform qualified on-target tests.
7. Separate **uninstall** (restore exact modified OEM/startup files, remove only project-owned runtime) from **reset to defaults** (erase user configuration only on explicit request). Decide the retention policy explicitly before installer implementation.

**MMX_SSH** is the current installer execution context. QNX `on -f rcc` is a separate, explicit boundary, not a reason to run all installer logic on RCC. Stock shell utilities must be checked against the real command inventory; the existing [QNX compatibility guide](../testing/MU1440_QNX_SHELL_COMPATIBILITY.md) and `tools/release/qnx_scripts.py` provide a static gate, **not** full real-unit proof.

## 6. Version identity end-to-end

One immutable product version for the combined beta, e.g. `1.x.y-beta.N` (illustrative), plus Git commit, build recipe/toolchain and SHA-256. Each target-specific Java JAR and native executable has a **component build identity** and exact file hash; shared identical binaries are hashed once and referenced by multiple profiles. Nonbinary config/tool/source file identities are part of the package/source manifests.

A future installer writes atomically verifiable installed identity under the **new** `version/` namespace only after successful file staging/verification, with rollback and a partial-install state. The existing Java Version page must read the **actual installed receipt**, show product version, target/brand, relevant configuration versions and each component's state, and distinguish receipt presence from full binary hash/actual running process verification. It must never claim that file-size equality proves a cryptographic match. Existing `MibrVersionInfo` is a useful reader foundation; binary embedding and a full package install receipt are **not** yet end-to-end integrated.

Update [PR #74](https://github.com/harman-f/mhi2_altscreen_carplay/pull/74) for compatibility with current `develop` before integrating its unfinished version generator/installer changes; avoid parallel competing version schemas. The release history/immutable tag contract is also tracked in [PR #83](https://github.com/harman-f/mhi2_altscreen_carplay/pull/83).

## 7. Implement in this order, and stop at meaningful gates

| Step | Deliverable | Exit criterion |
| --- | --- | --- |
| A | Merge/reconcile the current documentation PRs **#108 (defaults)** and **#109 (storage/names)**, and this consolidated handoff | No contradictory source-vs-doc claims; conflict-resolved reviewed `develop` |
| B | Full path + settings/owner/format inventory, shared release-default/override schema, firmware menu source selection | All referenced paths and 48+13 settings accounted for; no collisions or duplicate writers; feature defaults explicitly reviewed |
| C | Coordinated root/naming migration and version manifest/receipt integration | All affected C/Java/shell/boot references updated and host-tested; rollback and powerloss checks; old path compatibility deliberate |
| D | Parameterized builds and profile-specific HMI/J9 outputs; full module source/build receipts | Per-profile binaries valid for the exact input firmware/ABI; no invented OEM inputs; hashes and source provenance complete or explicitly blocked |
| E | Full installer + complete beta ZIP including source, tools, defaults matrix, README and component receipts | Actual archive passes all layout, SHA-256, firmware-selector, QNX-static and document-consistency gates; no partial substitute |
| F | Parked reference/SEAT vehicle tests, exact postboot profile/config readback, cross-profile recovery and upgrade/uninstall | Evidence per profile and complete combined beta acceptance; explicit remaining reconnect/operational defects, no unsafe use claim |
| G | Immutable, clearly labeled beta publication and docs/main promotion | Only after A–F; no rewrite/deletion of old releases and no silent change of pinned vehicle-tested binaries |

Parallel development is fine, but the **release gate** is serial and fail-closed. Preserve a working stock recovery route. The multi-profile beta has equal inclusion of the three declared profiles; missing target build inputs postpone the combined release rather than silently dropping a target.

## 8. References and handoff status

- [Modular package contract](PACKAGE_LAYOUT.md) · [Module source-build lineage](MODULE_BUILD_LINEAGE.md) · [Release readiness and QNX-script audit](../../tools/release/README.md).
- [Defaults, complete matrix and installer README: PR #108](https://github.com/harman-f/mhi2_altscreen_carplay/pull/108) — open at time of audit, not yet in `develop`.
- [MMX storage/naming and migration proposal: PR #109](https://github.com/harman-f/mhi2_altscreen_carplay/pull/109) — open at time of audit, not yet in `develop`.
- [Version schema/menu integration: PR #74](https://github.com/harman-f/mhi2_altscreen_carplay/pull/74) — draft/open; current `main` already contains some read-only menu reader source, but **not** full version propagation.
- [Immutable build/release-history work: PR #83](https://github.com/harman-f/mhi2_altscreen_carplay/pull/83).
- [Source-only migration work: PR #73](https://github.com/harman-f/mhi2_altscreen_carplay/pull/73); verify against current canonical `develop` before taking any old PR description as implementation truth.

**At handoff:** no released three-firmware installer, no source-to-installed-receipt closure for all components, no storage path migration, and no on-vehicle testing from this documentation work. The working branch/PR containing this record is documentation-only; it should be reviewed and merged into `develop` with explicit follow-up engineering tasks rather than described as a finished beta.
