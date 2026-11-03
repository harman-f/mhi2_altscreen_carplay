# MU1440 menu, controller and route-guidance source

This source update brings the OEM-style menu model and editor, MIBR/3 controller,
independent display scaling, paired FPS/keyframe settings, demo GPS controls and
route-guidance helpers into one buildable source tree. It does not replace the
published vehicle-version binaries or installer ZIP.

## Menu and settings

`tools/menu-editor/` contains the function catalog and browser editor.
The saved menu format and loader limits are documented in
[MENU_FILE_FORMAT.md](../../tools/menu-editor/MENU_FILE_FORMAT.md).
The model and native controller use the canonical registry and generated catalogs.
The paired FPS choices are30FPS/20 frames per keyframe or60FPS/180; applying them
requires a Unit restart. The selected maximum does not prove the phone sends60FPS.

Main-display and cluster zoom and millimetre dimensions are separate controls.
Changing advertised physical dimensions can affect applications differently.
GPS-demo selection and route-guidance state are experimental; source or host-test
success is not evidence of phone-side GPS acceptance or an installed route-guidance
integration.

## Reproduction

- Native controller: `bash tools/build_mibr_control.sh host` for the host binary;
  `bash tools/build_mu1440_source.sh <output>` inside the pinned QNX toolchain for
  the common native stack. See [the source-build guide](MU1440_R57_SOURCE.md).
- Menu host contracts: `bash modules/menu/source/tests/run_view_model_test.sh` with a
  host JDK. The IBM J9 production compiler additionally requires locally supplied
  firmware API classes; those bytes are not part of this repository.
- Route Guidance: follow [its standalone build inputs](../../modules/navigation/source/README.md).
  It builds two artifacts with a locally supplied, hash-verified firmware library.
  The GPL TLV parser is pinned and attributed. The public CI cannot substitute a
  firmware library it does not redistribute.

The common source workflow separates immutable released-output hashes from
changed development source. Development outputs are checked for ARM ELF identity
and their actual build hashes are recorded; the released hashes are retained.
Neither path updates or approves the shipped vehicle package.

No Unit installation is performed by this source publication. The route-guidance
helper has no included launcher/installer/rollback kit; building its source must
not be presented as a complete installable feature.

## Menu metadata boundaries

The current function catalog, editable layout and authored expanded
`MibrMenuDefinition.java` preserve the cockpit-arrows, safe-area and version pages.
`generate_menu_catalog.py` handles the current function catalog. The older
`generate_catalog.py` also remains available for the finite registry-only projection
used by legacy model tests; its three-group menu output must not overwrite the
expanded production menu snapshot. The settings catalog itself is generated from
the common registry. The paired FPS/keyframe keys all retain their existing
`unit_reboot` apply metadata.
