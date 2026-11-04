# Building and using direct-ts-remux

> Developer / SSH workflow only. This is not an SD-card installer.

`direct-ts-remux` is the smallest currently useful public binary from the proven Virtual Cockpit path.
It does one job:

```text
Annex-B H.264
  -> MPEG-TS
  -> strict MU1440 isoTX2 writes
```

It does not negotiate CarPlay, patch the HMI, enable the VC map view or take ownership away from the
stock DisplayManager producer.

## Proven source baseline

The public source is imported unchanged from the vehicle-proven Run143 downstream implementation.

- private source authority: `9b82b2d10f591ce34670f66824d911bea10fa04b`
- source Git blob: `718974737f7e01d94968424466dfe5a5c6896f53`
- reference firmware: `MHI2_ER_SKG13_P4526_MU1440`

The public build changes only the build/debug policy:

```text
historic runtime build: -O2 + strip -s
public developer build: -O2 -g + NO strip
```

## Reproducible build

The repository CI builds against the pinned public QNX 6.5 ARMv7 toolchain from
`luka-dev/qnx65-armv7-toolchain`.

Pinned toolchain commit:

```text
56a66557245af14077678cd28a83ce3a337d9e2d
```

FFmpeg input:

```text
FFmpeg 6.1.5
ffmpeg-6.1.5.tar.xz
SHA-256 05fbe9db1f5452a3605bb1d9bf91da9d4bb08162891692e4f172b58c49109412
```

This is the archive used by `tools/build_direct_ts_remux.sh` and CI. The
historical vehicle-proven run143 artifact was built from `ffmpeg-6.1.5.tar.gz`
(SHA-256 `b8c8e926b948c14df1264cd0beac1c773df9170ac9cac97bdf1275cd3d385902`,
see its receipt under `artifacts/`); the receipt is not rewritten.

The exact build logic is in:

```text
tools/build_direct_ts_remux.sh
.github/workflows/build-direct-ts-remux.yml
```

The workflow keeps the resulting ELF unstripped and validates that both `.symtab` and
`.debug_info` are present.

## Manual build

After building the pinned QNX toolchain image, run the repository build script inside that
environment.

Conceptually:

```text
tools/build_direct_ts_remux.sh \
  modules/carplay/source/direct-ts-remux/direct_ts_remux.c \
  build/direct-ts-remux
```

The build script downloads the exact FFmpeg release tarball, verifies its SHA-256, builds only the
required H.264/MPEG-TS subset and links the executable.

## Command line

```text
direct-ts-remux INPUT OUTPUT FPS MAX_SECONDS WAIT_SECONDS VIDEO_PID
```

Arguments:

| Argument | Meaning |
| --- | --- |
| `INPUT` | Annex-B H.264 file or supported input URL, e.g. local TCP source |
| `OUTPUT` | output file or device; proven VC device is `/dev/mlb/isoTX2` |
| `FPS` | source/presentation timing used to synthesize packet timestamps |
| `MAX_SECONDS` | bounded runtime; `0` means no time limit |
| `WAIT_SECONDS` | bounded input-open retry window |
| `VIDEO_PID` | MPEG-TS video PID; proven path uses `0x11` |

Example from the proven live architecture:

```text
./direct-ts-remux \
  tcp://127.0.0.1:19820 \
  /dev/mlb/isoTX2 \
  30 90 45 0x11
```

This example is a transport invocation, **not** a complete installation recipe.

## MU1440 device contract

The application does not issue one `write()` per 188-byte TS packet.

Vehicle testing established:

```text
64 MPEG-TS packets × 188 bytes = 12032 bytes
```

as the working application message boundary for `/dev/mlb/isoTX2`.

The remuxer therefore buffers complete TS packets and emits exactly 12032-byte blocks. A positive
short write is treated as a hard failure. A final partial block is completed with MPEG-TS null
packets.

## Before using /dev/mlb/isoTX2

Do not start direct output while the native DisplayManager video producer is simultaneously feeding
the same channel.

The project has proven a separate process-local DisplayManager `writev()` gate for reversible
STOCK/DIRECT arbitration. See:

```text
docs/architecture/DIRECT_VC_VIDEO_PATH.md
```

The useful order is:

```text
1. verify stock map and recovery
2. verify alternate H.264 source is ready
3. enter DIRECT / suppress only native DisplayManager payload
4. start direct-ts-remux
5. observe/log
6. stop direct-ts-remux
7. return STOCK
8. verify native map recovery
```

Do not test while driving.

## What this binary does not solve

It does not solve:

- CarPlay ScreenAlt capability negotiation
- Type-111 session setup/decryption
- `suggestUI` / `showUI`
- navigation-provider handover
- ViewArea selection
- HMI smartphone-navigation arbitration
- stock map ownership by itself

Those are deliberately separate layers.

## Debug information

The public developer ELF is kept unstripped so that crashes and behavioral differences can be
correlated with exact symbols.

CI publishes text sidecars for:

- ELF header
- section table
- full symbol table
- undefined symbols
- dynamic section
- relocations
- SHA-256
- build provenance

This is intentional and should remain the default while the implementation is experimental.
