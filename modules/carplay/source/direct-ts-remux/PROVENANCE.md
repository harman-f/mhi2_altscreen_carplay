# direct-ts-remux provenance

This source is the vehicle-tested remuxer used by the MU1440 direct Virtual Cockpit path.

## Public source authority

- Public source path: `src/native/direct-ts-remux/direct_ts_remux.c`
- Reference target: `MHI2_ER_SKG13_P4526_MU1440`
- Canonical developer binary SHA-256:
  `672275fc0e840e604cef68b6bd7b1e9e2059342471997d9bd859e32c34a0f02b`

The public source was checked against the vehicle-tested downstream implementation before
publication.

## Proven function

```text
Annex-B H.264
  -> direct-ts-remux
  -> MPEG-TS
  -> strict 64 × 188 = 12032-byte writes
  -> /dev/mlb/isoTX2
  -> devp-iso-mmx-mib2
  -> MOST150
  -> Virtual Cockpit decoder
```

## Public developer build policy

The public binary is intentionally built:

```text
-O2 -g
NOT stripped
```

The developer build keeps symbol/debug information for inspection and fault analysis.

## FFmpeg input

The remuxer statically links the required subset of FFmpeg 6.1.5:

- release tarball: `ffmpeg-6.1.5.tar.gz`
- SHA-256: `b8c8e926b948c14df1264cd0beac1c773df9170ac9cac97bdf1275cd3d385902`
- enabled components: H.264 demux/parser, MPEG-TS muxer, file and TCP protocols

See `THIRD_PARTY_NOTICES.md` for third-party licensing/provenance.
