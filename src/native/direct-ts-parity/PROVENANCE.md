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
