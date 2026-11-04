# Module binary lineage (source-build receipt, not release acceptance)

The development repository's [module layout contract](../architecture/REPOSITORY_LAYOUT.md) requires an exact link between module inputs, compiler provenance, target and generated binary hashes. This is an **incremental build receipt**, not an assertion that all published or carried historical binaries can be rebuilt.

## Current implementation

`tools/emit_module_build_lineage.py` reads the canonical `modules/module-index.json` and a **selected set of actual, already-built** binary paths. It emits a stable UTF-8 JSON file containing:

- Git source commit and *declared* toolchain commit plus the original pinned Dockerfile SHA-256;
- target profile requested for the build, clearly **not** proof of target hardware/ABI qualification;
- each output's module, declared logical name, relative path, size and SHA-256;
- all indexed source, runtime and build-script inputs for the chosen module(s) and declared transitive dependencies; per-file SHA-256 and a stable ordered aggregate input hash;
- declared build coverage flags (including partial-source status). The receipt always records `vehicle_qualified: false` and `bit_reproducible_verified: false`.

A missing source path, unknown module/profile/output, duplicate output, unsafe file reference, changed build hash or mismatched exact Git HEAD fails closed. No target writes are performed. An existing binary with no verifiable module source link must remain a separately labeled prebuilt artifact, not be added under an invented ownership mapping.

## Immutable toolchain image provenance (pending implementation)

The [QNX toolchain image contract](QNX_TOOLCHAIN_IMAGE.md) identifies the
existing digest-pinned GCC 4.9 / QNX 6.5 ARMv7 container and the necessary
CI migration and qualification checks. The current receipt's declared
toolchain commit/Dockerfile SHA-256 must **not** be mistaken for proof of which
container was actually executed. A future build-lineage revision must capture
and verify the actual container digest and compiler version before the release
pipeline can rely on it for native-binary provenance.

## Host checks

```bash
python3 tools/check_module_index.py --self-test
python3 tools/emit_module_build_lineage.py --self-test
```

The independent `module-build-lineage.yml` workflow tests these checks on supported branches. Both tests use synthetic disposable data; they **do not compile or qualify a QNX target**.

## Example: record already-built MU1440 outputs

Run on the exact checkout used for the QNX source build, **after** its existing build and output verification. The toolchain identity below is the pinned public build recipe; confirm the current workflow before reuse.

```bash
python3 tools/emit_module_build_lineage.py \
  --commit "$(git rev-parse HEAD)" \
  --target-profile skoda-mu1440-p4526 \
  --toolchain-commit 56a66557245af14077678cd28a83ce3a337d9e2d \
  --toolchain-dockerfile-sha256 9a867a7ae70f2c0222a241b80232856526ccec0db2cfe013f8991ca31c74bcb1 \
  --artifact carplay:libaltscreen111.so=build/mu1440-source/libaltscreen111.so \
  --artifact carplay:alt111-settings=build/mu1440-source/alt111-settings \
  --artifact broker:mibr-v3-service=build/mu1440-source/mibr-control/mibr-v3-service-QNX65-ARMv7-NOT-INSTALL-READY \
  --out build/mu1440-source/MODULE_BUILD_LINEAGE.json

python3 tools/emit_module_build_lineage.py \
  --verify build/mu1440-source/MODULE_BUILD_LINEAGE.json
```

The MU1440 QNX source-build workflow now emits and verifies `build/mu1440-source/MODULE_BUILD_LINEAGE.json` after its actual source-build and SHA-256/ARM-ELF gates. Its first receipt covers the built CarPlay GEN2 library, CarPlay settings CLI, and Broker V3 service; all other binaries remain outside this specific receipt unless separately inventoried and verified. The JSON is uploaded alongside existing source-build artifacts. This receipt explicitly records `vehicle_qualified: false` and `bit_reproducible_verified: false`. A future R3 packager must consume only verified receipts, establish the independent distribution source inventory, and pass final ZIP, profile and payload-hash validation before publication.

## Deliberate limitations

Source paths are supplied by the migration-in-progress module index; the current index does **not** yet enumerate all possible build-time inputs, compiler command-line flags, external SDK/JDK libraries, generated Java resources or profile-specific binaries. A present input hash is not an exhaustive dependency proof. The unmodified CI toolchain recipe is identified by source commit/Dockerfile hash; a byte-exact toolchain image digest and actual compiler version/output reproducibility have not yet been independently attested. No vehicle readiness, firmware universality, installer compatibility, source completeness or bit-for-bit repeatable build is claimed.

Next: extend the module index with complete recipes and artifact owners as each component is migrated, add complete build command/SDK identity, record verified QNX outputs in CI, and let the later multi-target R3 packager stage profile-aware inputs without duplicated source ownership.
