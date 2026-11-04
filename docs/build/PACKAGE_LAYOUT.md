# Multi profile package layout

This document specifies the single **three-target beta** distribution: all three firmware profiles are mandatory, with common software tests and final combined system testing pending. The supported profile identifiers in this layout are `skoda-mu1440-p4526`, `seat-mu1409-p4708`, and `seat-mu1447-p4709`. The package layout does not change the installation paths used by the target system. Per-firmware Java/J9 adapter fixes are expected during beta without changing common module ownership.

```text
package/
  installer/                 install, check, and uninstall entrypoints
  common/
    carplay/{bin,scripts,config}/
    broker/{bin,scripts,config}/
    menu/
      bin/                    shared support JARs
      config/                 deployed standard mibr-menu.conf
      scripts/                shared menu loader
      icons/                  brand-neutral scrollbar assets only
    navigation/{bin,scripts,config}/
    config/                  shared defaults and configuration
  profiles/
    skoda-mu1440-p4526/{hmi,icons,display,input,integration}/
    seat-mu1409-p4708/{hmi,icons,display,input,integration}/
    seat-mu1447-p4709/{hmi,icons,display,input,integration}/
  tools/
    menu-editor/              editor, present once
    ...                       host-side packaging and validation
  source/
    hmi/                      Java HMI source, present once
    SOURCE_MANIFEST.json      independent source inventory and hashes
  INSTALLATION-README.md     concise defaults, selected profile, install/recovery instructions
  docs/
    configuration/DEFAULT_CONFIGURATION_MATRIX.md
                              complete audited settings/defaults matrix
    ...                       build, use, and support documentation
  package.json               runtime package manifest
  PACKAGE.sha256             runtime package hashes
```

There is one `profiles/` directory. Shared implementations have one canonical owner under `common/`; profile directories hold target-specific HMI, icons, display, input, and integration data or outputs. Runtime binaries live in each `common/<module>/bin/`, with module scripts and configuration under `scripts/` and `config/`. The deployed standard menu is `common/menu/config/mibr-menu.conf`, its loader is under `common/menu/scripts/`, and support JARs are under `common/menu/bin/`. The menu editor exists once under `tools/menu-editor/`, and Java HMI source exists once under `source/hmi/`. Skoda-specific icons live in the Skoda profile; `common/menu/icons/` holds brand-neutral scrollbar assets only. A profile may contain a compiled target artifact when requirements produce distinct outputs, tied to its shared source and build recipe. Album-art handling is not included in this package layout.

Profile values describe differences that the implementation actually supports. A declarative mapping does not make hard-coded binary behavior configurable. Unsupported variation requires a profile-specific integration or build and must not be represented as a fictional runtime setting.

The beta ZIP **must** ship `INSTALLATION-README.md` at its root and `docs/configuration/DEFAULT_CONFIGURATION_MATRIX.md`. The README must summarize the *effective packaged default* for CarPlay video, phone-route arrows, arrow source/placement, view/presentation, navigation composition, Auto-Direct, D2, diagnostics, and menu brand, including any per-firmware overrides or an explicit `not yet implemented` status. The full matrix inventories all 48 CarPlay registry settings, all 13 durable broker switches and menu-only entries. Release validation must compare these claims against the **actual staged** menu/config/installer artifacts and reject mismatches. Descriptions of defaults are not proof of an active unit state or completed vehicle tests. The current `release-mu1440-aid10.yml` ZIP is a CI-internal legacy compatibility audit, not a completed modular beta ZIP.

Runtime and source contents ship in the same ZIP and have separate manifests. The runtime manifest lists the exact runtime files and hashes. `source/SOURCE_MANIFEST.json` independently lists and hashes source files; it is included in the ZIP, not a pointer to a separate mandatory download. The source inventory identifies project-owned inputs, documents excluded OEM, operating-system, JDK, or other third-party dependencies, and states source and build coverage gaps. Partial source coverage must not be described as full reproducibility.

If profile selection uses the original firmware executable, selection is based on an exact SHA-256 match to one profile. Unknown or ambiguous hashes stop before installation. Names, partial hashes, and inferred model labels are not selectors. Root convenience wrappers may delegate to the canonical installer entrypoints, but do not duplicate their behavior.

**Single-profile scope (developer subset).** The three-profile requirement above is the default and is enforced whenever `package.json` has no `scope` key. A package may instead declare `"scope": "single-profile"` together with `"profiles": ["<one known profile id>"]` (for example `skoda-mu1440-p4526`); the gate then requires exactly that profile in `installer/config/profiles.list` and in `profiles/`, and rejects unknown profile ids or any other `scope` value. Whole-file OEM variants are never published. Each `profiles/<id>/integration/variants.list` row is `target stock_sha256 patched_sha256 transform_file transform_sha256 [mode]`: the transform file (`.awk`, `.sed`, `.block`, `.patch`, `.sh` or `.ksh`) lives under `profiles/<id>/integration/`, its SHA-256 is checked against `transform_sha256`, and the installer applies it only to an input matching `stock_sha256`, expecting `patched_sha256`. A variant file that is named like an OEM payload or whose bytes equal the stock or patched hash is rejected.

Package validation checks manifest coverage and hashes, known profile identifiers, unique fail-closed profile selection, and the source/build relationship for profile artifacts. Run `python tools/validate_modular_package.py --self-test <package.zip>` before distributing an archive. The distribution includes this host gate under `tools/package/`. The CI self-test covers rejection of legacy/unsafe layouts; validating the actual final ZIP is a separate required step. Host checks describe packaging correctness only; they do not by themselves establish target compatibility or vehicle readiness.
