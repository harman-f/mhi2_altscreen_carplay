#!/usr/bin/env bash
set -euo pipefail
# Run only inside the pinned QNX 6.5 ARMv7 toolchain container.
QCC="${QCC:-qcc}"
OUT="${1:-build/keypanel}"
mkdir -p "$OUT"
"$QCC" -O2 -std=gnu99 -mfloat-abi=softfp -Wall -Wextra \
  modules/broker/source/keypanel/mibr_keypanel_native.c \
  -o "$OUT/mibr-keypanel-native" -lsocket