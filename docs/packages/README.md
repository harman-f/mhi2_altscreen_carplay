# Packages, installation and release status

MIB Runtime has **one shared codebase** and **three exact firmware profiles**, but there are two different packaging generations. **Do not confuse published source, a CI artifact, a validated ZIP and a vehicle-qualified release.**

## Which package?

| Line | Targets | Availability and scope | Instructions |
| --- | --- | --- | --- |
| **Frozen MU1440 developer reference** | Exact Škoda MU1440 P4526 / AID10-class reference | Seven-payload historical developer package; pinned bytes and limited observed capability. No newer Java/menu/three-profile promise | [Frozen release inventory](../../release/CURRENT.md), [legacy developer procedure](../INSTALLATION.md) |
| **Modular MIB Runtime beta** | Škoda MU1440 P4526; SEAT MU1409 P4708; SEAT MU1447 P4709 | Shared `common/` plus all three `profiles/`; installer, selector and assembler are in source. **A complete validated final beta ZIP is not yet demonstrated by this page.** | [Package contract](../build/PACKAGE_LAYOUT.md), [profile matrix](../testing/MULTI_PROFILE_TESTING.md) |

The frozen developer release is **not replaced** merely because newer source was merged. Its tag, bytes and hashes stay as published. The new MIB Runtime installer must not silently be used with the old seven-payload bundle.

## New modular package: what the tools provide

- `tools/release/build_modular.py` assembles a deterministic `MIBR-CarPlay/` ZIP using separately supplied native build outputs and per-profile compiled J9 menu JARs.
- `tools/validate_modular_package.py` verifies the **actual assembled ZIP**, common/profile layout and manifests. A self-test alone is not final artifact validation.
- `installer/select-profile.ksh` matches the original `/ifs/lsd.jxe` hash uniquely and cross-checks the firmware train. An unknown/ambiguous identity is a hard stop.
- `installer/mibr-install.ksh` exposes read-only check, apply, uninstall and rollback for a matching package. It uses backups, receipts and the canonical on-unit root `/mnt/app/root/mibr/`. Host tests and CI do not replace actual QNX/vehicle recovery acceptance.
- New profile-specific Java builds depend on exact, *externally supplied* firmware API/J9/OEM inputs. These must not be redistributed as part of public project source.

The release workflow on `main` defaults to the three hash-pinned, class-major-46 profile menu JARs; source changes invalidate this shortcut and require an independently reviewed local J9 rebuild. The separate `ghcr.io/harman-f/mhi2-qnx65-armv7` package is the immutable QNX **compiler image**, not an app installer. The end-to-end beta still needs a protected runner and private navigation inputs; the J9 extender can be independently supplied as a pinned local artifact or built on that runner; the workflow does not publish a permanent GitHub Release. [Build and reuse procedure](../build/MULTIPROFILE_RELEASE.md).

The ordinary beta package should include all three profiles; a deliberately flagged single-profile test build is not the common beta distribution. Reconstructed JAR hashes and selector fingerprints have different meanings.

## Status and gates

1. **SOURCE:** public modules and firmware-profile source available.
2. **BUILD / HOST:** CI tests and native source builds evaluated by exact revision; external J9 build is separately evidenced.
3. **PACKAGE:** all required binaries/JARs, manifests, installer and source inventory present; final complete ZIP validator passes.
4. **UNIT:** target preflight, backup, startup, STOCK handback, boot guard, settings/readback, reboot and rollback observed on exact unit.
5. **RELEASE:** package published with accurate tested-target and evidence labels. **No source or CI PASS automatically satisfies level 4 or 5.**

When a necessary J9/firmware input is missing, record `MISSING_INPUT` or `incomplete`; do not substitute a Škoda binary for SEAT. [Firmware-profile schema](../architecture/FIRMWARE_PROFILES_AND_CONFIGURATION.md) · [Compatibility](../testing/COMPATIBILITY_MATRIX.md) · [Full features and evidence](../status/FEATURE_STATUS.md).

## Finding the right guide

For a frozen MU1440 package, use [the historical installation document](../INSTALLATION.md). For **a future complete modular package**, follow its own generated `INSTALLATION-README.md`, `package.json` and verified scripts. Never install from this overview alone.

[Developer toolchain](../build/QNX_TOOLCHAIN_IMAGE.md) · [Java and navigation source build](../build/MU1440_MENU_RGI_SOURCE.md) · [Release/source ownership](../status/PUBLISHED_SOURCE_COVERAGE.md) · [Security and testing](../../SECURITY.md).
