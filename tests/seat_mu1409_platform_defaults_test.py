#!/usr/bin/env python3
"""MU1409 SEAT/CUPRA view calibration: validate the shipped platform-defaults rectangles.

GEN2 reads safe_wide/safe_voll/safe_center from config/platform/defaults.conf
(apply_safe_override in libaltscreen111_gen2.c), installed from
modules/navigation/source/platform-defaults/seat-mu1409.conf.
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
CONF = ROOT / "modules/navigation/source/platform-defaults/seat-mu1409.conf"
W, H = 1010, 376
vals = {}
for line in CONF.read_text().splitlines():
    if line.strip() and not line.startswith("#"):
        k, v = line.split("=", 1)
        if k.strip().startswith("safe_"):  # key.* / zoom.* input-mapping lines are covered elsewhere
            vals[k.strip()] = tuple(int(x) for x in v.split(","))
assert set(vals) == {"safe_wide", "safe_voll", "safe_center"}, vals
assert vals["safe_wide"] == (151, 56, 708, 244)
assert vals["safe_voll"] == (264, 56, 482, 244)
assert vals["safe_center"] == (377, 56, 256, 244)
for k, r in vals.items():
    assert len(r) == 4 and r[2] > 0 and r[3] > 0, k
    assert r[0] >= 0 and r[1] >= 0 and r[0] + r[2] <= W and r[1] + r[3] <= H, k
def inside(a, b):
    return a[0] >= b[0] and a[1] >= b[1] and a[0]+a[2] <= b[0]+b[2] and a[1]+a[3] <= b[1]+b[3]
assert inside(vals["safe_center"], vals["safe_voll"]) and inside(vals["safe_voll"], vals["safe_wide"])
print("SEAT_MU1409_PLATFORM_DEFAULTS_TEST=PASS")
