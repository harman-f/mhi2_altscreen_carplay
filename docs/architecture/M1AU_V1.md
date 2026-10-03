# M1AU v1 local AU metadata framing

Status: experimental, disabled by default.

M1AU is a **local loopback transport** between the GEN2 Stream-111 receiver and
`direct-ts-remux`. It does not change the iPhone-facing AirPlay protocol and it
does not change the MOST/MPEG-TS output contract.

The purpose is to keep one complete Annex-B access unit associated with the
metadata that arrived with the same Apple Stream-111 frame.

## Runtime switch

```text
DIRECT_SOURCE_FRAMING=0   # default: vehicle-proven raw Annex-B TCP
DIRECT_SOURCE_FRAMING=1   # experimental M1AU v1
```

The Auto-Direct supervisor coordinates both endpoints. Before the remuxer opens
the local renderer connection it:

1. creates `/tmp/mibr-alt111-au-framing.enabled` when framing is requested;
2. starts `direct-ts-remux` with `MIBR_INPUT_M1AU=1`.

GEN2 selects raw or framed mode once when the renderer connection is accepted.
The format cannot change in the middle of that TCP connection.

## Header

Each complete queued AU is preceded by a fixed 56-byte header.

```text
offset  size  encoding    meaning
0x00    4     bytes       "M1AU"
0x04    2     BE          version = 1
0x06    2     BE          header size = 56
0x08    4     BE          flags
0x0c    4     BE          Annex-B payload bytes
0x10    8     BE          GEN2 stream generation
0x18    8     BE          codec generation
0x20    8     BE          consumer generation
0x28    8     BE          AU sequence / ordinal
0x30    8     raw bytes   Apple Stream-111 timestamp area
```

Flags:

```text
bit 0  IDR AU
bit 1  priming AU (current SPS/PPS prepended before first IDR)
```

The final eight bytes are copied **verbatim** from Stream-111 header offsets
`0x08..0x0f`. M1AU deliberately assigns no endian, epoch or unit to them.

## Remux behaviour in v1

The M1AU reader strips the 56-byte records through a custom FFmpeg AVIO reader.
The H.264 demuxer therefore still receives the same concatenated Annex-B bytes
as the legacy path.

Version 1 is diagnostic only:

- sequence and generation metadata are validated/recorded;
- raw timestamp bytes and two diagnostic little-endian word views are logged;
- timestamp-word deltas are logged;
- sequence gaps are counted;
- **PTS/DTS/PCR generation remains the existing CFR implementation**.

This separation is intentional. First prove the metadata path and determine the
Apple timestamp semantics from vehicle data. Source-derived 90-kHz timing is a
later opt-in stage.

## Failure/fallback contract

Raw Annex-B remains the release/default path.

A framed producer and a raw consumer, or the reverse, is not supported. The
Auto-Direct supervisor owns both switches to prevent that mismatch.

GEN2 preserves its existing queue, IDR priming, codec/consumer generations and
nonblocking/backpressure behaviour. Header bytes do not advance the AU payload
offset.

## Telemetry

`/tmp/mibr-direct-remux.status` adds:

```text
input_mode=raw-annexb|m1au-v1
m1au_records=
m1au_stream=
m1au_codec=
m1au_consumer=
m1au_sequence=
m1au_sequence_gaps=
m1au_flags=
m1au_ts_raw=
m1au_ts_word1_le=
m1au_ts_word2_le=
m1au_ts_word1_delta=
m1au_ts_word2_delta=
```

The same values are sampled into each Auto-Direct session's
`telemetry.tsv`, alongside source arrival FPS, H.264 bit rate, MOST bit rate,
pacer metrics and isoTX backpressure.

## Vehicle test order

1. Keep `DIRECT_SOURCE_FRAMING=0`; establish the normal 30-fps baseline.
2. Set `DIRECT_SOURCE_FRAMING=1`; keep source and output at 30 fps.
3. Reconnect/restart the direct session and confirm:
   - `input_mode=m1au-v1`;
   - increasing `m1au_sequence`;
   - `m1au_sequence_gaps=0`;
   - stable picture and unchanged MOST behaviour.
4. Only after M1AU at 30 fps is stable, test source/output 40 fps.
5. Do not enable source-derived PTS/PCR until the raw timestamp fields have
   enough runtime evidence to identify their semantics.
