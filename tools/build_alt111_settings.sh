#!/usr/bin/env bash
set -euo pipefail
CC="${CC:-arm-unknown-nto-qnx6.5.0eabi-gcc}"
OUT="${1:-build/alt111-settings}"
# CI checks generated metadata on the host; the pinned compiler image need
# not supply Python as a target build dependency.
if command -v python3 >/dev/null 2>&1; then
  python3 tools/generate_alt111_settings.py --check
fi
mkdir -p "$(dirname "$OUT")"
"$CC" -include stddef.h -D_QNX_SOURCE -DMIBR_SHA256_LIBRARY_ONLY \
  -O2 -g -std=gnu99 -Wall -Wextra -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 \
  -Imodules/carplay/source/altscreen111-gen2/include -Imodules/carplay/source/alt111-settings/include \
  modules/carplay/source/alt111-settings/settings_cli.c modules/carplay/source/alt111-settings/settings_core.c \
  modules/carplay/source/alt111-settings/settings_posix.c modules/carplay/source/altscreen111-gen2/src/alt111_policy.c \
  modules/carplay/source/sha256sum-compat/sha256sum_compat.c -lc -o "$OUT"
test -s "$OUT"
