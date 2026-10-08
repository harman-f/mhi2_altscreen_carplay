#!/usr/bin/env python3
"""Regenerate a visually equivalent MU1440 30fps M1AU test fixture.

Preserves the algorithm, H.264 elementary-stream + M1AU 56-byte wrapper and
inspection procedure for future diagnostic sessions. This is **not** a
bit-identical reconstruction of the first hand-authored 2026-10-08 fixture:
the original file SHA256 remains pinned in PR #24. New output requires a new
explicit hash, reviewed QNX build and operator sign-off.

Dependencies (host only): Python 3, numpy, ffmpeg with libx264.
Usage:
  python3 tools/fixtures/generate_mu1440_motion_m1au.py --output /tmp/mu1440-fixture
  python3 tools/fixtures/generate_mu1440_motion_m1au.py --output /tmp/test-small --frames 60
"""
import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

import numpy as np

W, H, FPS, GOP, SECONDS_WORD = 1010, 376, 30, 20, 364000
AUD = re.compile(rb"\x00\x00\x00?\x01")


def draw_digits(rgb: np.ndarray, number: int) -> None:
    # Fixed-geometry seven-segment counter, no external fonts or OS-rendering drift.
    segments = ("abcedf", "bc", "abged", "abgcd", "fgbc", "afgcd",
                "afgecd", "abc", "abcdefg", "abfgcd")
    positions = {
        "a": (3, 0, 19, 4), "g": (3, 17, 19, 4), "d": (3, 34, 19, 4),
        "f": (0, 3, 4, 16), "b": (21, 3, 4, 16),
        "e": (0, 20, 4, 16), "c": (21, 20, 4, 16),
    }
    rgb[9:64, 10:179] = (6, 10, 19)
    for idx, digit in enumerate(f"{number:05d}"):
        x, y = 16 + 31 * idx, 17
        for seg in segments[int(digit)]:
            dx, dy, dw, dh = positions[seg]
            rgb[y+dy:y+dy+dh, x+dx:x+dx+dw] = (254, 251, 228)


def frames(n: int):
    yy, xx = np.ogrid[:H, :W]
    for frame in range(n):
        rgb = np.empty((H, W, 3), dtype=np.uint8)
        rgb[..., 0] = 10 + (xx // 80) % 16
        rgb[..., 1] = 22 + (yy // 24) % 28
        rgb[..., 2] = 38 + ((xx // 35 + frame // 4) % 48)
        grid = (xx % 70 < 2) | (yy % 47 < 2)
        rgb[grid] = (56, 70, 97)
        # High-contrast moving diagonal crosses the full screen at 240px/s.
        v = (xx + (yy * 13 // 16) - frame * 8) % (W + 160)
        rgb[(v < 7).repeat(1, axis=0)] = (252, 230, 56)
        rgb[((v >= 7) & (v < 13)).repeat(1, axis=0)] = (18, 230, 244)
        # A second constant-speed reference bar makes 1-frame holds obvious.
        marker_x = (frame * 8) % W
        rgb[H-31:H-9, marker_x:marker_x+4] = (247, 247, 247)
        draw_digits(rgb, frame)
        yield rgb.tobytes()


def encode(out: Path, count: int):
    args = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{W}x{H}", "-framerate", str(FPS), "-i", "pipe:0",
        "-an", "-c:v", "libx264", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level:v", "3.1",
        "-g", str(GOP), "-keyint_min", str(GOP), "-sc_threshold", "0",
        "-bf", "0", "-b:v", "1550k", "-maxrate", "1800k", "-bufsize", "3600k",
        "-x264-params", "aud=1:repeat-headers=1:open-gop=0",
        "-f", "h264", str(out)
    ]
    with subprocess.Popen(args, stdin=subprocess.PIPE) as process:
        assert process.stdin
        for image in frames(count):
            process.stdin.write(image)
        process.stdin.close()
        if process.wait():
            raise RuntimeError("ffmpeg / libx264 failed")


def split_aus(stream: bytes):
    starts = list(AUD.finditer(stream))
    nal_starts = []
    for m in starts:
        i = m.end()
        if i < len(stream):
            nal_starts.append((m.start(), stream[i] & 0x1f))
    aud_start = [offset for offset, typ in nal_starts if typ == 9]
    if not aud_start or aud_start[0] != 0:
        raise ValueError("first NAL is not an AUD")
    result = []
    for i, start in enumerate(aud_start):
        end = aud_start[i+1] if i+1 < len(aud_start) else len(stream)
        next_nals = [typ for pos, typ in nal_starts if start <= pos < end]
        assert 9 in next_nals and (5 in next_nals or 1 in next_nals)
        result.append((stream[start:end], 5 in next_nals))
    return result


def wrap(data: bytes, out: Path, count: int) -> dict:
    aus = split_aus(data)
    if len(aus) != count:
        raise ValueError(f"Access units: got {len(aus)}, expected {count}")
    idrs = 0
    with out.open("wb") as f:
        for i, (au, idr) in enumerate(aus):
            if idr != (i % GOP == 0):
                raise ValueError(f"unexpected GOP/IDR pattern frame {i}")
            idrs += int(idr)
            flags = 0x0C | int(idr)  # TIME_KNOWN, TIME_PRESENT, IDR
            sec = SECONDS_WORD + i // FPS
            frac = ((i % FPS) * (1 << 32) + FPS // 2) // FPS
            header = struct.pack(">4sHHIIQQQQ", b"M1AU", 1, 56, flags, len(au),
                                 1, 1, 1, i + 1) + struct.pack("<II", frac, sec)
            if len(header) != 56:
                raise ValueError("internal M1AU header error")
            f.write(header)
            f.write(au)
    return {"au": len(aus), "idr": idrs, "p": count - idrs, "b": 0,
            "fps": FPS, "gop": GOP, "seconds": count / FPS}


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=3600)
    a = parser.parse_args()
    if a.frames < GOP or a.frames > 3600 or a.frames % GOP:
        parser.error("--frames must be a positive multiple of GOP=20, <=3600")
    a.output.mkdir(parents=True, exist_ok=True)
    h264 = a.output / "mu1440_motion_regenerated.h264"
    m1au = a.output / "mu1440_motion_regenerated.m1au"
    encode(h264, a.frames)
    summary = wrap(h264.read_bytes(), m1au, a.frames)
    summary["h264_bytes"] = h264.stat().st_size
    summary["m1au_bytes"] = m1au.stat().st_size
    summary["h264_sha256"] = sha(h264)
    summary["m1au_sha256"] = sha(m1au)
    summary["sha256_matches_original_frozen_fixture"] = (
        summary["m1au_sha256"] ==
        "e853dbf2d690e534f9020fd3c206550ca44177408d3d2c5d20f2f863645724b9"
    )
    (a.output / "AUDIT.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print("NOTE: new output is NOT automatically accepted by the frozen QNX fixture build.")


if __name__ == "__main__":
    main()
