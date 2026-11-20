#!/usr/bin/env python3
"""The calibration clips: 1010x376, 30 fps test patterns. Needs ffmpeg with libx264.

Patterns (--pattern, default grid):
  grid      static pixel grid with coordinate labels, 60 frames (file mibr-calib.avcc)
  black     solid black, 60 frames (mibr-calib-black.avcc)
  white     solid white, 60 frames (mibr-calib-white.avcc); the black/white pair shows the OEM overlay alpha
  contrast  static gray/near-black/near-white steps, colour bars, 1-px and 2-px checkers, 60 frames
  motion    120-frame seamless loop: moving bars, frame counter, 30-box frame ruler on a dark grid

Output: records of <u32 BE length><AU with 4-byte NAL lengths>, SPS and PPS in-band on each IDR.
usage: make_calib_clip.py <out.avcc> [--pattern grid|black|white|contrast|motion] [ffmpeg command]
"""
import struct
import subprocess
import sys
from pathlib import Path

W, H, FPS, GOP, FRAMES = 1010, 376, 30, 20, 60
PATTERNS = ("grid", "black", "white", "contrast", "motion")
MOTION_FRAMES = 120
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


def canvas(bg):
    px = bytearray(bytes(bg) * (W * H))

    def put(x, y, rgb):
        if 0 <= x < W and 0 <= y < H:
            px[(y * W + x) * 3:(y * W + x) * 3 + 3] = bytes(rgb)
    return px, put


def rect(put, x0, y0, w, h, rgb):
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            put(x, y, rgb)


def label(put, s, x, y, rgb, scale):
    for c in s:
        bits = DIGITS[c]
        for row in range(5):
            for col in range(3):
                if bits[row * 3 + col] == "1":
                    rect(put, x + col * scale, y + row * scale, scale, scale, rgb)
        x += 4 * scale


def solid(v):
    return bytes((v, v, v)) * (W * H)


# The cockpit overlay cannot be switched off. Measured on the rectified photos (2026-11-15): the top bar covers y<36
# (clock notch to y=50 at x 468..542) in every view; Voll leaves the full width only down to y=273 (below that only
# the trapezoid x 152..858); Center leaves only x 369..641 between the round gauges. So every test element lies in
# y 52..268 (full width visible in Voll), and the essentials repeat inside x 380..630 (Center).
TOP, BOTTOM = 52, 268


def contrast():
    px, put = canvas((0, 0, 0))
    bw = W // 16
    for i in range(16):  # band 1: 16 gray steps 0..255
        v = i * 17
        rect(put, i * bw, TOP, bw, 46, (v, v, v))
        label(put, str(v), i * bw + 4, TOP + 4, (255, 255, 255) if v < 128 else (0, 0, 0), 3)
    for i in range(16):  # band 2: near-black 0,4..60 (crush check)
        v = i * 4
        rect(put, i * bw, TOP + 46, bw, 34, (v, v, v))
        label(put, str(v), i * bw + 4, TOP + 50, (120, 120, 120), 3)
    for i in range(16):  # band 3: near-white 195..255
        v = 195 + i * 4
        rect(put, i * bw, TOP + 80, bw, 34, (v, v, v))
        label(put, str(v), i * bw + 4, TOP + 84, (60, 60, 60), 3)
    bars = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255), (255, 0, 255), (255, 255, 0),
            (255, 255, 255), (0, 0, 0))
    cw = W // len(bars)
    for i, c in enumerate(bars):  # band 4: R,G,B,C,M,Y,white,black
        rect(put, i * cw, TOP + 114, cw, 36, c)
    for x in range(W):  # band 5: black-to-white ramp
        v = x * 255 // (W - 1)
        rect(put, x, TOP + 150, 1, 20, (v, v, v))
    # band 6, sharpness, centred so it is inside the Center strip: 1-px checker, 2-px checker, 1-px vertical and
    # horizontal line pairs, each 56 wide, 46 high
    y0, h = TOP + 170, BOTTOM - TOP - 170
    for y in range(h):
        for x in range(56):
            for k, on in enumerate(((x + y) % 2 == 0, (x // 2 + y // 2) % 2 == 0, x % 2 == 0, y % 2 == 0)):
                v = 255 if on else 0
                put(384 + k * 62 + x, y0 + y, (v, v, v))
    return bytes(px)


def motion_frames():
    base, _ = canvas((32, 32, 32))
    for x in range(0, W, 100):
        for y in range(H):
            base[(y * W + x) * 3:(y * W + x) * 3 + 3] = bytes((52, 52, 52))
    for y in range(0, H, 50):
        for x in range(W):
            base[(y * W + x) * 3:(y * W + x) * 3 + 3] = bytes((52, 52, 52))
    n = MOTION_FRAMES
    out = []
    for f in range(n):  # frame n would equal frame 0 again: the loop is seamless
        px = bytearray(base)

        def put(x, y, rgb):
            if 0 <= x < W and 0 <= y < H:
                px[(y * W + x) * 3:(y * W + x) * 3 + 3] = bytes(rgb)
        rect(put, f * W // n, 0, 12, H, (255, 255, 255))
        rect(put, 0, f * H // n, W, 12, (255, 255, 255))
        # counter on its own box, drawn over the bars so it stays readable
        cw = 3 * 4 * 8 - 8
        # below the Wide view's guidance banner/arrow (y 58..126 while a route runs)
        rect(put, (W - cw) // 2 - 10, 132, cw + 20, 60, (0, 0, 0))
        label(put, "%03d" % f, (W - cw) // 2, 142, (255, 255, 255), 8)
        # 30-box ruler as two rows of 15 so it fits the Center strip; one box per frame at 30 fps.
        # Stays above y 268 (Voll keeps the full width visible only down to y 273).
        bw, gap = 14, 4
        x0 = (W - (15 * bw + 14 * gap)) // 2
        rect(put, x0 - 6, 202, 15 * bw + 14 * gap + 12, 50, (0, 0, 0))
        for i in range(30):
            rect(put, x0 + (i % 15) * (bw + gap), 208 + (i // 15) * 20, bw, 16,
                 (255, 214, 60) if i == f % 30 else (70, 70, 70))
        out.append(bytes(px))
    return out


def nals(stream):
    i = stream.find(b"\x00\x00\x01")
    while i >= 0:
        j = stream.find(b"\x00\x00\x01", i + 3)
        end = len(stream) if j < 0 else j
        nal = stream[i + 3:end].rstrip(b"\x00") if j >= 0 else stream[i + 3:end]
        yield nal
        i = j


def main():
    argv = sys.argv[1:]
    if not argv:
        raise SystemExit(__doc__)
    out = Path(argv.pop(0))
    pattern = "grid"
    if argv[:1] == ["--pattern"]:
        if len(argv) < 2 or argv[1] not in PATTERNS:
            raise SystemExit("--pattern needs one of: " + ", ".join(PATTERNS))
        pattern = argv[1]
        argv = argv[2:]
    ffmpeg = argv or ["ffmpeg"]
    if pattern == "motion":
        raw, frames = b"".join(motion_frames()), MOTION_FRAMES
    else:
        frame = {"grid": picture, "contrast": contrast,
                 "black": lambda: solid(0), "white": lambda: solid(255)}[pattern]()
        raw, frames = frame * FRAMES, FRAMES
    args = ffmpeg + ["-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgb24",
                     "-video_size", f"{W}x{H}", "-framerate", str(FPS), "-i", "pipe:0", "-an", "-c:v", "libx264",
                     "-preset", "medium", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level:v", "3.1",
                     "-crf", "20", "-g", str(GOP), "-keyint_min", str(GOP), "-sc_threshold", "0", "-bf", "0",
                     "-x264-params", "aud=1:repeat-headers=1:open-gop=0", "-frames:v", str(frames),
                     "-f", "h264", "pipe:1"]
    stream = subprocess.run(args, input=raw, stdout=subprocess.PIPE, check=True).stdout
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
    if len(aus) != frames or aus[0][0][0] & 31 != 7 or not any(n[0] & 31 == 5 for n in aus[0]):
        raise SystemExit("unexpected clip: %d access units" % len(aus))
    with out.open("wb") as f:
        for au in aus:
            body = b"".join(struct.pack(">I", len(n)) + n for n in au)
            f.write(struct.pack(">I", len(body)) + body)
    if out.stat().st_size >= 4 << 20:
        raise SystemExit("clip too large: %d bytes" % out.stat().st_size)
    print(out, out.stat().st_size, "bytes", len(aus), "frames", pattern)


if __name__ == "__main__":
    main()
