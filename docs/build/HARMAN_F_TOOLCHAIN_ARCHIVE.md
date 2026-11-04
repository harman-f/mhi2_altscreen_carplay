# harman-f: QNX 6.5 ARMv7 toolchain archive in GHCR

The `harman-f/mhi2_altscreen_carplay` repository owns its public **build recipes and
source code**, while GitHub Container Registry (GHCR) stores the **large OCI image**.
Do **not** commit a Docker `.tar` archive or expanded toolchain into Git.

## Project-owned package

- Package namespace: `ghcr.io/harman-f/mhi2-qnx65-armv7`.
- Publisher: [`archive-qnx65-image.yml`](../../.github/workflows/archive-qnx65-image.yml),
  using this repository's tracked [`build_qnx65_image.sh`](../../tools/build_qnx65_image.sh).
- Source version: `luka-dev/qnx65-armv7-toolchain@56a66557245af14077678cd28a83ce3a337d9e2d`.
- Exact upstream Dockerfile SHA-256: `9a867a7ae70f2c0222a241b80232856526ccec0db2cfe013f8991ca31c74bcb1`.
- Target: QNX 6.5 / ARMv7 / GCC 4.9.4, container platform `linux/amd64`.
- Immutable provenance: the **registry-generated** `sha256:` digest recorded in the
  successful Actions run's `registry-ref.txt` and `archive-provenance.json`.
- No container image has been proved published by merely adding the workflow.
  The first eligible `main` push or an explicit workflow dispatch must complete
  successfully before the GHCR reference can be used.

The previously archived Research-side image is a **different package with
a recorded historic digest**. The new package is rebuilt independently from
the pinned public recipe, with its own verified digest. Although it uses the
same upstream compiler source revision, the Debian snapshot and local bootstrap
recipe may differ. Treat output equivalence as **unproven** until validated.

## Publishing procedure

1. Merge the archive workflow only after publication/security checks pass.
   A new run starts automatically when the workflow first lands on `main`.
   Repeat deliberately with GitHub Actions → *Archive QNX 6.5 ARMv7 toolchain
   in harman-f GHCR* → *Run workflow*.
2. The job constructs the toolchain once, checks GCC 4.9.4, qcc, ARM ELF and
   `linux/amd64`, attaches the public source-label, logs in using
   `GITHUB_TOKEN` with `packages: write` and pushes to **its own** namespace.
3. Verify the registry-returned full `ghcr.io/harman-f/...@sha256:...` value
   in the archived build receipt; **tags are not trustworthy build pins**.
4. In GitHub's package settings, confirm the package is accessible to this
   repository's Actions. If the package must be publicly pullable, change its
   visibility to public using an authorized account; publishing from a public
   GitHub repository does not guarantee public package visibility.
5. In the repository's **Settings → Secrets and variables → Actions → Variables**,
   set `QNX65_VERIFIED_IMAGE` to the verified **harman-f GHCR digest-qualified
   reference**, not an alias tag. A normal repository variable is sufficient for
   an image name; do not store tokens in plaintext or commit registry credentials.
6. Run the native-build PR and compare ARM ELF headers, dynamic symbols, tests
   and binary hashes to the previous baseline. Only then disable the explicit
   legacy compiler-rebuild transition toggle.

If the package push or cross-compilation fails, do **not** silently repoint
CI to a Research package, use a `:latest` alias, or publish a new application
release. Recover the owning package or rerun the **separate archive workflow**.

## Build/release separation

- Compiler package: a **host build dependency**, never QNX headunit firmware.
- Native source build: `MU1440`, GEN2, keypanel, direct-TS and support tools
  should use one verified compiler reference and retain a per-output SHA receipt.
- Release readiness: needs a complete module/target identity and verified
  final assembled installer; success here alone is **not a vehicle acceptance**
  and does not authorize any on-unit installation or product publication.
- Existing historical/tagged vehicle-evidenced binaries remain unchanged.

See [the general QNX image contract](QNX_TOOLCHAIN_IMAGE.md) and
[the release gates](../../tools/release/README.md).
