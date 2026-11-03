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
