# direct-ts-parity provenance and design contract

This component is a clean-room implementation of the media behavior documented by the M.I.B. Omonob 790/791/Paid audit.
It does not include third-party binary bytes or copied decompiler output.

The component intentionally differs from `direct-ts-remux`:

- input is **M1AU complete AU records only**;
- source timestamps are interpreted as relative 32.32 fixed-point seconds and mapped to a 90-kHz presentation timeline;
- no `frame_no/fps` presentation clock exists;
- no fixed frame pacer exists;
- each complete AU becomes one H.264 PES;
- transport is continuous 12.288-Mbit/s TS with null fill;
- PID topology is PAT `0x0000`, PMT `0x0010`, PCR `0x1000`, H.264 `0x0011`;
- PAT/PMT and PCR recur at approximately 40 ms;
- physical writes are exactly 64 x 188 = 12032 bytes;
- predictive output pauses after a sequence gap until a fresh IDR;
- recovery is AU/PES-boundary safe: queued AUs are never packet-flushed mid-PES.

The current source-timestamp interpretation is based on two independent observations:

1. static audit of the Omonob bridge's source-timestamp to 90-kHz PTS arithmetic;
2. MU1440 vehicle telemetry where `seconds + fraction/2^32` tracks wall time and the fractional word is quantized near 1/240 s.

The source clock is used only relative to the first valid AU. No external epoch name is required.

## Exact reference behavior implemented

The parity path also reproduces the audited runtime invariants that materially affect the media transport:

- `/dev/mlb/isoTX2` is opened write-only/nonblocking;
- the reference diagnostic driver probes (`0x4004050c`, `0x4004050d`, `0x40040510`) are issued before streaming;
- queue flush `0x40040506` precedes start `0x80040509` with a 64-packet block argument;
- source-frame ordinal, not bridge receive count, owns the every-20-frame parity keyframe request;
- DMDT ownership is handled by the separate bounded parity-session component, not by the M.I.B. writev gate.

## Deliberate robustness differences

Functional parity does **not** mean reproducing defects that are not required for the reference behavior.

The audited reference producer rejects a video body above `0x40000` (262144) bytes before ring publication.
GEN2 currently accepts a larger complete-AU safety envelope and the parity bridge accepts up to its own bounded
M1AU maximum. The reference 262144-byte limit is published in runtime status for audit visibility, but it is not
artificially reintroduced as a failure mode. Normal reference-sized traffic follows the same media algorithm.

The audited reference low-latency path can discard packet-queue entries after a prefix of an AU/PES has already
been transmitted. This clean-room implementation instead performs latency/generation/sequence recovery only at
complete-AU boundaries. If the head PES has started, its remaining tail is preserved; only not-yet-started AUs
behind it are discarded before waiting for a fresh IDR.

These are explicit safety divergences, not unknown parity gaps.

## Control-plane scope

The transport parity proof is intentionally scoped to the producer metadata, source clock, H.264/PES/TS construction,
MOST writer and DMDT ownership lifecycle.

An already-installed M.I.B. `NavIgnore` Java policy is **not** part of the Omonob media reference and must not be
described as part of this clean-room parity implementation. A vehicle test may retain that existing policy only as
a separately identified control-plane substrate; exact full-stack Omonob parity would require a separate rebooted
control-plane experiment.

