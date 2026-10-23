# Source-time media transport

This project-authored GPL-3.0-or-later implementation consumes complete M1AU access units, maps the relative 32.32 source clock to 90 kHz PTS/PCR, emits H.264 PES and MPEG-TS, and writes exactly 64 × 188 = 12032 bytes per physical output block. The media worker does not acquire display ownership. Its parent `parity-session` must establish and maintain the native gate contract.

The source derives from the independently authored public implementation at `harman-f/mhi2_altscreen_carplay@324b4f249883bb707e0d0a8995b2b6b5fe23be25`. Behavioral interoperability observations informed the design; no third-party implementation binaries or decompiler output are incorporated. Existing project and third-party notices remain applicable.

The pinned QNX 6.5 ARMv7 recipe reproduced the reference installed SHA-256 `3098cdd4469a4a3b4ee92c583518b3af362e02e41921ed3d80641853ced0827b`. Host transport, clock, recovery, EOF and exit tests are in `tests/direct_ts_parity_*`; the synthetic H.264 decode test needs FFmpeg with libx264. These checks establish source/build and host behavior, not an integrated vehicle release.
