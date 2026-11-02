#!/usr/bin/env python3
"""The calibration clip: a static pixel grid, 1010x376, 30 fps. Needs ffmpeg with libx264.

Output: mibr-calib.avcc, records of <u32 BE length><AU with 4-byte NAL lengths>, SPS and PPS in-band on each IDR.
usage: make_calib_clip.py <out.avcc> [ffmpeg command]
"""
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

W, H, FPS, GOP, FRAMES = 1010, 376, 30, 20, 60
DIGITS = {"0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111",
          "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001010010010",
          "8": "111101111101111", "9": "111101111001111"}
SCALE = 3


def picture():
    px = bytearray(b"\x00\x00\x00" * (W * H))

    def put(x, y, rgb):
        if 0 <= x < W and 0 <= y < H:
            px[(y * W + x) * 3:(y * W + x) * 3 + 3] = bytes(rgb)

    def strength(v):
        return (170, 190, 180) if v % 100 == 0 else (90, 104, 96) if v % 50 == 0 else (42, 50, 46)

    for x in range(0, W, 10):
        for y in range(H):
            put(x, y, strength(x))
    for y in range(0, H, 10):
        rgb = strength(y) if y % 50 == 0 else (42, 50, 46)
        for x in range(W):
            put(x, y, rgb)
    for x in (W - 1,):
        for y in range(H):
            put(x, y, (170, 190, 180))
    for x in range(W):
        put(x, H - 1, (170, 190, 180))

    def text(s, x, y, rgb):
        for c in s:
            bits = DIGITS[c]
            for row in range(5):
                for col in range(3):
                    if bits[row * 3 + col] == "1":
                        for dy in range(SCALE):
                            for dx in range(SCALE):
                                put(x + col * SCALE + dx, y + row * SCALE + dy, rgb)
            x += 4 * SCALE

    # Every 100x50 cell names its own top left corner, x in white, y in yellow: any part of the picture a cockpit
    # view leaves open can be read on its own.
    for y in range(0, H, 50):
        for x in range(0, W, 100):
            sx, sy = str(x), str(y)
            for dy in range(1, 5 * SCALE + 4):
                for dx in range(1, (len(sx) + len(sy)) * 4 * SCALE + 8):
                    put(x + dx, y + dy, (0, 0, 0))
            text(sx, x + 3, y + 3, (255, 255, 255))
            text(sy, x + 3 + (len(sx) * 4 + 1) * SCALE, y + 3, (255, 214, 60))
    for d in range(-24, 25):
        for w in (0, 1):
            put(W // 2 + d, H // 2 + w, (255, 70, 70))
            put(W // 2 + w, H // 2 + d, (255, 70, 70))
    return bytes(px)


def nals(stream):
    i = stream.find(b"\x00\x00\x01")
    while i >= 0:
        j = stream.find(b"\x00\x00\x01", i + 3)
        end = len(stream) if j < 0 else j
        nal = stream[i + 3:end].rstrip(b"\x00") if j >= 0 else stream[i + 3:end]
        yield nal
        i = j


def main():
    out = Path(sys.argv[1])
    ffmpeg = sys.argv[2:] or ["ffmpeg"]
    with tempfile.TemporaryDirectory() as tmp:
        h264 = Path(tmp) / "c.h264"
        args = ffmpeg + ["-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgb24",
                         "-video_size", f"{W}x{H}", "-framerate", str(FPS), "-i", "pipe:0", "-an", "-c:v", "libx264",
                         "-preset", "medium", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level:v", "3.1",
                         "-crf", "20", "-g", str(GOP), "-keyint_min", str(GOP), "-sc_threshold", "0", "-bf", "0",
                         "-x264-params", "aud=1:repeat-headers=1:open-gop=0", "-frames:v", str(FRAMES),
                         "-f", "h264", "pipe:1"]
        frame = picture()
        done = subprocess.run(args, input=frame * FRAMES, stdout=subprocess.PIPE, check=True)
        h264.write_bytes(done.stdout)
        stream = h264.read_bytes()
    aus, current = [], []
    for nal in nals(stream):
        kind = nal[0] & 31
        if kind == 9:
            if current:
                aus.append(current)
            current = []
            continue
        if kind == 6:
            continue
        current.append(nal)
    if current:
        aus.append(current)
    if len(aus) != FRAMES or aus[0][0][0] & 31 != 7 or not any(n[0] & 31 == 5 for n in aus[0]):
        raise SystemExit("unexpected clip: %d access units" % len(aus))
    with out.open("wb") as f:
        for au in aus:
            body = b"".join(struct.pack(">I", len(n)) + n for n in au)
            f.write(struct.pack(">I", len(body)) + body)
    print(out, out.stat().st_size, "bytes", len(aus), "frames")


if __name__ == "__main__":
    main()
