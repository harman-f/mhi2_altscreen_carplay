# Omonob/QCDWJ 791 AID12 minimal 30-fps test plan

> **Research status · 2026-11-05:** **MEDIA / COMPARATOR RESEARCH.** Findings or proposals are not automatically qualified runtime capabilities. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


Date: 2026-10-03  
Status: design only; no vehicle binary published yet

## Goal

Prepare the smallest possible A/B candidate for an AID12.3 tester who observes recurring block artifacts.

Requested behavior:

```text
791 geometry:            unchanged (800x480)
source maxFPS:           40 -> 30
periodic forceKeyFrame:  every 20 frames -> every 30 frames
effective cadence:       about 0.5 s -> about 1.0 s at 30 fps
```

## Preferred implementation

Do not rebuild the complete producer from decompiled source.

The low-risk diagnostic approach is to patch the original public 791 `core.so` at the two policy constants while preserving the ELF layout and exported ABI.

Public 791 base:

- size: 75,099 B
- SHA-256: `00b48a8fe876e6ff405124b87ed9eace1bcb079220ff7f02b866f42676477a4a`

## Exact semantic changes

### AirPlay display advertisement

```c
maxFPS = 40
```

becomes:

```c
maxFPS = 30
```

### Periodic IDR request

```text
frameOrdinal % 20 == 0 -> forceKeyFrame
```

becomes:

```text
frameOrdinal % 30 == 0 -> forceKeyFrame
```

Startup/recovery-triggered keyframe requests remain unchanged.

## Why this is useful

At the fixed 12.288-Mbit/s MOST transport, ideal queue drain between source frames increases from about 38.4 kB at 40 fps to about 51.2 kB at 30 fps.

That directly reduces pressure from large forced-IDR bursts while preserving the same AID12 geometry and the same downstream bridge.

## Test interpretation

- If artifacts disappear, source-rate / IDR-burst / queue-pressure interaction becomes strongly supported.
- If artifacts remain and line up with `latency-reset`, the next target should be the shared bridge's packet-level recovery flush, not more frequent keyframes.
- If no bridge correlation exists, investigate MOST write latency, AID12 receiver behavior, ring publication ordering, or oversized AU drops.

## Build gate

Before handing a file to a tester, pin the exact instruction/file offsets, prove the only semantic changes are `40->30` and periodic `20->30`, verify ELF/export/dependency identity, and publish original/patched hashes plus a reversible patch manifest.
