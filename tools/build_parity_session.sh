#!/usr/bin/env bash
set -euo pipefail

SRC="${1:-src/native/parity-session/parity_session.c}"
OUT="${2:-build/parity-session}"
CC="${CC:-arm-unknown-nto-qnx6.5.0eabi-gcc}"

mkdir -p "$(dirname "$OUT")"
"$CC"   -include stddef.h -D_QNX_SOURCE   -O2 -g -std=gnu99 -Wall -Wextra   -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16   "$SRC" -lsocket -lc -o "$OUT"

test -s "$OUT"
