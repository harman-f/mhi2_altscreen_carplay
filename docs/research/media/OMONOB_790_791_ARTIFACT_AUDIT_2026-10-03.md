# Omonob/QCDWJ 790 vs 791 artifact-path audit

> **Research status · 2026-11-05:** **MEDIA / COMPARATOR RESEARCH.** Findings or proposals are not automatically qualified runtime capabilities. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


Date: 2026-10-03  
Scope: public Free 790/AID10.x and 791/AID12.3 profiles  
Status: static analysis; runtime causality still requires vehicle-log correlation

## Main result

The public 790 and 791 Stream-111 media paths are substantially the same.

- AVCC receive/decrypt handling is effectively shared.
- CPRG ring publication is identical.
- The force-keyframe worker is identical.
- Both request `forceKeyFrame` every 20 video frames in addition to recovery/startup requests.
- Both use the same downstream `altscreen-most-bridge` and `carplay-cluster-supervisor` binaries.
- The hot-path 791 difference is primarily the expected `800x480` config geometry instead of `1010x376`.

The 791 build additionally advertises CarPlayControl at the root feature layer and adds a virtual-knob worker. Those are control-plane differences rather than a separate video transport implementation.

## Media chains

```text
790:
CarPlay type 111, 1010x376, maxFPS 40
 -> TCP screen stream
 -> AES-CTR
 -> AVCC validation / IDR detection
 -> periodic + recovery forceKeyFrame
 -> CPRG ring
 -> native H.264/PES/MPEG-TS bridge
 -> 12032-byte isoTX2 writes
 -> MOST
 -> AID10.x

791:
CarPlay type 111, 800x480, maxFPS 40
 -> same TCP/AES/AVCC/keyframe logic
 -> same CPRG writer
 -> same native bridge
 -> same isoTX2 writer
 -> MOST
 -> AID12.3
```

## Periodic IDR pressure

At a 40-fps source ceiling, a request every 20 frames is approximately one forced-IDR request every 0.5 seconds. This can shorten the duration of a damaged H.264 reference chain, but it also creates recurring bitrate bursts.

## Shared bridge recovery pressure point

The shared bridge queues individual 188-byte MPEG-TS packets. Low-latency recovery is triggered above roughly 1024 queued packets, about 192.5 kB or 125 ms at the 12.288-Mbit/s transport rate.

Recovery flushes the pending TS packet queue and waits for a fresh IDR. Static analysis shows that the flush itself is not explicitly aligned to a PES/access-unit boundary, while the MOST writer independently drains 64-packet / 12032-byte blocks.

That creates a concrete theoretical failure path:

```text
video PES begins
 -> prefix reaches the writer
 -> latency/gap recovery triggers
 -> remaining queued tail is discarded
 -> receiver sees an incomplete H.264 access unit
 -> block corruption can persist
 -> next clean IDR restores reference state
```

Classification: `MID_PES_QUEUE_FLUSH_ARTIFACT_PATH = PROVEN_STATIC_MECHANISM / RUNTIME_CAUSALITY_OPEN`.

## Why 40 fps is a useful discriminator

At 12.288 Mbit/s the ideal transport drain between source frames is approximately:

| Source fps | bytes drained per frame interval |
|---:|---:|
| 40 | 38.4 kB |
| 30 | 51.2 kB |
| 25 | 61.4 kB |
| 20 | 76.8 kB |

The ring accepts individual AUs up to 256 KiB. A large IDR at 40 fps can therefore leave much more queue backlog for the next frame than the same-sized AU at 20 fps.

## Recommended A/Bs

1. Disable only the permanent every-20-frame keyframe request while retaining event/recovery keyframes.
2. Test the 791 profile with a 20-fps source ceiling.
3. Disable the 791 virtual-knob worker as an independent control-plane test.
4. Correlate visible artifacts with `idr_max`, `queue_hi`, `latency-reset`, slow-write metrics and `latency-resume-idr`.

If the queue-reset correlation is confirmed, recovery should be changed to discard data only at an access-unit/PES boundary rather than flushing arbitrary queued TS packets.

## M.I.B. implication

Keep timing and recovery separate:

```text
source timestamps / PTS / PCR -> cadence and presentation timing
forceKeyFrame                -> decoder/reference recovery
```

Permanent periodic IDRs should remain a diagnostic or bounded fallback, not automatically become the normal final policy.
