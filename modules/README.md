# Repository components

The component pages follow the same functional boundaries as the modular
distribution: [CarPlay and video](carplay/), [broker and input](broker/),
[menu](menu/), [navigation](navigation/), and [platform profiles](profiles/).

These pages identify the canonical source, runtime, tools, artifacts and docs
for each component. The existing physical paths remain authoritative for builds
and links until a particular move and its dependent paths have been migrated.
The distribution layout itself is specified in the
[package contract](../docs/build/PACKAGE_LAYOUT.md).

The machine-readable [ownership and dependency index](module-index.json) records
current canonical paths, module build recipes and output names, plus migration
status. Its [host-only validation gate](../tools/check_module_index.py) checks
ownership conflicts and reports dependency-aware change impact; it does **not**
claim full reproducible builds or a qualified multi-target release.
