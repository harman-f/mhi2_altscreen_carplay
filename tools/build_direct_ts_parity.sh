#!/usr/bin/env bash
set -euo pipefail

SRC="${1:-src/native/direct-ts-parity/direct_ts_parity.c}"
OUT="${2:-build/direct-ts-parity}"
CC="${CC:-arm-unknown-nto-qnx6.5.0eabi-gcc}"

printf '#include <stddef.h>\n#include <pthread.h>\nint main(void){pthread_mutex_t m=PTHREAD_MUTEX_INITIALIZER;return pthread_mutex_lock(&m);}\n' | "$CC" \
  -include stddef.h -D_QNX_SOURCE -O2 \
  -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 \
  -x c - -lsocket -o /tmp/mibr-qnx-parity-link-smoke

mkdir -p "$(dirname "$OUT")"
"$CC" \
  -include stddef.h -D_QNX_SOURCE \
  -O2 -g -std=gnu99 -Wall -Wextra \
  -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 \
  "$SRC" -lsocket -lm -lc -o "$OUT"

test -s "$OUT"
