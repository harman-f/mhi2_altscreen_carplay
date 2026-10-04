#!/usr/bin/env python3
import argparse
import socket
import struct
import subprocess
import tempfile
import threading
import time
from pathlib import Path

TS = 188
BLOCK = 12032
PORT = 21987


def sc(nal: bytes) -> bytes:
    return b"\x00\x00\x00\x01" + nal


# Opaque H.264 NAL byte strings are sufficient for transport-level testing.
SPS = sc(b"\x67\x42\x00\x1f\xe5\x88\x68")
PPS = sc(b"\x68\xce\x06\xe2")
IDR = sc(b"\x65\x88\x84\x21")
PFRAME = sc(b"\x41\x9a\x22\x11")


def source_ts(frame_index: int, hz: int = 240, sec0: int = 1000) -> bytes:
    sec = sec0 + frame_index // hz
    rem = frame_index % hz
    frac = (rem * (1 << 32)) // hz
    return struct.pack("<II", frac, sec)


def m1au(seq: int, payload: bytes, idr: bool = False, priming: bool = False) -> bytes:
    flags = (1 if idr else 0) | (2 if priming else 0)
    header = struct.pack(
        ">4sHHIIQQQQ",
        b"M1AU",
        1,
        56,
        flags,
        len(payload),
        1,
        1,
        1,
        seq,
    )
    return header + source_ts(seq - 1) + payload


def serve(records, ready):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", PORT))
    s.listen(1)
    ready.set()
    c, _ = s.accept()
    with c:
        for record in records:
            c.sendall(record)
        # Prove that physical TS/PCR continues while the source is momentarily quiet.
        time.sleep(0.12)
    s.close()


def pid(packet):
    return ((packet[1] & 0x1F) << 8) | packet[2]


def payload_offset(packet):
    afc = (packet[3] >> 4) & 3
    if afc == 1:
        return 4
    if afc == 3:
        return 5 + packet[4]
    return None


def parse_pts(payload):
    assert payload[:4] == b"\x00\x00\x01\xe0", payload[:8].hex()
    assert payload[7] & 0x80
    q = payload[9:14]
    return (
        (((q[0] >> 1) & 7) << 30)
        | (q[1] << 22)
        | ((q[2] >> 1) << 15)
        | (q[3] << 7)
        | (q[4] >> 1)
    )


def decode_pcr(packet):
    assert pid(packet) == 0x1000
    assert ((packet[3] >> 4) & 3) in (2, 3)
    assert packet[4] >= 7 and packet[5] & 0x10
    q = packet[6:12]
    return (q[0] << 25) | (q[1] << 17) | (q[2] << 9) | (q[3] << 1) | (q[4] >> 7)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bridge")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.ts"

        # Six complete AUs on the exact 240-Hz source-time grid.
        aus = [SPS + PPS + IDR] + [PFRAME + bytes([i]) for i in range(1, 6)]
        records = [
            m1au(i + 1, au, idr=(i == 0), priming=(i == 0))
            for i, au in enumerate(aus)
        ]

        ready = threading.Event()
        thread = threading.Thread(target=serve, args=(records, ready), daemon=True)
        thread.start()
        assert ready.wait(3)

        cp = subprocess.run(
            [args.bridge, f"tcp://127.0.0.1:{PORT}", str(out)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            check=False,
        )
        thread.join(2)
        if cp.returncode:
            raise SystemExit(
                f"bridge rc={cp.returncode}\nSTDOUT={cp.stdout}\nSTDERR={cp.stderr}"
            )

        data = out.read_bytes()
        assert data and len(data) % BLOCK == 0, (len(data), "not 12032-byte aligned")
        packets = [data[i : i + TS] for i in range(0, len(data), TS)]
        assert all(p[0] == 0x47 for p in packets)

        pids = {pid(p) for p in packets}
        expected = {0x0000, 0x0010, 0x0011, 0x1000, 0x1FFF}
        assert pids <= expected, pids
        assert expected <= pids, pids

        video = [p for p in packets if pid(p) == 0x0011]
        starts = [i for i, p in enumerate(video) if p[1] & 0x40]
        assert len(starts) == len(aus), (len(starts), len(aus))

        pts = []
        pes_payloads = []
        for idx, start in enumerate(starts):
            end = starts[idx + 1] if idx + 1 < len(starts) else len(video)
            raw = bytearray()
            for packet in video[start:end]:
                off = payload_offset(packet)
                assert off is not None and off <= TS
                raw.extend(packet[off:])
            pts.append(parse_pts(raw))
            header_end = 9 + raw[8]
            pes_payloads.append(bytes(raw[header_end:]))

        # 1/240 second at 90 kHz is exactly 375 ticks.
        diffs = [b - a for a, b in zip(pts, pts[1:])]
        assert all(abs(delta - 375) <= 1 for delta in diffs), (pts, diffs)

        # One complete AU becomes one PES; AUD is explicit; IDR carries SPS/PPS.
        assert pes_payloads[0].startswith(b"\x00\x00\x00\x01\x09\xf0")
        assert b"\x00\x00\x00\x01\x67" in pes_payloads[0]
        assert b"\x00\x00\x00\x01\x68" in pes_payloads[0]
        assert b"\x00\x00\x00\x01\x65" in pes_payloads[0]
        assert all(
            payload.startswith(b"\x00\x00\x00\x01\x09\xf0")
            for payload in pes_payloads[1:]
        )

        pcrs = [decode_pcr(p) for p in packets if pid(p) == 0x1000]
        assert len(pcrs) >= 2, pcrs
        pcr_diffs = [b - a for a, b in zip(pcrs, pcrs[1:])]
        assert all(3500 <= delta <= 3700 for delta in pcr_diffs), pcr_diffs[:10]

        assert sum(1 for p in packets if pid(p) == 0x1FFF) > 0

        print("PARITY_INTEGRATION=PASS")
        print(
            f"blocks={len(data)//BLOCK} packets={len(packets)} "
            f"video_pes={len(starts)} pts_diffs={diffs} "
            f"pcr_diffs={pcr_diffs[:4]}"
        )


if __name__ == "__main__":
    main()
