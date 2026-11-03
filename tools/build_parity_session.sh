#!/usr/bin/env bash
set -euo pipefail

SRC="${1:-modules/carplay/source/parity-session/parity_session.c}"
OUT="${2:-build/parity-session}"
CC="${CC:-arm-unknown-nto-qnx6.5.0eabi-gcc}"

mkdir -p "$(dirname "$OUT")"
BRIDGE_IDENTITY_PATH="${BRIDGE_IDENTITY_PATH:-$(dirname "$OUT")/direct-ts-parity}"
test -s "$BRIDGE_IDENTITY_PATH"
BRIDGE_SHA=$(sha256sum "$BRIDGE_IDENTITY_PATH" | awk '{print $1}')
"$CC" -include stddef.h -D_QNX_SOURCE -DMIBR_SHA256_LIBRARY_ONLY \
  "-DMIBR_EXPECTED_BRIDGE_SHA256=\"$BRIDGE_SHA\"" \
  -O2 -g -std=gnu99 -Wall -Wextra -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 \
  -Imodules/carplay/source/altscreen111-gen2/include -Imodules/carplay/source/alt111-settings/include \
  "$SRC" modules/carplay/source/alt111-settings/settings_core.c modules/carplay/source/alt111-settings/settings_posix.c \
  modules/carplay/source/altscreen111-gen2/src/alt111_policy.c \
  modules/carplay/source/sha256sum-compat/sha256sum_compat.c -lsocket -lc -o "$OUT"

test -s "$OUT"
