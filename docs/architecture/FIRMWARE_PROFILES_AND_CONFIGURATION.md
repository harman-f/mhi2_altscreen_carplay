# MIB Runtime: firmware profiles and unified configuration (architecture contract v2)

> Status: **v2, 2026-11-04, owner decisions E1–E6**. v1 was the draft before E1–E6. Decisions are marked **[E#]**, technical assumptions **[Assumption]**. Base: `main` `5a6533c` / `develop` `0c08a9a` (same tree `3e10cce`), plus the pending change sets listed in §5. The SEAT adapter work, the MU1409/MU1447 menu comparison and the firmware extraction are private research evidence (not public). None of this is unit or vehicle proof.

## 0. Summary

- **Name [E6]:** MIBR = **MIB Runtime** (MIB = Modularer Infotainmentbaukasten, R = Runtime). This is a product definition dated 2026-11-04, not a historical derivation. MIBR means the whole runtime platform. The control service is called the **Broker** (`controller`).
- **Three layers, tested separately:** development repository (module owners) → generated distribution ZIP (`common/`, `profiles/`) → installation on the unit under **`/mnt/app/root/mibr/`** [E6]. A move in the repository is not a path change on the unit, and vice versa.
- **One code base, N firmwares:** CarPlay (Auxiliary Receiver, formerly GEN2), Broker, menu core and navigation are 100 % shared. Per firmware only **data** varies (fingerprints, geometry, OEM IDs, icons, key maps, transformations) plus a **thin Java adapter layer** against the OEM API.
- **Measured** (SEAT MU1409 against the shared Java state, which is byte-identical with main): 162 of 10 806 Java lines differ (**1.5 %**: +130/−32). Because the research tree overwrites whole files, the current cost is **6 files / 1 405 lines (≈ 13 %)** per firmware. With an adapter interface this becomes ≈ 250 lines per profile.
- **One configuration source:** `settings/registry.json` becomes the sole owner of the 48 CarPlay keys **and** the 13 Broker switches. All bindings (C, Java, shell, editor) are generated from it. Storage locations follow storage decisions D7–D12 (approved 2026-11-04).
- **One package:** `common/` + `profiles/<id>/` (PACKAGE_LAYOUT). OEM files are only modified by transformation, never shipped as bytes. Single-profile test packages are allowed (`scope: single-profile`).

## 1. Layers: what belongs where

| Layer | Content | Today | Target |
|---|---|---|---|
| **Core** (shared) | `modules/carplay`, `modules/broker`, `modules/menu/source` (core Java, generator, menu format), `modules/navigation` | as target. Exception: Skoda specifics in the core (see below) | no brand or firmware literals in the core; every variation goes through profile data or the adapter interface |
| **settings/** (own module) | `registry.json`, generators, generated bindings | listed in the module index only under `broker.source` (`modules/module-index.json`), K1 | own module index entry `settings`; `carplay`, `broker` and `menu` depend on it |
| **Profile** `modules/profiles/<id>/` | `profile.json`, `display/`, `hmi/`, `integration/`, `icons/`, `input/` | only `profile.json` and 15 placeholder READMEs. The only reader is `tools/release/plan_multi_profile_beta.py` | all firmware differences live here, in the package under `profiles/<id>/` |

Profile content in detail (target). Bold marks what lives elsewhere today:

| Group | Content | Elsewhere today |
|---|---|---|
| `profile.json` | id, brand, firmware string, `selector` (sha256 of `/ifs/lsd.jxe`), **`hmi.api_jar_sha256`**, **`hmi.adapter`** (class name or `adapter_from`), **`evidence`** | lsd.jar hashes exist only in private research build scripts (MU1409 `cda36398…`, MU1447 `203087fe…`) |
| `display/` | **`platform-defaults.conf`** (safe_voll/wide/center etc.), tile geometry, stream dimensions | `modules/navigation/source/platform-defaults/skoda-mu1440.conf:3-5`; tile dimensions hard-coded in Java (`MibrHomeList` Skoda 235×154, SEAT 150×150) |
| `hmi/` | adapter implementation (Java), `oem-anchors.json` for `prepare_oem_sources.py`, OEM IDs (e.g. `INTERNAL_VIEW_ID` 982 vs. 957), build receipt + built JAR | SEAT: 6 override files plus a separate patcher in private research evidence |
| `integration/` | `variants.list` + transformations (`.awk`/`.block`) for startup.sh, smartphone_integrator.json, usblauncher_otg.lua, lsd.sh block | in the pending MU1440 stock-transform change set: `profiles/skoda-mu1440-p4526/integration/{si-carplay,lua-rgi}.awk`, `install_preload.sh` Guard:Gate |
| `icons/` | project-owned menu icons per brand/firmware (home tile, menu symbols, scroll assets where different; e.g. SEAT gear 150×150 `db25dd8c…`). The core references icons only by logical name; the mapping name → file is in `icons/icons.json` | private research evidence (SEAT skin icons) |
| `input/` | only deviations from the shared key map (normally empty). Key assignment depends on the steering-wheel/keypanel hardware, not on the firmware: shared map `common/input/keymap.json` (logical action → keypanel group/code; measured 11 Oct: right press 4/40, right back 4/41, right phone 4/53, left up 4/46, left down 4/47, left press 4/44, voice 4/50, Home 13/116, Menu 13/78, Power 13/88; long press left = CarPlay↔native, right = view sync). Reported by the project owner (2026-11-04) as identical for both firmware variants. Broker/`mibr-key40d` and menu read logical actions only | values evidenced; profile override only on proven deviation |

**Variation points in the Java code, measured** (diff against the shared state; the 5 base files are byte-identical with main):

| File | ± lines | What differs | Kind |
|---|---|---|---|
| `MibrOemSsmTemplate` | 12 | `INTERNAL_VIEW_ID` 982→957, comments | **Data** |
| `MibrHomeList` | 94 | icon geometry; SEAT uses a native `StaticImage` + gear overlay instead of the Skoda 4-state icon and empty stock art | **Code** (`HomeTileRenderer`) + data |
| `MibrHomeAnimationMirror` | 19 | SEAT animates the container (`GridMenuPlate`), table with 3 rows | data (table) + small code path |
| `MibrNativeDropdownEditor` | 7 | availability depends on live OEM widgets instead of `MibrOemDropdownStyle` (MU1440) | **Code** (strategy) |
| `MibrOemTileLongPress` | 10 | MU1409 `deInit` deletes the listener → re-register on every init | candidate **for the core** (`addIfAbsent`; not yet checked on MU1440) |
| `MibrSeatGearOverlayImage` | +20 | new class, asset path | profile |
| `prepare_oem_sources.py` | 61 of 129 | MU1409: `throws Exception`, no `InvalidSyntaxException` block | anchor set per profile |

MU1447 takes over the MU1409 adapter unchanged. Differences: `getImage(index+6)`; the two patched OEM classes are byte-identical (private research evidence). `lsd.jar` MU1409 vs. MU1447: 24 247 of 26 240 classes are byte-identical; in the menu area 905 of 978 (private comparison report, not public).

## 2. Unified configuration system

### 2.1 One schema, five layers

`registry.json` schema 3 (today 2, `settings/registry.json:2`) describes every value exactly once: key, type, allowed/min/max, apply, hmi, **storage** (exactly one location, §2.4), defaults per layer.

| Priority (low→high) | Layer | Source | Writer | Today |
|---|---|---|---|---|
| 1 | compiled | `registry.json` `default[preset]` → generated C/Java | generator | yes (`tools/generate_alt111_settings.py:24-26`, 3 presets hard-coded) |
| 2 | firmware-profile | `registry.json` `profile_defaults[<profile_id>]` (only keys that actually differ) | generator (compiled into the bindings per profile) | missing; today these values sit in C defaults such as `0,58,1010,248` (`mibr_durable_switch.c:36-40`) |
| 3 | platform/installer | `config/platform/defaults.conf` from `profiles/<id>/display/platform-defaults.conf`, chosen by fingerprint | **installer only** | yes, as `mibr-platform-defaults.conf`, read by GEN2 (`libaltscreen111_gen2.c:1261`), Broker (`mibr_durable_switch.c:45,83`) and Java (`MibrPlatformDefaults.java:11`) |
| 4 | persistent (user) | registry group or Broker CAS file | **Broker only** | CarPlay: blocked (`settings_posix.c:480`, `settings_cli.c:101`); switches: yes |
| 5 | temp | `/tmp/mibr-*` | Broker / alt111-settings | yes |

Rules:
- A lower layer never overwrites a stored value. For safe areas this is already implemented (`libaltscreen111_gen2.c:1267-1314`: Broker choice > stored registry value > platform default > compiled).
- **Fix the name conflict:** in `layer_order` the preset layer is currently called `profile` (`registry.json:3-8`, C `ALT111_PROFILE`). It is renamed `preset`. "Profile" then means only the firmware profile.

### 2.2 Consumers (all generated)

| Consumer | Binding (generated from registry.json) | Reads at runtime |
|---|---|---|
| C GEN2 / alt111-settings | `registry_generated.h`, `registry_table_generated.h` (present) + `storage_paths_generated.h` (new) | layers 3–5 |
| Broker C | `switch_defs_generated.h` (new, replaces hand-written `mibr_switch_defs`) | CAS files, platform defaults |
| Java menu | `MibrSettingsCatalog`, `MibrMenuDefinition`, `MibrSwitchCatalog` (new): **build output only, never checked in** | Broker via MIBR/3; `MibrPlatformDefaults` read-only |
| Shell / installer | `runtime-paths.generated.sh` (replaces the currently unused `runtime-basenames.generated.sh`) | – |
| Menu editor | `function-catalog.json` (generated part) | – |

CI: `generate_*.py --check` for all outputs. In addition a gate that rejects every absolute `/mnt/app/root/…` path in C/Java/ksh that is not listed in `storage_paths`.

**Versioning:** `schema` is only raised on a format change. Every key rename needs an `aliases` entry and a migration step in the installer (one-time import, §6). For file formats the storage contract applies (`UNIT_STORAGE_AND_NAMING_CONTRACT.md`): CAS magic/revision and menu CRC stay byte-exact.

**Names:** keys `domain.name` (lowercase, dot); new files `config/<domain>/<kebab>.conf`; feature switches positive (`auto-direct=1`); profile IDs `<brand>-<mu>-<train>`.

### 2.3 Conflicts K1–K9: one rule each

| # | Conflict | Rule |
|---|---|---|
| K1 | registry.json belongs to the Broker according to the module index, but its generator is in carplay (cycle) | own module `settings` without dependencies; carplay/broker/menu `depends_on: [settings]` |
| K2 | the checked-in `MibrMenuDefinition.java` is stale against the generator; `build.sh:26-33` compiles the checked-in **and** the generated copy. The SEAT `build_j9.sh` also uses the checked-in copy | never check in generated Java files. `build.sh` and profile builds take only `$OUT/catalog`. CI verifies that no `*Generated*` copy is in the tree |
| K3 | 13 Broker switches maintained by hand in 8 places | `switches[]` section in registry.json; the generator emits the C table, Java constants, editor catalog and the `api_v3_contract` op list |
| K4 | safe-area defaults in three places (C, platform file, Java) | exactly one user owner: Broker CAS (`config/cockpit/safe-*.conf`). Compiled default from the registry, firmware default from `profiles/<id>/display/`. The matrix documentation is generated |
| K5 | sourceVersion rule (950.7.1/1005.8.1) kept by hand in `MibrDraftChoiceModel.java`, GEN2, editor, tests | `allowed` and the rule live only in registry.json; Java/editor get it generated; tests read the registry |
| K6 | duplicate protocol models (root `src/`) | done: removal of root `src/` (pending change set, §5) |
| K7 | two parity-supervisor copies (broker r53 vs. carplay) | owner is `modules/carplay/runtime/parity`. The Broker copy is removed after a diff (also the D9 gate for `parity-drive`) |
| K8 | LSD hash in four places (profile.json, `install.sh:108`, `release/CURRENT.md`, profile README); in addition `install.sh:382` checks `/mnt/app/eso/hmi/lsd/lsd.jxe` while the selector uses `/ifs/lsd.jxe` | `profile.json.selector` is the only source. `profiles.list`, README table and CURRENT are generated. `plan_multi_profile_beta.py:74-80` will check all copies. One selector path for all |
| K9 | `adapter_status` and `evidence` are free text without validation | `adapter_status` becomes an enum (`none/source/built/unit-tested`); `evidence` must name path + hash, `check_module_index.py` verifies this |

### 2.4 Persistent switches and storage locations (storage decisions D7–D12, refined by E4/E6)

**Target tree [E6]:** exactly one project root. The former target root `/mnt/app/root/altscreen-u2/` from `UNIT_STORAGE_AND_NAMING_CONTRACT.md` and `storage_destination_plan.py` is **obsolete**. The groups below it stay the same, only the root changes, and there is no second, subsequent target migration.

```text
/mnt/app/root/mibr/
  bin/                           binaries, runtime libraries (today scattered: altscreen-u2/, mibr-rgi/, mibr-kit/)
  scripts/                       start, guard, service, installer, recovery helpers (boot.ksh, boot-guard.ksh, firewall.ksh, mibr-watch.ksh …)
  config/carplay/<group>.conf    registry persistence layer, 12 groups (D7); active only after the beta [E5]
  config/cockpit/                safe-{voll,wide,center}.conf (Broker CAS, D8), scaling.conf
  config/navigation/             carplay-nav.conf, nav-*.conf (Broker CAS)
  config/menu/                   layout.conf (CRC, mibr-menu.ksh), language.conf (Broker)
  config/platform/defaults.conf  installer, chosen by fingerprint, fallback only (D11)
  config/features/*.conf         auto-direct, parity-*, rgi, cpvc, sd-log, expert-mode (positive, value 0/1)
  config/vehicle/                data-mode.conf, status-mode.conf
  state/boot/disabled            SINGLE kill switch [E4] (presence flag), plus boot failure counter
  state/cockpit/                 view/position (D12; owner mibr-view.ksh)
  version/                       installed-version.properties, components.manifest, install-defaults.receipt
  version/ownership/             most20.marker, navignore.marker, d2-marker.owned, lsd-block.owned, …
  backup/<migration-id>/         original snapshots, upgrade/rollback evidence with hashes
  logs/                          controlled, size-bounded logs only
/tmp/mibr-*                      volatile (IPC/lock/PID/status), names unchanged until a separate cutover
```

OEM locations (`/ifs`, `/mnt/app/eso`, stock startup files) are **not** moved into the project root. Changes there happen only through hash-bound transformations with their own restore contract (§4).

**One writer per physical storage group [E2].** Not every key needs its own file: the 48 CarPlay keys deliberately share 12 group files. Registry rows carry `storage: {group, format, writer}`; the groups are declared once in `storage_groups{}` with `path`, `format` (presence / value01 / keyvalue / cas / crc / binary) and exactly one `writer`. Generator and validator check uniqueness **per group/file**: two groups with the same path or one group with two writers are errors, several keys in one group are not. Separate owners remain: CAS switches (Broker), menu CRC (`mibr-menu.ksh`), platform defaults and receipts (installer), view state (`mibr-view.ksh`), volatile `/tmp` files. `storage_destination_plan.py` checks against registry.json instead of keeping a second list.

**Prove formats per path:** presence flag ≠ `0/1` value ≠ CAS magic/revision ≠ CRC. Inverted semantics (`*.disabled`, `-disable`) are converted to positive switches during the move **only** together with reader and writer. The path search also covers composed paths (base variables, Java concatenation, embedded startup blocks), not only string constants (inventory §7).

**Status of the 66 candidates** (own-runtime-parts change set, self-test `storage_destination_plan.py:599-604`): MIGRATE_AS_PLANNED 18, DEFER_MIGRATION 20, CONSOLIDATE_OR_RETIRE 13, KEEP_TECHNICALLY_REQUIRED 2, EXCLUDE_NONCONFIG 8, BLOCKED_INPUT 5. `kit/disabled` changes through E4 from KEEP to **MIGRATE** (target `state/boot/disabled`, legacy only as migration source).

**Rule: no new paths at legacy locations.** New code reads and writes only paths from the generated `storage_paths`. Exceptions are declared explicitly: OEM/stock locations (`oem_paths`) and legacy paths read only by the upgrade migrator (`migration_sources`). A gate "every absolute path must be in the registry" without these lists would forbid legitimate `/ifs` accesses. Violations today (resolved with the root move):

| Location | Legacy path | Target |
|---|---|---|
| own-runtime-parts change set: `cpvc_config.sh:14`, `boot.ksh:14` | `/mnt/app/root/mibr-cpvc.enabled` | `mibr/config/features/cpvc.conf` |
| same: `boot.ksh:8`, `boot-guard.ksh:10`, `mm-ipod-rgi.sh:12` | `/mnt/app/root/mibr-kit/disabled` | `mibr/state/boot/disabled` [E4] |
| same: `mm-ipod-rgi.sh:9` | `/mnt/app/root/mibr-rgi/` (payload + `rgi.on`) | `mibr/bin/`, `rgi.on` → `mibr/config/features/rgi.conf` |
| stage-2 design notes (line 202) | `/mnt/app/root/mibr-kit/boot.ksh` | `mibr/scripts/boot.ksh` |
| stage-2 design notes (line 233) | receipt copies in `mibr-kit/` | `mibr/version/` only; `MibrVersionInfo.java:13` reads `version/installed-version.properties` |
| stage-2 design notes (lines 60, 235) | `mibr-kit/firewall/`, `firewall.ksh` | `mibr/scripts/`, stock image `mibr/backup/`, ownership `mibr/version/ownership/` |
| all consumers | `/mnt/app/root/altscreen-u2/**` | same group under `mibr/` |

**D7–D12: code vs. plan**

| D | Content | Implemented in code | Planned only |
|---|---|---|---|
| D7 | one persistent CarPlay channel (registry persistence layer, Broker writer) | classification in the plan tool; replay reader in source (`cpvc_config.sh`) | **[E5] after the beta:** writer (today `POLICY_BLOCKED`), import of `cpvc-r5.profile`, power loss/readback/reboot/RW-RO/rollback per firmware. The beta keeps `cpvc-r5.profile` as the only authority |
| D8 | safe area: Broker CAS is the sole user authority | GEN2 precedence stored > platform default (`libaltscreen111_gen2.c:1267-1314`) | move to `config/cockpit/`, remove `safearea.conf` |
| D9 | boot/feature switches | isoTX2 `-disable` stays | `features/*.conf`, consolidate D2 and fps, one supervisor |
| D10 | registry navigation group is the owner | – | remove 6 legacy nav files + url-map |
| D11 | platform = installer fallback; ownership → `version/ownership/` | upgrade preserves D2 and navigation (`install.sh:620-627`) | most20/navignore markers, mibr-kit receipts to `version/` |
| D12 | paths outside the 63 (mibr-view, boot-guard, lsd.sh backups) | – | `state/cockpit/`, boot-guard to `scripts/`, remove lsd.sh backups |

**Migration: correction against v1.** v1 provided compat readers in stage 2 that read "target first, else legacy" while only legacy continued to be written; stage 3 then copied once. This is **rejected**: after a stale copy the reader would ignore newer user changes. New rule: **reader and writer of a group switch together, in the same installation.** Until then the existing writer remains authoritative, and a staged target copy is never read authoritatively.

This yields two separate migrations:

**M1 – root move `altscreen-u2/` + `mibr-kit/` + `mibr-v3/` + `mibr-rgi/` + `mibr-*.enabled` → `mibr/` [E4, E6].** `mibr-v3/` (Broker binary, `mibr-v3-boot.ksh`; callers `boot.ksh:25`, `mibr-watch.ksh:14-16`, `mibr_broker_quiesce.c:26`) is a third legacy root and moves to `bin/` or `scripts/`. The RW writer compares the path with an exact `strcmp` (`mibr_v3_qnx_mount.c:79,160`) and rejects other paths, so Broker, GEN2 `.so`, Java JAR, scripts and hook text must be switched together. Pure location change without format change, as one installer transaction. There is no shipped intermediate state in which guard, writer and reader point to different roots, and no compat readers at runtime.
1. Preflight: profile by JXE fingerprint [E3], lock, RW lease, free space. Failure → no write operation.
2. **Kill switch first:** if `mibr-kit/disabled` exists, `mibr/state/boot/disabled` is created immediately and read back. In addition the installer creates `state/boot/disabled` as an install lock for the duration of the transaction (content `install-in-progress <id>`) and removes it only at the end, and only if the previous state was not disabled. An abort at any point therefore leaves the system disabled, never unintentionally active.
3. Snapshot the old trees to `mibr/backup/<id>/` with `SHA256SUMS`, file modes and owner.
4. **Copy, do not move:** build `mibr/.staging-<id>/`, bytes 1:1 (CAS/CRC unchanged), read back against the snapshot, then `rename` to `mibr/` (same filesystem). User values are never overwritten.
5. Install new binaries and scripts that know only `mibr/`. Then switch the OEM hooks (lsd.sh block, startup/usblauncher transformations) to the new script paths, as the last step before commit.
6. Receipt in `mibr/version/` (migration ID, source/target hashes). Remove the install lock (see 2.).
7. The old trees stay **unchanged and unreferenced** as rollback source. Rollback to the previous package means: hooks back, old trees untouched. Changes made after the migration are lost in that case (documented). The old trees are deleted only in a later package after unit acceptance; until then the kill-switch reader ignores the old location.
8. Uninstall restores only what `version/ownership/` lists as own intervention, and removes `mibr/` only afterwards.

**M2 – format/writer change per group** (D7 writer, D9 feature hooks, D10 nav cleanup). One PR each, reader and writer in the same release, with conflict, revision and rollback tests. D7 only after the beta [E5].

**Reclassification of sd_log:** the pending SD-log reader change set supplies the missing reader (`parity_drive_supervisor.sh:125`, `MIBR_SD_LOG/1`; writers Broker `mibr_durable_switch.c` and Java `MibrDurableSwitch`). After this lineage is confirmed, the row changes from BLOCKED_INPUT → MIGRATE_AS_PLANNED (target `mibr/config/features/sd-log.conf`) and the switch is added to `switches[]`.

**Regressions for M1 (host, then unit):** boot failure counting, automatic disable, early-boot guard, reboot, unlock, damaged/missing directories, RW/RO return, abort in every transaction step, upgrade with disabled prior state, uninstall, recovery, rollback.

**Gates:** `migration_authorized` and `final_destination_reviewed` stay `false` until it is proven per profile on the unit: RW lease/RO return, power loss while writing, readback after reboot, rollback. M1 may be created as code and host test; it is installed only with approval.

## 3. Java menu JAR per firmware

- **[E1] One core source tree** `modules/menu/source/java`, no complete SEAT override files as a permanent solution. New is an interface `MibrOemProfile` with the variation points from §1: `viewIds()`, `homeTileGeometry()`, `homeTileRenderer()`, `dropdownAvailability(stock)`, `animationTable()`, `imageIndexOffset()`, `listenerLifecycle()` (re-registration after `deInit`), back/focus/scroll/slider strategy. The ≈ 250 adapter lines are an estimate, not a limit. Profile values count as implemented only when executable code reads them. The data (IDs, dimensions, tables) is generated from `profiles/<id>/hmi/oem.json`. Code lives only in `profiles/<id>/hmi/java/…/Mibr<Brand>Adapter.java`.
- **Build per profile:** `tools/build_profile_hmi.sh <id>` = generator + core + profile adapter + `prepare_oem_sources.py --anchors profiles/<id>/hmi/oem-anchors.json`. Compilation is against the profile's `lsd.jar` (hash from `profile.json.hmi.api_jar_sha256`, otherwise abort), with J9 `-source/-target 1.2`, `verify_class_major.py --major 46` (cf. `build.sh:26-40`). The receipt contains core tree hash, adapter hash, API JAR hash and JAR hash.
- **MU1447:** `profile.json.hmi.adapter_from: seat-mu1409-p4708` plus its own `api_jar_sha256` and `imageIndexOffset=6`. No copied classes.
- **Installer selection:** `sha256(/ifs/lsd.jxe)` must hit **exactly one** row in `installer/config/profiles.list` (generated from all `profile.json`). The firmware string is only cross-checked: if it differs, the installer stops; it is not usable as a selector. On an unknown, missing or ambiguous match no write operation happens (PACKAGE_LAYOUT.md:45; assembler `build_mu1440_modular.py:208,357`). `P4708_1` is unknown until measured and is rejected.

## 4. Package

- Layout per `docs/build/PACKAGE_LAYOUT.md:5-35`: `common/<module>/{bin,scripts,config}` once, `profiles/<id>/{hmi,icons,display,input,integration}` per profile, `source/` + `SOURCE_MANIFEST.json`.
- **Scope:** without `scope` all three profiles must be present. With `"scope": "single-profile"` exactly one known profile is allowed (implemented in the pending validator change set, `validate_modular_package.py:19-60`).
- **Transformations instead of OEM bytes:** `variants.list` = `target stock_sha patched_sha transform transform_sha [mode]`. A transformation is applied only to a known stock hash, and the result must have the expected hash. The validator rejects files that look like OEM payload or whose bytes equal the stock or patched hash (pending validator change set, PACKAGE_LAYOUT addendum). Examples: `si-carplay.awk`, `lua-rgi.awk`, Guard:Gate block for startup.sh (pending MU1440 stock-transform change set).

## 5. Implementation plan (small PRs)

**Already prepared as pending change sets** (base main `5a6533c` = develop `0c08a9a`, same tree `3e10cce`, checked 2026-11-04):

| Change set (by content) | Status after E1–E6 |
|---|---|
| Documentation refresh | still valid |
| Removal of root `src/` (K6) | still valid |
| CI cleanup | still valid |
| Validation of the final ZIP | still valid |
| Single-profile validator scope + transform variants | valid |
| MU1440 stock transforms + tests | valid; hook targets switch to `mibr/scripts/` with M1 |
| MU1440 modular assembler | to be extended to the three-profile assembler (PR 9) |
| Own runtime parts import (boot.ksh, boot-guard, cpvc_config, RGI wrapper, extender P1) | paths are legacy → switch in PR 6 (M1) |
| SD-log reader + lock diagnostics | valid; confirm the sd_log lineage afterwards |

**Order:**
1. **Contracts:** this document, `UNIT_STORAGE_AND_NAMING_CONTRACT.md` (root `mibr/`, altscreen-u2 targets marked obsolete), naming matrix §7. No runtime change.
2. **Module index:** `settings` as its own module (K1); stop checking in generated Java files (K2, verify the J9 build).
3. **Registry schema 3:** `profile`→`preset`, `switches[]`, `storage_groups{}`, `profile_defaults{}`; generators C/Java/shell/editor; path gate with `oem_paths` and `migration_sources` (K3, K5).
4. **profile.json v2 + selector [E3]:** `selector.lsd_jxe_sha256`, `firmware` (cross-check only), `hmi.api_jar_sha256`, `adapter[_from]`, `evidence`; generated `profiles.list`; one selector path `/ifs/lsd.jxe` (K8, K9). P4708_1 stays rejected.
5. **Platform defaults** to `profiles/<id>/display/`, shared `common/input/keymap.json`, icon mapping `icons/icons.json` (K4).
6. **M1 root and kill-switch move** (§2.4) with all consumers in one PR: boot guard, early hooks, start/stop, RGI, watchdog, diagnostics, Java, installer, uninstall, rollback, SD scripts, CI. Host regressions for every transaction step.
7. **[E1] `MibrOemProfile`** + Skoda implementation in the core. Evidence via J9 major 46, API check against the profile `lsd.jar` and view-model regression tests, **not** byte identity.
8. **SEAT MU1409** as adapter + anchor set; **MU1447** via `adapter_from` + offset 6, built against its own `lsd.jar`.
9. **Three-profile beta ZIP** (assembler, validator, installer with profile selection, rollback), check of the real final ZIP and negative cases.
10. M2 steps per group; D7 writer only after the beta [E5].

## 6. Owner decisions (2026-11-04, binding)

| # | Decision |
|---|---|
| E1 | Shared Java menu core + thin firmware adapter (`MibrOemProfile`). No permanent override files. Check J9 major 46, no byte identity required |
| E2 | `settings/registry.json` schema 3 is the sole **definition** source (48 CarPlay keys + 13 Broker switches, `sd_log` after lineage confirmation). One registry ≠ one file; writer uniqueness per physical group. `settings` is its own module owner |
| E3 | Only automatic selector: SHA-256 of `/ifs/lsd.jxe`, exactly one match. Firmware string is a mandatory cross-check. Unknown/ambiguous/contradictory → no write operation. API `lsd.jar` hash is separate. P4708_1 not without evidence |
| E4 | The kill switch moves completely to `/mnt/app/root/mibr/state/boot/disabled`. `mibr-kit/disabled` is only a migration source, the disabled state is preserved, no permanent second reader. (The v1 recommendation "legacy stays readable permanently" is thereby rejected) |
| E5 | D7 writer only after the beta; the beta keeps `cpvc-r5.profile` |
| E6 | MIBR = MIB Runtime; one root `/mnt/app/root/mibr/`; GEN2 → functional name (CarPlay Auxiliary Receiver); real ABI/wire/format/release IDs remain |

Further rulings: the key map depends on the steering-wheel hardware and is identical for all profiles (`common/input/keymap.json`); menu icons are per profile. One three-profile beta ZIP; beta inclusion is not a vehicle qualification. Status is kept separate: `SOURCE_BUILD_PASS` / `PACKAGE_VALIDATED` / `UNIT_TESTED` / `VEHICLE_RELEASE_APPROVED`.

## 7. Name inventory (U2, GEN2, Rxx, alt111, MIBR/3, CPVC)

Rule [E6]: real wire/ABI/file-format/release IDs remain until a separate, tested contract change. Vague generation labels are retired. Counts: develop `0c08a9a`, lines/files.

| Identifier | Extent | What it stands for today | Decision |
|---|---|---|---|
| `altscreen-u2` | 167 / 62 | location on the unit, compiled into C/Java literals | **Retire** in favor of `mibr/` (M1, all consumers together) |
| `U2_*`, `U2-LOG.txt` | `auto-direct/common.sh` | shell variables, log name | **Retire** (variables freely; log name together with the log collectors) |
| `GEN2` (files, scripts, CI, prose) | 914 / 144 | development generation | **Retire** in favor of "CarPlay Auxiliary Receiver" (module/docs/build entry points, step by step) |
| `/tmp/mibr-alt111-gen2.status`, `-reacquire`, `gen2=1` | cross-process | IPC contract | **Keep** (volatile `/tmp/mibr-*` stay) |
| `mibr-gen2-*` backup folders | restore paths | legacy installations | **Keep** as restore source |
| `R57`, `R46…R56`, `r14` | 65 + 289 lines | iteration labels in comments, docs, file names (`*_r53.sh`, `r52-*.diff`) | **Retire** in prose and file names (with references in `module-index.json`, audit script, tests); no wire/receipt field affected |
| `alt111`, `altscreen111`, `ALTSCREEN111_PORT` | 1 840 + 211 | C symbols, env names, installed binary names, OEM patch in `smartphone_integrator.json` | **Keep** ("111" = stream-111 view) |
| `MIBR/3` | 149 | wire version in the loopback frame (`mibr_v3_client.c:98`) | **Keep** (only with a protocol change) |
| `mibr-v3/` install folder | 3 callers | location | **Retire** → `bin/`, `scripts/` (M1) |
| `/tmp/mibr-v3-*`, `mibr-v3-single-writer.enabled` | | IPC, qualification gate (2-byte contract) | **Keep** |
| `mibr_v3_*` source file prefix | | internal | optional, cosmetic, not in M1 |
| `CPVC`, `cpvc-r5.profile` | 67 / 23 | feature ID; file name read by the Broker, `-r5` = schema generation | **Keep** feature ID; file name stays until D7 after the beta [E5] |
| `MIBR_*/n` magics, `MIBR_COMPONENTS/1`, `product=MIBR-CarPlay` | 101 / 27 | file format/receipt | **Keep**, migrate bytes 1:1 |
| `mibr-kit` | 24 / 9 | location (Java, ksh), installer script name, lsd.sh marker block | **Retire** the location (`version/`, `state/boot/`, `scripts/`); uninstall must keep recognizing the old marker block |
| `mibr-isotx2-gate-disable`, `mibr-parity-*-enabled` | in the patched startup.sh | inverted or absent=ON semantics | **Keep**, convert only together with reader and writer (M2) |

**Gap:** the kit installer, lsd.sh block, CPVC installation tree and `/mnt/app/eso` hooks are not in the public source tree. Their path literals cannot be verified there; before M1 they must enter the repository as source or transformation (stage-2 installer).

**E3 evidence** (state of #107 and the profiles):

| Profile | `/ifs/lsd.jxe` SHA-256 | Evidence | Status |
|---|---|---|---|
| skoda-mu1440-p4526 | `a55d9cfb…cbeea8`, 55 840 933 B | own unit, bytes in private research evidence (not public) | selector approved |
| seat-mu1447-p4709 | `945586fb…cb22e`, 55 712 574 B | firmware corpus | selector as source; unit confirmation open |
| seat-mu1409-p4708 | `25b9f128…904403`, 55 712 590 B | original firmware image, variants 50 and 70 recomputed independently (2026-11-04) | selector enabled for the beta (owner decision 2026-11-04); unit confirmation open |
| seat-mu1409-p4708_1 | – | length 55 712 590 B only, no identity | rejected |

API `lsd.jar` for the Java build (`hmi.api_jar_sha256`, checked by `modules/menu/source/build.sh`): MU1440 `57dc5e93…3ae7` (documented J9 build input; the other reconstructions `5a65c4bb…` and `d012c2a6…` are not build inputs), MU1409 `cda36398…a06f`, MU1447 `203087fe…9c88`.
