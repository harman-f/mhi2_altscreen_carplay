# Release readiness, module ownership and target-shell safety

The canonical source of truth for build ownership is
[`modules/module-index.json`](../../modules/module-index.json). The workflow
[`release-mu1440-aid10.yml`](../../.github/workflows/release-mu1440-aid10.yml)
uses this structure for **pre-publication readiness**, not as a vehicle-ready
multi-profile release generator.

## Mandatory three-profile beta release inputs

`python3 tools/release/plan_multi_profile_beta.py --self-test --json-out beta-profile-plan.json` emits the *same* common beta inclusion for Škoda MU1440 and both SEAT firmware families. Java adapters are per-firmware repairable; code and registry remain shared. This is a real CI input for the future R3 packager, not yet an executable installation ZIP. Final vehicle acceptance is common beta testing, not an exclusion gate. The three original LSD JXE SHA-256 profile selectors are now present in source. Exact compiled ABI-specific Java, target integration and package/vehicle qualification are still required for the final installer; never manufacture substitutes.

## Independent stages

1. **Impact plan (host):** `module_plan.py` compares the exact base/head Git
   paths and resolves reverse dependencies through the canonical index.
   For example, CarPlay can affect Broker, Menu and Navigation; Broker
   can affect Menu and Navigation. Unknown new module paths fail closed.
   Central settings/module-index changes invalidate the entire owner graph.
   Output is `mu1440-release-module-plan`, a JSON CI artifact, not an executable ZIP.
2. **Build and lineage:** the existing GEN2, MU1440 QNX, support-tool and
   module-lineage workflows retain their own QNX compile/receipt gates.
   The owner impact plan does not pretend to recompile, promote or qualify
   their binaries. Module binaries are not automatically substituted for
   pinned vehicle-evidenced binaries in the old installer.
3. **QNX shell compatibility:** `qnx_scripts.py --canonical` discovers
   `*.sh`/`*.ksh` from all indexed module runtime owners and shared
   deployment/diagnostic roots. After staging, the same checker runs against
   **every script in the exact assembled SD root**. This includes the outer
   installer, Auto-Direct, isoTX2, diagnostics and navigation scripts.
   The checker applies the [MU1440 QNX command contract](../../docs/testing/MU1440_QNX_SHELL_COMPATIBILITY.md)
   and `bash -n` for eligible .sh files as an additional host-only syntax
   check; neither operation is a successful QNX/MMX/RCC execution claim.
4. **Legacy archive integrity:** `audit_legacy.py` re-opens the finished ZIP
   and rejects path traversal, symlinks, duplicate members, unlisted content,
   missing scripts, payload drift and mismatched SHA-256 receipts. It checks
   pinned vehicle-media digests and current build-confirmed helper receipts.
   The old SD-root ZIP remains **CI-internal**, not downloadable as a release.
5. **Actual R3 publication boundary:** the R3 validator's self-test is not
   enough. The final assembled archive must contain the
   `MIBR-CarPlay/common/`, `profiles/`, `installer/`, `source/` inventories
   and the unique fail-closed firmware selectors required by
   [PACKAGE_LAYOUT.md](../../docs/build/PACKAGE_LAYOUT.md), and pass
   `python3 tools/validate_modular_package.py <final.zip>`. That archive
   does not yet exist in this public tree: the profile-specific Java/HMI,
   icons and integration inputs are not fully qualified. Publishing is
   intentionally **disabled**; no legacy R3 aliases, placeholder profiles,
   tag rewriting or automatic release deletion.

## Host commands

```bash
python3 tools/release/module_plan.py --self-test
python3 tools/release/module_plan.py --all
python3 tools/release/qnx_scripts.py --self-test --canonical
python3 tools/release/audit_legacy.py --self-test
tools/prepare_mu1440_sd.sh /tmp/mu1440-legacy-audit
python3 tools/release/qnx_scripts.py --package-root /tmp/mu1440-legacy-audit
```

The final archive integrity gate is invoked from CI **after ZIP creation**.
These commands are workstation/GitHub-Runner commands and are **not installed
or executed on the QNX unit**.

## QNX caveats that cannot be waived by green host CI

- Never use external `printf`, `sed`, `tr`, unbundled `sha256sum` or
  `tee`, or GNU-`date` assumptions in on-unit scripts. The known QNX
  shell/environment is not a generic GNU/Linux environment.
- Do not assume command/option behavior validated on MMX applies to RCC.
  Use verified absolute helper paths and documented mount/remount rules.
- `awk` is not banned, but the exact scripted program must have evidence.
  `grep 'A\\|B'` alternation is not portable. Dynamic command evaluation,
  boot-time side effects and device nodes require manual/vehicle review.
- A passing shell syntax check is necessary, not sufficient. A newly
  introduced target command/option is a dependency needing a separate
  vehicle/board-specific inventory and regression fixture.
- Do not start installation or create a release merely because the
  dependency plan and legacy compatibility checks are green.

## Future R3 implementation gate

Implement the real symmetrically inventoried profile tree and complete
source/build receipts. Only then connect a **separate publish job** requiring
successful final ZIP validation, exact source commit and binary SHA-256
provenance, relevant QNX regression and vehicle/profile authorization.
Release tags must be immutable and unrelated historical release assets preserved.

## Source-defined defaults and on-unit storage references (host-only)

Run `python3 tools/release/source_defaults_inventory.py --self-test --json-out source-defaults-inventory.json` on a checkout. The publication audit also uploads a short-retention `source-defaults-unit-path-inventory` JSON artifact.

The generator reads the **canonical** CarPlay registry, broker durable-switch C declarations/header, menu layout/catalog and required firmware-profile index. It validates unique settings/fields, per-preset default values and apply boundaries, broker switch count and source-defined defaults, and menu/catalog references. It records source-file SHA-256, the current 48 CarPlay settings in 13 file groups, 13 broker switches with their separate revision/CAS storage contract, and menu entries that have no directly matching registry key.

A separate lexical scan records literal `/mnt/app/root/mibr*`, `/mnt/app/root/altscreen-u2*` and `/tmp/mibr*` references in project-owned C/Java/shell/Python source, with source file and line. It intentionally does **not** infer a reader, writer, safe migration mapping or comprehensive handling of dynamically concatenated paths. No file is moved and no unit state is touched.

The three CarPlay compatibility **presets** are not the three firmware **profiles**. The tool does not select a CarPlay preset for an installer, resolve user-persistent/platform overrides or assert a live effective value. A future multi-profile packager must supply an explicit selected preset and verified per-firmware overrides and fail its own final-package gate if these remain unresolved. Host inventory PASS is not an install or vehicle test.

## Persistent-storage migration review queue (host-only)

After the canonical source inventory is checked, run:

```bash
python3 tools/release/storage_migration_review.py --self-test --json-out storage-migration-review.json
```

The resulting review JSON is uploaded next to the existing defaults/path inventory
in the `source-defaults-unit-path-inventory` CI artifact. It enumerates the 13
source-defined CarPlay file groups and 13 separately owned broker switch files,
showing their actual source-declared identity, lexical reference locations and
**unapproved** proposed destination directory. It keeps the existing broker
magic/revision/CAS contract intact. New unknown broker keys and duplicate
broker source paths fail the audit; the built-in negative tests exercise both.

All entries deliberately start at `PENDING`, with no chosen destination
filename, completed consumer set or verified migration/restore path. A
CarPlay basename is **not** independent proof of where its runtime writer
opens the file; both its persistent and /tmp pathname are labeled candidates.
Unmatched lexical fragments and source lines requiring dynamic-path review
are separately listed. Comments, constants and generated paths can all produce
false inferences if treated as verified readers/writers.

`--require-migration-ready` intentionally **fails** on the current source.
The JSON is a worklist for reviewing actual C, Java, shell, generated and
boot-time consumers, not an approval to move persistent data, change defaults,
replace format-specific files or operate a vehicle. Before a migration release
is implemented, review every writer/reader and exact format, agree target
filenames and establish all update/uninstall/power-loss recovery gates in
[the on-unit storage contract](../../docs/architecture/UNIT_STORAGE_AND_NAMING_CONTRACT.md).

## A2.2 — categorize lexical paths without mistaking them for configuration files

Run after the source inventory and review generator:

```bash
python3 tools/release/storage_path_triage.py --self-test \
  --review-json storage-migration-review.json \
  --json-out storage-path-triage.json
```

This report groups the repeated lexical locations by **distinct literal fragment**
and category. It separates `/tmp/mibr-*` IPC/test-state references (retain
the volatile namespace), persistent presence/activation markers, known but
format-specific config, version receipts, runtime/bin/scripts, backups,
ownership receipts, and incomplete strings such as `%s.conf` or brace
fragments. It also expands nonliteral path-source leads into their exact
checkout line and categorizes environment `PATH`, root-directory composition,
comments, embedded runtime environment and remaining unknown contexts.

**A category is only a triage lead**, not proof of a real runtime file, safe
destination, actual reader/writer role, live activation or a completed migration.
Even `/tmp` references can be operationally relevant to boot/recovery; they
must not be renamed by the persistence cleanup. Source references from test
and host utilities are not treated as installed paths without evidence.

Review the actual CI JSON, then construct a source-linked ownership map of
each true persistent store, its single writer, all readers, exact file grammar
and aliases, and every boot/upgrade/uninstall/rollback consumer. Until that
work and negative recovery tests are complete, `migration_authorized=false`
in all reports and the earlier `--require-migration-ready` hard stop remains
in force. This report does not modify runtime or on-unit storage.

## A2.2 consumer cross-check (C/Java/QNX source, selected only)

Run `python3 tools/release/storage_consumer_crosscheck.py --self-test --json-out storage-consumer-crosscheck.json`.
Publication-audit CI produces this as a fourth JSON next to the source
inventory, the per-owner review worklist and the lexical path triage.

The host gate uses exact current source files to verify that the broker's
**13 declared durable paths, magic strings and operations match the Java
MibrDurableSwitch reader**. It also compares the shared firmware defaults
path across broker, Java and GEN2; the native menu loader path against
MibrMenuLayout; and the old /tmp + /mnt/app/root CarPlay grouped-store
roots across selected C consumers. It explicitly checks that CarPlay
persistent mutations remain `POLICY_BLOCKED`. Negative fixtures reject
C/Java pathname drift, menu loader/Java divergence and a removed persistent
write hard stop.

A substantive migration trap is already evident: the parity-drive toggle
is named `mibr-parity-drive.enabled`, but the current enable and disable
scripts **write the values `1` and `0`**. A suffix ending in
`.enabled` is therefore not evidence that the file is an existence-only
toggle. Audit actual readers before converting or renaming any marker.

This is **selected** source-proven evidence, not an exhaustive owner matrix:
other native scripts/Java/installer/boot readers remain to be enumerated.
No file is moved, no value becomes writable, and a unit migration is not
authorized by this CI PASS.

## A2.3 legacy marker semantics and boot/source evidence

Run `python3 tools/release/legacy_marker_contract.py --self-test --json-out legacy-marker-contract.json`.
The publication audit uploads the resulting source-pinned, machine-readable
review together with the earlier storage-path and consumer evidence.

It distinguishes six risky current file contracts: file-presence Auto-Direct
(including the generated OEM launcher hook); D2 persistent→volatile presence
bridge for retained older binaries; parity drive's actual `1`/`0` **content**
in a filename ending `.enabled`; inverse-polarity isoTX2 disable marker
embedded into DisplayManager startup; the broker's strict two-byte `1\n`
single-writer admission gate; and parity diagnostic `temp > persistent >
default` value-file precedence. Per role, the script checks the exact
current source token and records that source's SHA-256. Negative fixtures
reject missing/changed evidence. This does not authorize a replacement
format, rename, boot-hook modification, or unit write.

**Next:** separately enumerate additional readers, code-generated boot
content, restore paths, file ownership collisions and the remaining
legacy/config stores. A reviewed source-path map must include exact
writer/readback/CRC/CAS and on-vehicle rollback conditions before the later
coordinated persistent migration. `migration_authorized=false` remains
binding even when this host evidence gate passes.

## A2.3.2 source-linked persistent access graph (incomplete by design)

`python3 tools/release/storage_access_graph.py --self-test --json-out storage-access-graph.json`
generates a **host-only** combined graph from the existing CarPlay registry,
broker C/Java declarations, lexical path triage, targeted consumer contracts
and six high-risk marker fixtures. Publication CI uploads it alongside the
existing source inventories.

The graph enumerates the 13 CarPlay grouped stores and 13 Broker CAS stores,
then separately includes other source-visible persistent path candidates,
including backup/version/receipt files. It additionally reconstructs shell
`ROOT=/mnt/app/root` plus filename assignments in both legacy navigation
helpers, which a literal absolute-path scanner cannot see. All code-generated
boot hook boundaries for Auto-Direct and isoTX2 are kept as separate
outside-project restore obligations. This graph is **not** a complete live
on-unit snapshot. Even a literal hit may come from a test, template or log,
and a constructed candidate may have a historical alternate consumer.

Each candidate has an explicit missing reader/writer/format/destination/
rollback qualification; destination filenames are deliberately unset.
`--require-complete` fails until every relevant installed and generated
reader, writer, firmware adapter, installer, upgrade, uninstall and recovery
path has been reviewed and exercised. Negative fixtures reject unsafe
absolute paths, unexpected source collisions and a premature completion
claim. **Do not use the generated graph as an installation plan or migrate
files based solely on its category.** The detailed review and upcoming
per-file ownership decisions belong to the next A2.3/A3 source PRs.

## A2.3.2b navigation file formats and selected source IO (host-only)

`python3 tools/release/legacy_navigation_storage_contract.py --self-test --json-out legacy-nav-storage.json`
checks the 8 shell-composed persistent navigation paths and selected local
read/write semantics from `gen2_nav_config.sh` and `gen2_safearea.sh`, then
matches each path against the earlier 63-candidate access graph. The
publication audit uploads the report and runs negative fixtures for renamed
paths, missing reader/writer operations, altered format, and previously unseen
persistent filenames. The generator is excluded from the target-path source
inventory, which would otherwise count illustrative fixtures as runtime files.

These are **local script contracts**, not an exhaustive firmware or installed
binary consumer audit. They distinguish the nav query *presence* marker, legacy
map fallback *presence* marker with only local unlink observed, single-line
surface/tristate/maneuver settings, and four-key `x/y/w/h` SafeArea rectangle.
They also expose the existing nontransactional 5-file profile change,
independent remounts without a proven cross-component RW lease, missing
exact-byte backup/readback/RO verification, and temporary URL override
precedence. No added target writes, no rename and no permission to migrate
persistent state. All global writer, binary reader, recovery and final
destination gates remain false.

## A2.3.2b broker, menu and platform source grammar (host-only)

`python3 tools/release/broker_menu_storage_format.py --self-test --json-out broker-menu-storage-format.json`
verifies the exact source layout and selected local access semantics for all
13 revisioned broker-CAS files, the Java `MibrDurableSwitch` read path,
the CRC32 menu layout loaded by `mibr-menu.ksh`, and the shared
`mibr-platform-defaults.conf` override. It reuses the canonical
C↔Java inventory and 63-candidate storage graph, emits source SHA receipts,
and adds negative mutations for CAS, CRC, Java cache, stage and default changes.
The CI artifact is a source review receipt, **not** a firmware acceptance.

Java and native C now apply the same revision rule: canonical decimal, no
leading zero (except `0`), at most `18446744073709551615`. The Java switch,
menu-layout and platform-defaults readers cache by mtime/length, but do not
trust an mtime younger than 2 s, and platform defaults are re-read when the
file changes (broker C reopens them on every lookup). An entry read while its
mtime was inside that window is never trusted later. A file whose mtime lies
ahead of the unit clock keeps the plain cache rule. Limit: a foreign rewrite
that keeps both the size and the exact old mtime stays invisible to any
mtime+size cache; writers must not restore an old mtime onto a changed file. The broker
C's own guarded CAS/fsync/rename/readback/RO restoration does not protect
the older independent navigation scripts or the menu shell's separate loader.

All selected local source checks may PASS with **unresolved installed/legacy
readers, format conflicts, backup/upgrade/uninstall and rollback**. The tool
deliberately leaves target paths unset and the migration completion gate
closed; A2.3.2b and B2 are not done from this host audit alone.

## A2/A3 proposed destination names and source owner separation (host-only)

Run `python3 tools/release/storage_destination_plan.py --self-test --json-out storage-destination-plan.json`.
The planner consumes the existing 63-candidate `storage_access_graph.py` output:
13 grouped CarPlay registry files, 13 native broker CAS/revision files and
37 separately classified additional path candidates. It supplies collision-
checked **candidate** target names under `/mnt/app/root/altscreen-u2/`,
including separate namespaces for CarPlay registry values, navigation,
menu, cockpit, feature intent, receipts and exact stock backups.

The output preserves the difference between revisioned broker files,
CRC menu layout, shell navigation's old per-file grammar, file-presence
boot switches, scalar values and ownership/version receipts. It holds
legacy navigation aliases, opposite bit26 force flags, backup directories,
unproven test artifacts and the early-boot two-byte single-writer gate
rather than fabricating a safe conversion. Critically,
`mibr-carplay-autodirect` (registry value) and
`mibr-carplay-autodirect.enabled` (legacy boot-presence flag) have
**different** candidate identities. Changing existing native content
formats requires a dedicated parser/converter and all consumers together.

Every row also carries an A3 disposition (`a3_disposition`, `a3_reason`,
`a3_single_writer`): **18 MIGRATE** (12 broker CAS switches, display
scaling, menu language, menu layout, platform defaults, two installer
ownership receipts), **40 KEEP_AT_LEGACY** (all 13 CarPlay registry groups,
because the native settings layer refuses persistent writes, plus boot
markers, aliases, backups and the single-writer gate), **2
EXCLUDE_NONCONFIG** (calibration clip, test-only script) and **3
BLOCKED_INPUT** (SD-log switch, two version receipts whose writers are not in
source). Only MIGRATE rows have a `candidate_destination_path`; every other
row keeps its former proposal as `reserved_future_name`, so two kept stores
can never collide in one target. Negative tests reject a held alias marked
MIGRATE, a reserved-name collision, a value boolean (absent means ON)
relabelled as presence, a stock backup split from its held directory, a
second writable safe-area store and a MIGRATE row without exactly one
writer.

This is a naming and source-provenance **proposal**, not implemented MMX
paths. All `verified_destination_path` fields remain null, and
`migration_authorized=false`. Negative tests reject path traversal, unknown
legacy stores, duplicate destinations, premature source approval and
silent alias merging. `--require-migration-ready` is deliberately
fail-closed. Firmware-specific installed readers, generated boot hooks,
backup/restore, RW/RO mounts, upgrade and unattended power-loss recovery
must still be proven before a coordinated installer cutover.
