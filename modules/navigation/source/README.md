# MU1440 Route Guidance source build

This directory builds two QNX ARM outputs: `libmibr_rgi_ipod.so` and `mibr-rgi`.
It does not contain an `mm-ipod` launcher/wrapper, an installer, or a deployable kit.
The output manifest covers only these two artifacts.

## Inputs

- `QNX_TARGET`: QNX 6.5 ARMv7 target sysroot.
- `IAP2_LIB`: caller-supplied, locally obtained MU1440 `libiap2client.so.1`.
  The build requires SHA-256 `c33021b21c5656886e64964efcf806fddb4259027c3c1ed396522e7a44adfdea`.
  Firmware library bytes are not included here. The hash is the identity of the
  previously analyzed MU1440 input, not a license to redistribute it.
- That exact library has a `DT_NEEDED` dependency on `libstrm.so.1`, which is supplied
  by the target firmware, not by the public QNX toolchain. The link leaves shared-library
  references unresolved for runtime resolution; this does not package or validate
  `libstrm.so.1`.
- Clang and LLD compatible with the source's QNX 6.5 ABI settings.
- Host `sha256sum` and `awk` for the input identity check and output manifest.

The RGD TLV parser is vendored from GPL-3.0 upstream source; see
[`third_party/luka-rgd/UPSTREAM.md`](third_party/luka-rgd/UPSTREAM.md).

## Build

```sh
QNX_TARGET=/path/to/qnx6 IAP2_LIB=/path/to/libiap2client.so.1 ./build.sh /tmp/rgi-out
```

The output's `SHA256SUMS` covers only the two files actually built. A passing compile
does not prove the fixed MU1440 driver offsets, runtime preload, HMI integration,
vehicle behavior, or a complete installation/rollback path. Those require separate
exact-target evidence.
