#!/usr/bin/env bash
set -euo pipefail
CC="${CC:-arm-unknown-nto-qnx6.5.0eabi-gcc}"
OUT="${1:-build/libmibr_isotx2_guard.so}"
mkdir -p "$(dirname "$OUT")"
"$CC" -shared -fPIC -include stddef.h -D_QNX_SOURCE \
  -O2 -g -std=gnu99 -Wall -Wextra -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 \
  -Isrc/native/altscreen111-gen2/include \
  src/native/altscreen111-gen2/src/alt111_native_gate.c \
  -Wl,-soname,libmibr_isotx2_guard.so -lsocket -lc -o "$OUT"
test -s "$OUT"
