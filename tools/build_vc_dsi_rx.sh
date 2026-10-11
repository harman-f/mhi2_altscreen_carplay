#!/bin/sh
# Run QNX build ONLY inside the same pinned QNX 6.5 ARMv7 container as build_keypanel_native.sh.
set -eu
QCC="${QCC:-qcc}"
OUT="${1:-build/vc-dsi-rx}"
mkdir -p "$OUT"
"$QCC" -O2 -std=gnu99 -mfloat-abi=softfp -Wall -Wextra \
  src/native/vc_trace/mibr_dsi_rx.c -o "$OUT/mibr-dsi-rx" -lsocket

"$QCC" -O2 -std=gnu99 -mfloat-abi=softfp -Wall -Wextra \
  src/native/vc_trace/mibr_fileeq.c -o "$OUT/mibr-fileeq"
