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
- **Published and verified:** [archive run 41805123089](https://github.com/harman-f/mhi2_altscreen_carplay/actions/runs/41805123089)
  completed successfully; exact immutable registry identity:
  `ghcr.io/harman-f/mhi2-qnx65-armv7@sha256:20d7d2bb16d6718d204afc7714b0e73227651935a9981a8bd2e2087cef48dd0d`. See `tools/qnx65-image.lock` for the current public build pin.

The previously archived Research-side image is a **different package with
a recorded historic digest**. The new package is rebuilt independently from
the pinned public recipe, with its own verified digest. Although it uses the
same upstream compiler source revision, the Debian snapshot and local bootstrap
recipe may differ. Treat output equivalence as **unproven** until validated.

## Publishing procedure

1. The one-time publisher is already on `main` and its initial image build passed.
   Re-run the archive workflow **only** to intentionally create a new image
   identity; do not overwrite an existing version pin as part of ordinary
   native source CI.
2. The job constructs the toolchain once, checks GCC 4.9.4, qcc, ARM ELF and
   `linux/amd64`, attaches the public source-label, logs in using
   `GITHUB_TOKEN` with `packages: write` and pushes to **its own** namespace.
3. Verify the registry-returned full `ghcr.io/harman-f/...@sha256:...` value
   in the archived build receipt; **tags are not trustworthy build pins**.
4. In GitHub's package settings, confirm the package is accessible to this
   repository's Actions. If the package must be publicly pullable, change its
   visibility to public using an authorized account; publishing from a public
   GitHub repository does not guarantee public package visibility.
5. The public `tools/qnx65-image.lock` is the **single checked-in source
   of truth** for the exact `ghcr.io/harman-f/...@sha256:...` reference.
   Updating it requires a reviewed source commit. No Actions image variable,
   mutable Docker tag, private Research registry or plaintext token is needed.
   The five native workflows request `packages: read` and use the owning
   repository's scoped `GITHUB_TOKEN` to pull the package.
6. [CI migration PR #126](https://github.com/harman-f/mhi2_altscreen_carplay/pull/126)
   has been merged after all six source/audit/build checks passed using this
   pinned image, without a legacy GCC rebuild. Future updates must repeat
   compiler, QNX ARM ELF, symbol, artifact SHA and source/receipt review;
   a successful compiler build is still not vehicle acceptance.

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
