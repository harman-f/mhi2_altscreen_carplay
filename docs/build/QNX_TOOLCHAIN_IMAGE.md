# Canonical QNX 6.5 ARMv7 toolchain image and release provenance

This is the public contract for selecting the **host-side cross-compiler environment** used to produce native MHI2/QNX ARMv7 binaries. It does **not** authorize a device installation, a firmware patch, or a public release.

## Archived compiler environment

The project has an existing, prebuilt GCC 4.9 / QNX 6.5 / ARMv7 Docker image in GitHub Container Registry. Use its immutable digest, not a floating tag:

```text
ghcr.io/canetlotw/mib-qnx65-armv7@sha256:19b5fb1d4559264a844080b6e381837655d4dcca50151cce3ff0ac509e4f3393
```

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

## Present CI implementation versus intended consumption

As of 2026-11-04, the public workflows still invoke `tools/build_qnx65_image.sh` to clone the pinned upstream toolchain and build a **new** local image named `mhi2-qnx65-armv7-public:4.9`. In particular, `.github/workflows/build-mu1440-source.yml` and `.github/workflows/build-altscreen111-gen2.yml` do so. Other native workflows (`build-direct-ts-remux.yml`, `build-keypanel-native.yml`, `build-support-tools.yml`) also obtain/build the pinned toolchain separately. A recent download fallback made that legacy rebuild path more reliable; it did **not** switch CI to the archived registry image.

**Desired default for future CI changes:** pull the canonical digest once per relevant build job, verify that the exact image is available, then execute the existing native build in that image. Keep `tools/build_qnx65_image.sh` as an explicit disaster-recovery/reprovisioning command, not an automatic silent fallback. Do not delete or overwrite the archived image or its provenance.

Example for a Linux GitHub runner or developer machine with Docker and read permission to the container package:

```bash
IMAGE='ghcr.io/canetlotw/mib-qnx65-armv7@sha256:19b5fb1d4559264a844080b6e381837655d4dcca50151cce3ff0ac509e4f3393'
docker pull "$IMAGE"
docker image inspect "$IMAGE" >/dev/null
docker run --rm --platform linux/amd64 "$IMAGE" arm-unknown-nto-qnx6.5.0eabi-gcc --version
```

If access to the registry is restricted, configure read-only GHCR authorization for CI; a pull failure is a **failed preflight**, not permission to replace the digest with `:latest`, build from an unverified network source, or skip the identity check. Do not put registry credentials in a source tree or release artifact.

### Migration/compatibility gate — not yet executed

Although the archived image and currently rebuilt image share an upstream toolchain commit, their Dockerfile/preflight and Debian snapshot provenance differ. **Do not assume byte-identical toolchain contents or outputs.** Before switching a workflow, verify on the actual CI runner:

1. The immutable digest resolves and the expected QNX ARMv7 cross-compiler runs; record `--version` and relevant tool locations.
2. Compare compiler/linker flags, dependencies, ARM/QNX ELF headers and required symbols against the current job; run the existing host and native build tests.
3. Compare output SHA-256 with the prior recipe when reproducibility is expected. Record and review legitimate differences rather than silently replacing frozen vehicle-evidenced binary identities.
4. Keep the exact image digest and build source revision in the build metadata; verify the generated output inventory and module receipts.
5. Check access and behavior for all affected jobs before retiring redundant toolchain-build steps.

This document records the intended selection policy and work required; it is **not** evidence that a workflow was migrated, that outputs are bit-reproducible, or that the archived image was smoke-tested in the current PR.

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
