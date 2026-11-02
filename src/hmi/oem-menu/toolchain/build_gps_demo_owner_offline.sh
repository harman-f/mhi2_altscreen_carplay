#!/usr/bin/env bash
# Build only. Existing HARMAN DIO owner/loader must call exported entry points
# and supply real iAP2 session events, DSI speed and original NMEA send hook.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CC="${CC:-arm-unknown-nto-qnx6.5.0eabi-gcc}"
OUT="${1:-/out}"
mkdir -p "$OUT"
"$CC" -O2 -std=gnu99 -Wall -Wextra -Werror -fPIC -shared \
    -I"$ROOT/control/native" \
    "$ROOT/control/native/mibr_gps_demo.c" \
    "$ROOT/control/native/mibr_gps_demo_owner.c" \
    "$ROOT/control/native/mibr_gps_demo_mode.c" \
    -o "$OUT/libmibr-gps-demo-owner.so"
printf 'BUILT GPS_DEMO_OWNER_SOURCE_ONLY: %s\n' "$OUT/libmibr-gps-demo-owner.so"
printf 'NOT LOADED, NOT ACTIVE, NOT AN INSTALLABLE PACKAGE\n'
