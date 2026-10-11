#!/usr/bin/env python3
"""Merge QNX-monotonic keypanel NOTE/EVENT and raw DSI receive chunk chronology.

This does NOT decode the proprietary DSITracer client protocol. Chunk receive time
is an upper-bound observation of delivery, not the emission time of a DSI method.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

STAMP = re.compile(r'^\[(\d+)ms\] (NOTE|EVENT|RELATED) (.*)$')


def merged(keypanel: str, chunks: str):
    events = []
    for n, line in enumerate(keypanel.splitlines(), 1):
        m = STAMP.match(line)
        if m:
            events.append((int(m[1]), 0, n, 'KEYPANEL_' + m[2], m[3]))
    dsi = csv.DictReader(chunks.splitlines(), dialect='excel-tab')
    if dsi.fieldnames != ['mono_ms', 'offset', 'bytes']:
        raise ValueError('Expected dsi-chunks.tsv header: mono_ms offset bytes')
    for n, row in enumerate(dsi, 2):
        ms, offset, size = (int(row[k]) for k in ('mono_ms', 'offset', 'bytes'))
        if ms < 0 or offset < 0 or size <= 0:
            raise ValueError(f'Bad chunk {n}')
        events.append((ms, 1, n, 'DSI_RECV_CHUNK', f'raw_offset={offset} received_bytes={size} PROTOCOL_UNDECODED'))
    return sorted(events)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('keypanel_combined', type=Path)
    ap.add_argument('dsi_chunks', type=Path)
    ap.add_argument('--out', type=Path, default=None)
    a = ap.parse_args()
    data = merged(a.keypanel_combined.read_text(errors='replace'), a.dsi_chunks.read_text())
    out = a.out.open('w', newline='') if a.out else sys.stdout
    try:
        w = csv.writer(out, delimiter='\t', lineterminator='\n')
        w.writerow(('mono_ms', 'origin', 'detail'))
        for ms, _, _, origin, detail in data:
            w.writerow((ms, origin, detail))
    finally:
        if a.out: out.close()

if __name__ == '__main__':
    main()
