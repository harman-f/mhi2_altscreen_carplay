#!/usr/bin/env bash
set -euo pipefail

QCC="${QCC:-qcc}"
SRC_ROOT="${SRC_ROOT:-src/native/altscreen111-gen2}"
OUT="${1:-build/libaltscreen111.so}"

mkdir -p "$(dirname "$OUT")"

"$QCC"   -shared -fPIC -mfloat-abi=softfp   -O2 -g -std=gnu99 -Wall -Wextra   -I"$SRC_ROOT/include"   "$SRC_ROOT/libaltscreen111_gen2.c"   "$SRC_ROOT/src/alt111_profile.c"   "$SRC_ROOT/src/alt111_control.c"   "$SRC_ROOT/src/alt111_policy.c"   "$SRC_ROOT/src/alt111_video.c"   "$SRC_ROOT/src/alt111_resync.c"   -Wl,-soname,libaltscreen111.so   -lsocket   -o "$OUT"

# Deliberately do not strip the developer artifact.
