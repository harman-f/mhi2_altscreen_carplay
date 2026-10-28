#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Host-only generator; first-party uniform-color artwork, no OEM pixels.
import argparse, pathlib, struct, zlib
def chunk(kind,data):
    return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
def png():
    raw=(b'\0'+bytes((220,35,55,255))*8)*32
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack(">IIBBBBB",8,32,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
if __name__=='__main__':
    ap=argparse.ArgumentParser(description="Generate the optional project-owned red thumb; no target installation.")
    ap.add_argument("--out",required=True,type=pathlib.Path);args=ap.parse_args()
    args.out.write_bytes(png())
