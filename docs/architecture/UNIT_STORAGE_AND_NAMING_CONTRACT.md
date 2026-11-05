# MIB Runtime (MIBR) on-unit storage and naming contract (design proposal)

> **Superseded target:** earlier revisions used `/mnt/app/root/altscreen-u2/` as target root; that target is obsolete. The single target root is `/mnt/app/root/mibr/` (decision E6, 2026-11-04; see [firmware profiles and configuration](FIRMWARE_PROFILES_AND_CONFIGURATION.md) §2.4). `altscreen-u2` paths remain listed as current/legacy source paths in the migration tables below.

> **Status: design only, 2026-11-03.** No on-unit files have been moved and no installed binary, Java class, legacy developer ZIP or release tag has been changed. This document defines a future *single three-firmware beta* migration contract, **not a current implemented filesystem layout**. Actual MMX paths are the authority until a target-tested migration is complete.

## Problem: a single functional subsystem has multiple path owners

The current source uses, among others:

| Logical owner | Current path / name | Representation and current owner |
| --- | --- | --- |
| CarPlay's 48 registry keys in 13 file groups | `/tmp/mibr-carplay111-*` or `/mnt/app/root/mibr-carplay111-*`; special `mibr-carplay-autodirect` basename | Volatile override before persistent before profile/compiled; `alt111-settings`, GEN2 and related scripts |
| Navigation composition | `/mnt/app/root/mibr-carplay111-nav.conf`, also legacy `mibr-carplay111-nav.*` | Registry group and/or individual legacy nav files; *not* automatically one reconciled store |
| Persistent navigation arrows | `/mnt/app/root/altscreen-u2/config/mibr-carplay-nav.conf`, `mibr-nav-source.conf`, etc. | Broker-owned revisioned `MIBR_*/1` files; Java and other readers share exact names |
| Other durable broker choices (13 switches in total) | `/mnt/app/root/altscreen-u2/config/mibr-*.conf` | Broker is sole writer; 13 individual values, including safe-area rectangles and expert mode |
| Standard menu | `/mnt/app/root/altscreen-u2/config/mibr-menu.conf` | Menu-specific CRC format, loaded from SD via existing script |
| Display scaling and platform defaults | `/mnt/app/root/altscreen-u2/config/display-scaling.conf`, `mibr-platform-defaults.conf` | Different reader/writer protocols; defaults are not user overrides |
| Persistent view-follow state | `/mnt/app/root/mibr-view/` | View script owner; `/tmp/mibr-view.*` is volatile state |
| Auto-Direct / keyframe policy markers | `/mnt/app/root/mibr-carplay-autodirect.enabled`, `/mnt/app/root/mibr-alt111-keyframe-policy.enabled` | File-presence booleans, not necessarily value-bearing `.conf` |
| Temporary video controls, locks and telemetry | `/tmp/mibr-*` | Transient markers, commands, status, locks and session generation values; other processes depend on exact names |
| Version and component metadata | `/mnt/app/root/mibr-kit/installed-version.properties`, `components.manifest` | Java version reader; installer write/verification not yet universally integrated |
| Deployed executables and maintenance | `/mnt/app/root/altscreen-u2/{bin,scripts,config,logs,backup}` | Existing MU1440 deployment root, **not** the entire current data root |

**Risks:** Moving one side of a cross-process file breaks readback, boot enablement or recovery. Some legacy marker names are not descriptive (and some `.disabled` markers reverse polarity); a user-controlled setting is distinct from a runtime status/lock. A grouped registry file may hold many fields; 48 logical keys **are not** 48 independent files. The QNX `/tmp` filesystem does not implement normal POSIX rename/fsync assumptions: retain the proven volatile transaction semantics.

## Proposed target layout: one project root, separated by ownership and lifespan

```text
/mnt/app/root/mibr/
  bin/                           executables, runtime libraries
  scripts/                       start, guard, service, installer, recovery helpers
  config/                        persistent configuration (never volatile)
    carplay/<group>.conf         registry-backed video/protocol settings (active only after the beta)
    cockpit/                     safe-{voll,wide,center}.conf (Broker CAS), scaling.conf
    navigation/                  phone arrow preferences and nav composition
    menu/                        layout.conf (CRC), language.conf
    platform/defaults.conf       installer-written firmware defaults, fallback only
    features/*.conf              explicit persistent enable/disable intent (positive, 0/1)
    vehicle/                     optional vehicle-data modes
  state/                         persistent operational state only, with owning writer
    boot/disabled                single kill switch (presence flag) plus boot failure counter
    cockpit/                     remembered view positions/resync selections
  version/                       installed product/build and per-component identity
    ownership/                   markers for installer-owned interventions
  backup/<migration-id>/         installer-owned migration/restore snapshots with hashes
  logs/                          bounded durable logs only when requested
/tmp/mibr-*                      volatile runtime IPC/overrides/locks/status (names unchanged)
```

This is a **namespace**, not permission to sweep arbitrary existing paths. Do not move `/mnt/app/eso` stock/OEM files or `/ifs` into the project root; firmware hooks and OEM resources have their own explicit install/rollback contract.

## Names and file-content conventions for new or migrated files

| Kind | Proposed naming rule | Meaning and examples |
| --- | --- | --- |
| Persisted configurable value(s) | short lowercase kebab-case basename, `.conf` extension, owner/category directory | e.g. `config/carplay/video.conf`, `config/navigation/arrows.conf`, `config/menu/layout.conf` |
| Per-profile defaults | `config/platform/defaults.conf` plus exact firmware-profile metadata in the package manifest | A firmware override **is not** a user setting; never silently replace user values |
| Persistent intentional feature toggle | positive key/value in `config/features/*.conf` (new code); legacy presence flags remain until migrated | `auto-direct=on`, `keyframe-recovery=on`; avoid mutually contradictory `.enabled`/`.disabled` flags |
| Persisted operational state | `state/<owner>/<purpose>.state` (format explicitly versioned) | e.g. `state/cockpit/view.state`, distinct from user intent |
| Installed identity | `version/installed-version.properties`, `version/components.manifest` | Same package identity as zip and read-only HMI Version page |
| Volatile telemetry | existing `/tmp/mibr-*.status` names until simultaneous writer/reader cutover | Status only, never used as a persistent source of truth |
| Volatile locks and process IDs | existing `/tmp/mibr-*.lock` / `*.pid` names until coordinated cutover | Do not put locks on `/mnt/app` or change QNX shmem semantics |
| Backups and migration receipts | `backup/<migration-id>/...` with source path, checksum and provenance manifest | Snapshot prior to any write, no blind overwrite |

The example target names are **logical desired names**, not existing parsers or aliases. Existing broker switch files have a revisioned magic header and compare-and-swap semantics; the menu has its own CRC format. Do **not** rewrite their file format into generic key/value merely to make the filename uniform. Distinct formats may keep descriptive `.conf` names with explicit schema metadata. No symlink-based migration, blind bulk rename, dual independently writable stores or silent fallback on invalid upper-layer content.

## Migration map (representative, not exhaustive)

Source paths in the left column are the **current/legacy** locations. Legacy source roots that fold into `mibr/`: `/mnt/app/root/altscreen-u2/`, `mibr-kit/`, `mibr-v3/`, `mibr-rgi/` and the `mibr-*.enabled` markers (including `mibr-cpvc.enabled`). Migration M1 (root move, single installer transaction, no runtime compat readers, reader and writer cut over together, kill switch first) is specified in [FIRMWARE_PROFILES_AND_CONFIGURATION.md](FIRMWARE_PROFILES_AND_CONFIGURATION.md) §2.4.

| Current source of truth | Proposed target namespace | Required code coordination |
| --- | --- | --- |
| `/mnt/app/root/mibr-carplay111-*` and companion `/tmp/mibr-carplay111-*` | `config/carplay/` and same logical volatile overrides | GEN2 C macros; settings CLI; 13 grouped registry basenames; generated HMI/C bindings; tests |
| `/mnt/app/root/altscreen-u2/config/mibr-nav-*.conf` | `config/navigation/` | Broker C switch definitions; Java `MibrDurableSwitch`; navigation renderer/reader; tests |
| `/mnt/app/root/altscreen-u2/config/mibr-menu.conf` | `config/menu/layout.conf` | Java `MibrMenuLayout`, menu SD loader, installer; preserve CRC and reload semantics |
| `/mnt/app/root/altscreen-u2/config/display-scaling.conf` | `config/cockpit/scaling.conf` | GEN2/Java/ MIBR broker reader and guarded persistent writer |
| `/mnt/app/root/altscreen-u2/config/mibr-platform-defaults.conf` | `config/platform/defaults.conf` | GEN2 C, Java, broker C; ensure per-firmware selector determined before applying defaults |
| `/mnt/app/root/mibr-view/` | `state/cockpit/` | `mibr-view.ksh`, physical key actions, broker, backup and rollback |
| `/mnt/app/root/mibr-carplay-autodirect.enabled` / `mibr-alt111-keyframe-policy.enabled` | `config/features/*.conf` after format-aware conversion | Installer, boot scripts, GEN2 and diagnostics must agree on positive toggle semantics |
| `/mnt/app/root/mibr-kit/` (receipts) | `version/`; `mibr-kit/disabled` → `state/boot/disabled` | Unified version manifest/receipt writer, HMI reader, upgrade/uninstall |
| `/mnt/app/root/mibr-v3/`, `mibr-rgi/`, `mibr-cpvc.enabled` | `bin/`, `scripts/`, `config/features/` | Broker, `boot.ksh`, watchdog, RGI wrapper; exact-path writer check must be switched together |
| `/tmp/mibr-*` | **keep original volatile paths during first migration** | Each IPC producer and consumer must be migrated together later if needed |

## A3 disposition of the 66 source candidates (proposal)

`tools/release/storage_destination_plan.py` assigns each candidate exactly one disposition, with a reason and, for MIGRATE, exactly one source writer. It is a proposal: `final_destination_reviewed` and `migration_authorized` stay `false`.

| Disposition | Count | Rows | Rule |
|---|---|---|---|
| MIGRATE | 18 | 12 broker CAS switches, display scaling, menu language, menu layout, platform defaults, two installer ownership receipts | One writer, all source readers known. Bytes are copied verbatim (magic, revision, CRC unchanged) in one cutover together with every reader. The receipts move only with the installer that replaces the current install/uninstall scripts. |
| KEEP_AT_LEGACY | 42 | All 13 CarPlay registry groups; CPVC profile; vehicle data/status mode; boot markers (Auto-Direct, D2, isoTX2, parity, CPVC enable, kit kill switch); legacy navigation files; bit26 pair; three backup directories and the isoTX2 stock preimage; the single-writer gate | No destination. The registry is kept because the native settings layer refuses persistent writes (durability is the CPVC profile replay). The Auto-Direct registry value and the Auto-Direct boot marker therefore no longer share a target basename. |
| EXCLUDE_NONCONFIG | 3 | Calibration clip, test-only rollback script, RGI payload directory | Payload or test reference, not state. |
| BLOCKED_INPUT | 3 | SD-log switch, the two version receipts | A claimed reader or the writer is not in source. |

Safe area keeps four stores but one user authority: the broker `safe-*` CAS files. The registry view-area group is a read path, platform defaults are an installer-written fallback, and the legacy `mibr-carplay111-safearea.conf` is rollback-only. `mibr-parity-statistics-enabled` and `mibr-parity-status-enabled` are value booleans whose absence means ON, never presence markers.

## Required rollout and CI gates

1. **Inventory first.** Generate a machine-readable complete map of *all* writes, reads, boot hooks, scripts, C string paths, Java constants, generated settings, configs, SD/USB entrypoints, firmware integration, external tools and uninstall operations. Mark each item's lifetime, writer/reader, file schema, default, precedence, backup/recovery and planned destination. This table is representative only.
2. **Agree on file identities and formats.** Per-option matrix from `settings/registry.json`, durable switch definitions and menu catalog. Reject duplicate logical IDs, contradictory positive/negative flags, ambiguous brand defaults, filename collisions and undocumented absolute paths.
3. **Migrate transactionally.** Preflight exact firmware and storage mode, snapshot and hash existing files on a safe medium, perform format-aware validation, stage new files with checksums and *one owner per setting*, update every consumer and boot hook at the same release boundary, then verify readback and post-reboot effect. Preserve rollback to original bytes and paths; fail closed on unknown/mixed states.
4. **Check QNX and persistence.** Actual MMX SSH startup is the execution contract; on unit, prove `/mnt/app` RW lease, RO restoration, interrupted-write/powerloss recovery, read/write permissions and no ambiguous old/new active copies. `/tmp` and SD behave differently and require separate tests.
5. **Enforce at release.** CI checks staged source/target file-reference inventory, exact files and schema, all three firmware profiles, generated defaults, version receipt and installed-menu readback. Verify the *actual* final multi-profile ZIP; host static checks alone are not target acceptance. Preserve user configuration on upgrade; an uninstall removes project-owned files only and restores modified OEM state from exact backups.

**Status:** Only the inventory/design is established in this document. The migration, full path discovery, automated validation, new QNX/Java builds, three-firmware beta ZIP and on-unit tests remain open and must not be described as implemented.
