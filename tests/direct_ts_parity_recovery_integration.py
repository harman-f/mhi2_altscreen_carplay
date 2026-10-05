#!/usr/bin/env python3
"""Deterministic source-gap recovery test for direct-ts-parity.

The test intentionally skips source ordinals 3 and then sends predictive AUs
before a fresh IDR. The parity bridge must not resume that broken predictive
chain. It may preserve an already-started PES tail, but the post-gap P-frames
must not be emitted and the fresh IDR must restart with TS discontinuity +
random-access flags.
"""
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
PORT = 21988

def sc(nal: bytes) -> bytes:
    return b"\x00\x00\x00\x01" + nal

SPS = sc(b"\x67\x42\x00\x1f\xe5\x88\x68")
PPS = sc(b"\x68\xce\x06\xe2")
IDR1 = sc(b"\x65\x91\x01")
P2 = sc(b"\x41\x92\x02")
P4 = sc(b"\x41\x94\x04")
P5 = sc(b"\x41\x95\x05")
IDR6 = sc(b"\x65\x96\x06")
P7 = sc(b"\x41\x97\x07")

def source_ts(frame_index: int, hz: int = 240, sec0: int = 2000) -> bytes:
    sec = sec0 + frame_index // hz
    rem = frame_index % hz
    frac = (rem * (1 << 32)) // hz
    return struct.pack("<II", frac, sec)

def m1au(seq: int, payload: bytes, idr: bool = False, priming: bool = False) -> bytes:
    flags = (1 if idr else 0) | (2 if priming else 0)
    header = struct.pack(
        ">4sHHIIQQQQ",
        b"M1AU", 1, 56, flags, len(payload), 1, 1, 1, seq
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bridge")
    args = ap.parse_args()

    # seq=3 is deliberately absent. seq=4 and seq=5 are predictive and must
    # be suppressed until seq=6 supplies a clean IDR.
    records = [
        m1au(1, SPS + PPS + IDR1, idr=True, priming=True),
        m1au(2, P2),
        m1au(4, P4),
        m1au(5, P5),
        m1au(6, SPS + PPS + IDR6, idr=True),
        m1au(7, P7),
    ]

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "recovery.ts"
        ready = threading.Event()
        th = threading.Thread(target=serve, args=(records, ready), daemon=True)
        th.start()
        assert ready.wait(3)

        cp = subprocess.run(
            [args.bridge, f"tcp://127.0.0.1:{PORT}", str(out)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=15, check=False,
        )
        th.join(2)
        if cp.returncode:
            raise SystemExit(
                f"bridge rc={cp.returncode}\nSTDOUT={cp.stdout}\nSTDERR={cp.stderr}"
            )

        data = out.read_bytes()
        assert data and len(data) % BLOCK == 0
        packets = [data[i:i+TS] for i in range(0, len(data), TS)]
        assert all(p[0] == 0x47 for p in packets)

        video = [p for p in packets if pid(p) == 0x0011]
        starts = [i for i,p in enumerate(video) if p[1] & 0x40]
        pes = []
        start_packets = []
        for n,start in enumerate(starts):
            end = starts[n+1] if n+1 < len(starts) else len(video)
            raw = bytearray()
            for p in video[start:end]:
                off = payload_offset(p)
                assert off is not None and off <= TS
                raw.extend(p[off:])
            assert raw[:4] == b"\x00\x00\x01\xe0"
            header_end = 9 + raw[8]
            pes.append(bytes(raw[header_end:]))
            start_packets.append(video[start])

        p4 = b"\x00\x00\x00\x01\x41\x94\x04"
        p5 = b"\x00\x00\x00\x01\x41\x95\x05"
        idr6 = b"\x00\x00\x00\x01\x65\x96\x06"
        assert not any(p4 in payload for payload in pes), "post-gap P4 leaked"
        assert not any(p5 in payload for payload in pes), "post-gap P5 leaked"

        resumed = [i for i,payload in enumerate(pes) if idr6 in payload]
        assert len(resumed) == 1, ("fresh IDR not emitted exactly once", len(resumed))
        first = start_packets[resumed[0]]
        assert ((first[3] >> 4) & 3) == 3, "fresh IDR missing adaptation field"
        assert first[4] >= 1, "fresh IDR adaptation field too short"
        assert (first[5] & 0xC0) == 0xC0, (
            "fresh IDR must assert discontinuity+random_access", hex(first[5])
        )

        assert "PARITY_SAFE_RECOVERY reason=sequence" in cp.stderr, cp.stderr
        print("PARITY_RECOVERY_INTEGRATION=PASS")
        print(
            f"blocks={len(data)//BLOCK} video_pes={len(starts)} "
            f"fresh_idr_index={resumed[0]}"
        )

if __name__ == "__main__":
    main()
