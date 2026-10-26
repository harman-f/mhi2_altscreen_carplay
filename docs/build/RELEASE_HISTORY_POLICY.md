# Release history and immutable product distribution

**26 October 2026:** The legacy `mu1440-aid10-dev-current` GitHub Release
and its two downloadable assets have been withdrawn. The original alias tag
remains for historical provenance. The historical publisher workflow at
`.github/workflows/release-mu1440-aid10.yml` is **retired and inert**:
manual invocation only, read-only permissions, no archive assembly and no
release/tag mutation. The name of the old developer archive is not a product
version or a current download.

This does **not** publish the archived private 1.3.2 kit, promote the public
R57 source-only stack, or qualify a Unit or vehicle.

## Contract for its successor

1. Use unique immutable versioned tags and names; fail on collisions rather
   than overwriting or sweeping historical tags/assets. Never reassign the
   retained `dev-current` alias to a different package as a shortcut.
2. Bind the full source commit, target/cluster identity, configuration
   fingerprints, binary-set identity, package identity, payload file hashes,
   toolchain/build provenance and qualification level in one validated manifest.
3. Independently verify complete package-member closure and repeatable archive
   assembly before granting any new publisher write privileges.
4. Keep source verification and release-publishing credentials separate.
   Ordinary PR CI must be read-only. No GitHub token with release-write
   privileges belongs in the retired workflow.
5. Proprietary firmware, unlicensed OEM/J9 inputs, private Unit data and
   unreviewed binaries are not eligible for public source or release assets.
6. Release publication is a separate, approval-gated action after installer
   rollback, target compatibility, rights and stated acceptance have passed.

The [product delivery plan](PRODUCT_DELIVERY_PIPELINE.md) will be the
public integration reference when that documentation reaches `develop`.
Until then, source and build CI outputs are **not** the versioned product.
