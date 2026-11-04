# SD support files (supplemental only)

**This directory is NOT a copy of a complete M.I.B. SD card, a firmware image, or a standalone installer.** It identifies only project-owned extra files used when assembling installation and verification media.

- [`manifest.json`](manifest.json) maps the selected **last MU1440 developer package** helper binaries and installer entry scripts to their actual positions in the staged SD root. The entries are source references, not redundant copies.
- [`bin/`](bin/README.md) documents bundled, target-ABI-specific command-line helpers. The approved `sha256sum` and `tee` binaries remain versioned once under `artifacts/mu1440/`.
- [`scripts/`](scripts/README.md) documents QNX installer scripts. Their maintained source remains under `deployment/` and `runtime/`; the release job copies exactly those bytes.
- Remaining runtime scripts, firmware-specific modules, menu files and configuration are assembled by the release recipe and audited separately. Nothing in `sd/` implies that the generated package is complete or vehicle-qualified.

**Pipeline contract:** `python3 tools/release/sd_support.py --self-test --source-check` validates inventory ownership and pinned helper hashes. After staging with `tools/prepare_mu1440_sd.sh`, `python3 tools/release/sd_support.py --stage-root <staged-root>` verifies every listed source/target pair byte for byte. The existing QNX shell scanner checks all delivered shell scripts, and the archive validator reopens the final ZIP.

Do not copy OEM firmware files, third-party M.I.B. SD content or unspecified utility binaries into this directory. Additional tools (for example `sed`) must first be proven compatible with the QNX target architecture and their options, be included with provenance/hash, and be resolved through a verified installation `PATH` or an explicit packaged path. The host's `PATH` is not evidence of availability on MMX/RCC.

This manifest currently covers the **legacy MU1440 staged package only**. The planned three-firmware package requires its own exact profile payloads and release gate; this index is not permission to publish a beta.
