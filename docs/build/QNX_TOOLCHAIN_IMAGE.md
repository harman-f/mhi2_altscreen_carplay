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

## Current CI implementation (2026-11-04)

The five public native-build workflows (MU1440 source, GEN2, direct-TS remux, keypanel and support tools) now share `tools/ci_qnx65_image.sh`. The script has two **explicit** modes:

- **archived-pinned**: when the repository Actions variable `QNX65_VERIFIED_IMAGE` is present, it must be an immutable GHCR `image@sha256:64hex` reference. The runner pulls and checks that digest, validates the linux/amd64 platform and GCC 4.9 cross-compiler, then tags it locally for the existing build commands. Any failed pull or check **stops the job**; there is no automatic network/source fallback.
- **legacy-rebuild**: until the registry alias/access has been configured, each workflow explicitly sets `QNX65_LEGACY_REBUILD_ALLOWED=1` and emits a visible warning before invoking the existing pinned source-build helper. This temporary bootstrap preserves build availability but **still downloads/rebuilds GCC** and is not the final performance improvement. Without that explicit flag and without an image reference, the selector fails closed.

To activate the archived image without publishing a separate development account name in source:

1. In the public repository, open **Settings → Secrets and variables → Actions → Variables** and create `QNX65_VERIFIED_IMAGE`. Supply an **approved, pullable, digest-qualified GHCR image reference** confirmed with the archive owner. Do not supply a mutable `:latest` or `:4.9` tag.
2. Ensure that GitHub-hosted runners can pull it. The selector currently uses Docker's existing read access: a publicly readable image works without login, but a private package needs an independently configured and reviewed read-only authentication step. Do not add a credential to the repository.
3. Verify that the MU1440, GEN2, remux, keypanel and support-tool CI jobs all report `QNX_IMAGE_READY=PASS mode=archived-pinned`; inspect each attached `QNX_TOOLCHAIN_PROVENANCE.txt`, output SHA-256, QNX ARM ELF identity and tests.
4. After real archived-mode CI success, delete the temporary `QNX65_LEGACY_REBUILD_ALLOWED=1` allowance from the five jobs. Retain `tools/build_qnx65_image.sh` as a separately invoked recovery helper.

The archived compiler may differ from the more recent source-rebuilt image because the bootstrap Dockerfile and Debian snapshot differ. **No byte-for-byte reproducibility or vehicle compatibility is inferred.** Changes in output hashes require review before anything enters a release.

Every native job now attaches a provenance text file recording the selected mode, actual local Docker image ID, compiler version, source revision and declared upstream toolchain recipe. Archived mode additionally records the checked manifest digest. This is supplemental evidence, not a replacement for the existing `MODULE_BUILD_LINEAGE.json` receipt, which still lacks a verified image-digest field. Only a later lineage-tool change may integrate the real Docker identity into a validated release receipt.

### Reproducibility/compatibility gate — still required for archived mode

The previously verified source-build path is not equivalent evidence for the archived image. Confirm the compiler/sysroot and required `qcc` and readelf tools, run full native build/host tests, compare ABI/ELF headers and output SHA-256 against the established baseline, and review any differences. Keep QNX compiler-verified binaries separate from frozen vehicle-tested artifacts until their own acceptance. The image-selection helper does not install on a unit, alter persistent storage, or qualify a new profile.

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
