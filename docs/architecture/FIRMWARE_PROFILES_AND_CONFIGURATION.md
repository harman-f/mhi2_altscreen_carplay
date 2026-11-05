# Firmware profiles and configuration

This document defines how the MIB Runtime represents firmware differences, selects a compatible profile, stores configuration, and packages runtime files. A repository layout change does not by itself change paths or behavior on a vehicle.

## Architecture layers

The system has three distinct layers:

1. **Source modules** own shared runtime code, profile data, generators, build tools, and tests.
2. **Distribution packages** contain shared files under `common/`, per-firmware files under `profiles/<id>/`, and a separately inventoried `source/` section. The package layout and its validation rules are defined in [PACKAGE_LAYOUT.md](../build/PACKAGE_LAYOUT.md).
3. **Installed runtime** resides under `/mnt/app/root/mibr/`. Paths in source or a package are not evidence that a vehicle has been migrated to those paths.

Shared CarPlay, Broker, menu, and navigation behavior belongs in their common modules. Profile-specific behavior belongs in `modules/profiles/<id>/` as data, integration transforms, and small adapters for firmware-specific APIs. Keep one canonical copy of shared code.

## Firmware profiles and selection

Each profile is described by `profile.json`. It identifies the profile and firmware family, the SHA-256 fingerprint of `/ifs/lsd.jxe`, profile evidence, and any firmware-specific menu adapter and API input fingerprint.

The installer selects a profile only when the observed `/ifs/lsd.jxe` SHA-256 matches exactly one enabled profile. The firmware train string is a required plausibility check; it does not select the profile. Missing, unknown, ambiguous, or contradictory values stop installation before any write. Do not infer a profile from a filename, file size, or train string alone.

Enable automatic installation only for profiles whose selector evidence meets the profile schema's requirements. Unverified or unsupported inputs remain disabled. Record evidence accurately and distinguish source/build checks, package validation, host tests, and vehicle results.

## Profile boundaries

Profile data may describe display geometry, OEM identifiers, key-map deviations, icons, and hash-bound transformations of stock configuration. The shared menu uses a common Java core with profile adapters for OEM API differences. An adapter should expose only the variation points needed by the shared core; avoid copying complete shared classes into each profile.

Build each adapter against its declared API input. The build must verify that the supplied API JAR matches the profile's expected hash and must use the target runtime's supported Java class format. The target OEM inputs and generated output are external build inputs: inventory them and their provenance, and do not package proprietary OEM files as source or payload.

Integration changes to stock files are transformations, not copies of OEM files. A transform applies only to a known stock hash and must produce the expected result hash. Unknown input or an unexpected result is a hard failure. Packages must not contain OEM source or binary payloads.

## Unified configuration

`settings/registry.json` is the definition source for settings and Broker switches. It describes each key's type, allowed values, defaults, application behavior, and storage ownership. Generators produce language-specific bindings and catalogs; generated outputs must be reproducible and checked for consistency in CI.

Configuration precedence, from lowest to highest, is:

1. Compiled defaults.
2. Firmware-profile defaults for values that differ by profile.
3. Installer-managed platform defaults.
4. Persistent user values, written by the owning Broker or component.
5. Volatile runtime state, such as IPC, lock, and status files under `/tmp`.

A lower-priority layer must not overwrite a value owned by a higher-priority layer. Firmware profile means the detected hardware/software variant; preset means a user-selected collection of compiled defaults. Keep those concepts distinct.

Every persistent storage group has one physical path, one format, and one writer. Multiple keys may share a group file. The registry and its generated path map are authoritative for project-owned paths. OEM and stock paths, and legacy paths read only during migration, must be explicitly inventoried. Do not add new project state at legacy locations.

Writers must preserve each format's contract, including CAS revisions, CRCs, binary layouts, and presence-flag semantics. Convert inverted switches or change file formats only when their readers and writers change together and migration is defined.

## Installed storage and migration

The project-owned runtime root is `/mnt/app/root/mibr/`:

```text
/mnt/app/root/mibr/
  bin/                         runtime binaries and libraries
  scripts/                     startup, guard, service, and recovery scripts
  config/                      persistent configuration, grouped by owner
  state/boot/disabled          boot kill switch
  state/                       other persistent runtime state
  version/                     package receipts and ownership records
  backup/<migration-id>/       original files needed for recovery
  logs/                        bounded runtime logs
```

OEM locations such as `/ifs` and `/mnt/app/eso` remain outside the project root. Integrations modify them only through validated, reversible changes with backups and ownership records.

Root migration is a location change, not a format conversion. Preserve user data and prior disabled state. Before changing files, identify the profile, acquire the required lock and writable lease, check capacity, and create verifiable backups. Stage and verify copied files before switching consumers. Keep the prior layout available as a rollback source until acceptance. Uninstall and rollback restore only changes recorded as owned by the installer; never overwrite a file that has changed independently.

The kill switch is `/mnt/app/root/mibr/state/boot/disabled`. Migration must preserve a previously disabled state, and an interrupted transaction must fail safely without activating runtime components. Legacy kill-switch paths may be read as migration inputs but must not remain a second runtime authority.

## Package and evidence rules

A multi-profile package includes the shared module tree once and a symmetric profile tree for each supported profile. A single-profile package is permitted only when its scope is declared and its profile is known. Every payload and transform must be covered by package manifests and hash validation; reject unlisted, missing, symlinked, or unexpected files.

Keep these evidence states separate: source build, package validation, host tests, unit tests, and vehicle approval. Passing a host build or package validator does not establish vehicle compatibility or installation approval. Document unsupported profiles and missing build inputs directly in public product documentation without including private provenance or internal work tracking.
