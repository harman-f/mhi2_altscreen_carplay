# MU1440 installed GEN2 source

This directory now carries the project-authored source overlay for the installed MU1440 R38
`libaltscreen111.so` checkpoint. The implementation is based on the public source tree at
`324b4f249883bb707e0d0a8995b2b6b5fe23be25`, with the source additions in this repository's
`settings/`, `src/native/alt111-settings/`, `src/native/vehicle-data/`, and the three-view changes in
this directory.

The installed binary recorded for this source is SHA-256
`304b5079374a08ed9a763528217476b29ad49e000ba25d0372ed4147cbb9a705`. That is an artifact
identity from the installed-source map, not a claim that this public integration has reproduced the
binary or that the current source has passed vehicle qualification. No OEM binary is published here.

## Source and build

The single settings authority is [`settings/registry.json`](../../../settings/registry.json). Its
generated C/HMI bindings are checked with:

```sh
python3 tools/generate_alt111_settings.py --check
```

Run the host-only settings and vehicle-data regression fixtures with:

```sh
bash tools/test_installed_gen2_host.sh
```

Build the QNX ARMv7 shared library from the repository root, using the pinned QNX 6.5 toolchain
image described in [`docs/build/INSTALLED_GEN2_SOURCE.md`](../../../docs/build/INSTALLED_GEN2_SOURCE.md):

```sh
docker run --rm --platform=linux/amd64 -v "$PWD:/src" -w /src mibr-qnx65-temp:4.9 \
  bash -c 'bash ./tools/build_altscreen111_gen2.sh build/gen2/libaltscreen111.so'
```

The build recipe links the shared settings core and project vehicle-data adapter into the existing
GEN2 library. The VehicleStatus and PASCD producers retain their existing off-by-default mode files.
The host fixtures cover the pure logic only; they do not execute the QNX interposer or establish
vehicle behavior.

## Three-view compatibility note

The installed overlay represents `viewarea.selected` as `0..2`, `viewareas.count` as `1..3`, and
`viewareas.initial` as `0..2`. The third safe-area geometry is supplied by GEN2 defaults. This
preserves the installed source behavior. It is a documented discrepancy with the current two-view
requirements snapshot and must not be read as a newly approved control redesign or as evidence that
the third view is qualified on every MU1440 unit.

The source tree retains the four runtime boundaries: the Type-111 hook, `parity-session`,
`direct-ts-parity`, and the DisplayManager arbitration guard remain separate components. This library
does not take ownership of parity lifecycle or MOST writes.
