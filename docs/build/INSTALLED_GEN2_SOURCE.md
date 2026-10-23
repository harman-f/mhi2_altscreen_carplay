# Building the installed MU1440 GEN2 source

The GEN2 source, shared settings backend, and project vehicle-data module build together as one
`libaltscreen111.so`. The generated registry is checked from the repository root before the cross
build:

```sh
python3 tools/generate_alt111_settings.py --check
bash tools/test_installed_gen2_host.sh
```

The public build workflow uses the pinned `luka-dev/qnx65-armv7-toolchain` revision
`56a66557245af14077678cd28a83ce3a337d9e2d`, verifies the Dockerfile SHA-256
`9a867a7ae70f2c0222a241b80232856526ccec0db2cfe013f8991ca31c74bcb1`, and builds target `base-env`
with `BASE=base-4.9`. It tags the resulting image `mhi2-qnx65-armv7-public:4.9`.

Build the shared object from the repository root:

```sh
docker run --rm --platform=linux/amd64 \
  -v "$PWD:/src" -w /src mhi2-qnx65-armv7-public:4.9 \
  bash -c 'QCC=arm-unknown-nto-qnx6.5.0eabi-gcc bash ./tools/build_altscreen111_gen2.sh build/gen2/libaltscreen111.so'
```

The same source recipe can use an already-built compatible local image by setting `QCC` to
`arm-unknown-nto-qnx6.5.0eabi-gcc` and running `tools/build_altscreen111_gen2.sh` from the repository
root. Keep the output outside source directories. The workflow also checks the ELF machine and
debug sections, then verifies expected configuration and protocol strings.

## Evidence boundary

The build is a QNX cross-build, not a vehicle test. The installed R38 library was recorded as
`304b5079374a08ed9a763528217476b29ad49e000ba25d0372ed4147cbb9a705`.

Validation performed on 2026-10-23 with `mibr-qnx65-temp:4.9`:

- Host settings, three-view validation, VehicleData and VehicleStatus fixtures: **PASS**.
- QNX ARMv7 build of `libaltscreen111.so`: **PASS**, SHA-256
  `304b5079374a08ed9a763528217476b29ad49e000ba25d0372ed4147cbb9a705`.
- A build of the public source with its generic one-line provenance comment, from the repository root
  at `/src`, reproduced the
  installed R38 library SHA-256 exactly: `304b5079374a08ed9a763528217476b29ad49e000ba25d0372ed4147cbb9a705`.
- The settings CLI build SHA-256 is `b0d61578452a93b966f268e2bd400029bb1b6fa249dfd18e8895f851ca89073c`,
  matching the recorded installed-source hash prefix `b0d61578452a93b9`.
- The public build output is verified and hashed by CI; the workflow uploads it as a build artifact
  and does not publish it as a release payload.
- Both public source outputs reproduce their recorded installed R38 hashes. This is source/build
  evidence, not a vehicle qualification result.

The 3-view registry values reproduce the installed source overlay. They are a known discrepancy
with the current two-view requirements snapshot; this source publication does not approve a change
to that requirements inventory.
