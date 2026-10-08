#!/usr/bin/env python3
"""Fail-closed fixture replay CLI checks; no MOST or OEM component exercised."""
import argparse
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("bridge", type=Path)
parser.add_argument("owner", type=Path)
args = parser.parse_args()

bad = [
    ([str(args.bridge), "fixture:/tmp/bogus.m1au", "/dev/mlb/isoTX2"], 64),
    ([str(args.bridge), "fixture:/tmp/bogus.m1au", "/tmp/parity-must-not-create.ts"], 64),
    ([str(args.owner), "--fixture", str(args.bridge),
      "fixture:/tmp/bogus.m1au", "/dev/mlb/isoTX2", "150"], 64),
    ([str(args.owner), "--fixture", str(args.bridge),
      "tcp://127.0.0.1:19820", "/dev/mlb/isoTX2", "150"], 64),
    ([str(args.owner), "--fixture", str(args.bridge),
      "fixture:/tmp/bogus.m1au", "/tmp/parity-must-not-create.ts", "150"], 64),
    ([str(args.owner), "--fixture", str(args.bridge),
      "fixture:/tmp/bogus.m1au", "/dev/mlb/isoTX2", "0"], 65),
]
for cmd, expected in bad:
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    assert r.returncode == expected, (cmd, r.returncode, r.stderr.decode(errors="replace"))
assert not Path("/tmp/parity-must-not-create.ts").exists()

bridge = Path("src/native/direct-ts-parity/direct_ts_parity.c").read_text()
owner = Path("src/native/parity-session/parity_session.c").read_text()
for needle in (
    "MIBR_FIXTURE_BYTES 23275739u",
    "MIBR_FIXTURE_FRAMES 3600u",
    "MIBR_FIXTURE_FPS 30u",
    "MIBR_FIXTURE_GOP 20u",
    "MIBR_FIXTURE_MAX_LATE_US 100000u",
    'fixture_mode ? open_fixture(input) : connect_input(input)',
    "fixture_pace(&fixture,seq,flags,frac,sec)",
    "M1AU_FLAG_TIME_PRESENT",
    'if(!fixture_mode && !prev_stream)request_keyframe',
):
    assert needle in bridge, needle
for needle in (
    'fixture_mode=(argc==6 && !strcmp(argv[1],"--fixture"))',
    "FIXTURE_MIN_SECONDS 125L",
    "FIXTURE_MAX_SECONDS 180L",
    "fixture_ready(input)",
    "if(fixture_mode && source_ready())",
    "if(!gate_owned())",
    "bridge_identity(bridge)",
    "stop_bridge(bridge_pid)",
    "restore_ok = backend_restore() == 0",
):
    assert needle in owner, needle

print("MU1440_FIXTURE_REPLAY_HOST=PASS bounded fixture mode + negative CLI")
