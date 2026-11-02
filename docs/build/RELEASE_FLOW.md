# MU1440 build and release flow

Changes pushed to main in the native source/build paths run the existing host and QNX checks. After both succeed, the QNX output and its checksums are published in an immutable prerelease named for the exact commit. This archive contains development binaries, not an installer or vehicle acceptance. It does not include the IBM J9 menu JAR or RGI outputs: those require separately supplied firmware-related inputs, which are not redistributed in this repository.

The legacy AID10 installer workflow remains available only through manual dispatch with a new unique version tag. It packages the older pinned seven-file payload identified in `release/CURRENT.md`; it does not package current menu/RGI sources. Existing tags and releases are retained. A new current installer requires a separately assembled and verified package with its exact payload, instructions and rollback; the legacy workflow must not be presented as that package.

The workflows use GitHub Actions; the existing `tools/build_mu1440_source.sh` also permits a local QNX build using the documented toolchain. GitHub build artifacts are temporary transport; the commit-tagged prerelease preserves the actual archive and its SHA-256.
