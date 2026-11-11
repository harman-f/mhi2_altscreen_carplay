# Repository components

The component pages follow the same functional boundaries as the modular
distribution: [CarPlay and video](carplay/), [broker and input](broker/),
[menu](menu/), [navigation](navigation/), [media](media/),
[phone](phone/), [audio](audio/),
and [platform profiles](profiles/).

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

**P1/P2 source stage:** Media and Phone have generation-aware host-tested ingress, attributed OSS reference excerpts and three disabled exact-firmware bindings. No Java/QNX integration or installed runtime is claimed.

**P6 source stage:** Audio has same-owner focus and stock-voice safeguards, exact ABI gates for all three targets, GPLv3 research excerpts and host tests; no DSP/audio driver is built or installed.
