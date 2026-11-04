# Canonical QNX 6.5 ARMv7 toolchain image and release provenance

This is the public contract for selecting the **host-side cross-compiler environment** used to produce native MHI2/QNX ARMv7 binaries. It does **not** authorize a device installation, a firmware patch, or a public release.

## Archived compiler environment

The project has an existing, prebuilt GCC 4.9 / QNX 6.5 / ARMv7 Docker image archived in GitHub Container Registry. Its archived **manifest digest** is:

```text
sha256:19b5fb1d4559264a844080b6e381837655d4dcca50151cce3ff0ac509e4f3393
```

The original archive belongs to the separate development build infrastructure. The public project must first establish and verify an approved, accessible registry reference before CI can switch to it. Do not guess a registry path, treat this digest alone as a pullable image reference, or assume a mirrored image necessarily retains the same manifest digest. Use a fully qualified `registry/image@sha256:<verified-manifest>` value for actual builds; keep internal registry ownership details outside this public repository.

Known build-source provenance for that archived image:

| Property | Recorded value |
| --- | --- |
| Upstream toolchain | `https://github.com/luka-dev/qnx65-armv7-toolchain.git` |
| Source commit | `56a66557245af14077678cd28a83ce3a337d9e2d` |
| Upstream Dockerfile SHA-256 | `9a867a7ae70f2c0222a241b80232856526ccec0db2cfe013f8991ca31c74bcb1` |
| Archive/preflight Dockerfile SHA-256 | `e5f15f5b69fcfd764be89f9804a487a1a05541de16a86c832955d46bc375c171` |
| Archived Debian snapshot | `20260608T060000Z` |
| Docker build | `--platform linux/amd64 --target base-env --build-arg BASE=base-4.9` |
| Expected native C compiler command | `arm-unknown-nto-qnx6.5.0eabi-gcc` |

The archived toolchain image is a **compiler/build environment**, not an application firmware image or a distributable installer. GCC 4.9.4 source downloads are unnecessary when the verified archived image is being used. Project C/C++ sources still need recompiling after changes. The OEM Java/J9 path is separate and requires exact firmware-specific dependencies.

## Current public compiler image (Harman-F)

The independent [project-owned archive workflow](../../.github/workflows/archive-qnx65-image.yml)
published a GCC 4.9.4 / QNX 6.5 / ARMv7 image successfully in
[run 41805123089](https://github.com/harman-f/mhi2_altscreen_carplay/actions/runs/41805123089).
The registry-authoritative reference is:

```text
ghcr.io/harman-f/mhi2-qnx65-armv7@sha256:20d7d2bb16d6718d204afc7714b0e73227651935a9981a8bd2e2087cef48dd0d
```

All five native build workflows consume this **exact** image using
[`tools/qnx65-image.lock`](../../tools/qnx65-image.lock) and the common
[`tools/ci_qnx65_image.sh`](../../tools/ci_qnx65_image.sh) selector.
The lockfile lives in the public repository with source/build recipes:
there is no separate dependency on the private Research account or on
a manually configured repository Actions variable.

CI authenticates to the **same repository's** GHCR package using a scoped
`GITHUB_TOKEN` with `packages: read`. It checks the complete manifest
digest, `linux/amd64` platform, GCC 4.9 compiler and QNX readelf/qcc tools.
Missing access, a mismatching override, wrong image/digest or an absent
compiler fails closed. A normal build does **not** rebuild or download GCC.
`tools/build_qnx65_image.sh` remains an explicit, independent
disaster-recovery/reprovisioning command.

Each native build uploads `QNX_TOOLCHAIN_PROVENANCE.txt` with the
verified image reference and manifest digest, compiler version, image ID,
source revision and explicit `vehicle_qualified=false`. A source build
passing CI **does not authorize** replacing the vehicle-tested legacy
binaries or publishing a modular release. Review ELF/ABI symbols and
SHA-256 differences versus previous builds.

The older Research image (`sha256:19b5fb...`) remains available for
history; it is not byte-for-byte interchangeable with this separately
rebuilt and published image. See the
[Harman-F archive runbook](HARMAN_F_TOOLCHAIN_ARCHIVE.md).

## Release pipeline requirements

The current `.github/workflows/release-mu1440-aid10.yml` is a **fail-closed release-readiness / legacy ZIP integrity audit**. It uses existing pinned binaries, does not itself cross-compile the product, intentionally rejects the legacy archive as an R3 package, and does not publish a GitHub Release or distributable ZIP. See [release readiness](../../tools/release/README.md) and the [current release boundary](../../release/CURRENT.md).

For a future end-to-end multi-profile build/release pipeline:

- Separate **compiler-image selection and verification**, **source compilation**, **binary lineage**, **package staging**, **final modular ZIP validation**, and **explicit publication** into independently gated stages.
- Pin native compilation to the immutable image digest. Record `toolchain_image_ref`, `toolchain_image_digest`, compiler version, source commit, effective Dockerfile/base-image identity, target profile, compile inputs/options and per-output SHA-256 in the build/lineage evidence. Verify the digest against the image actually used, rather than copying a documentation constant into an untested receipt.
- The current `tools/emit_module_build_lineage.py` receipt records source/target/output hashes and a *declared* upstream toolchain commit and Dockerfile SHA-256; **it does not currently attest the actual image digest or a bit-reproducible build**. Extend and test that receipt before treating it as sufficient release provenance.
- Do not promote source-build CI outputs merely because they compile. Keep frozen, vehicle-evidenced binaries distinct from unqualified new binaries, including outputs marked `NOT-INSTALL-READY`.
- For a multi-profile release, require exact firmware fingerprints, OEM/J9 adapter build coverage, three-profile inclusion, shell compatibility, complete source/package inventories, recovery/rollback evidence, integrity checks of the **final** ZIP and appropriate target acceptance. Missing inputs block publication; never insert placeholders.
- Never rewrite published tags, old GitHub Releases or historical binary hashes. No publication, source migration, or on-unit installation is authorized by a green compiler-image check.

This is a **host/CI-only** contract: all Docker and GNU hash commands above run on the build machine, not the QNX head unit.
