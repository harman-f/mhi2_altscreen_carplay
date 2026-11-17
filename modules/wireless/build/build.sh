#!/usr/bin/env bash
# HOST BUILD ONLY. Never run on a head unit.
set -euo pipefail
OUT=${1:?Usage: build.sh absolute-output-directory [host|qnx]}
MODE=${2:-host}
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
case "$OUT" in /*) ;; *) echo 'Output must be absolute' >&2; exit 2;; esac
mkdir -p "$OUT"
case "$MODE" in
  host) CC=${CC:-cc}; AR=${AR:-ar} ;;
  qnx) CC=${CC:-arm-unknown-nto-qnx6.5.0eabi-gcc}; AR=${AR:-arm-unknown-nto-qnx6.5.0eabi-ar} ;;
  *) echo 'Unknown build mode' >&2; exit 2 ;;
esac
FLAGS=(-std=c99 -Wall -Wextra -Werror -pedantic -O2 -fno-common)
if [[ "$MODE" == qnx ]]; then FLAGS+=(-march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 -DMIBR_WCP_TARGET_QNX); fi
for unit in wcp_control wcp_protocol wcp_config wcp_target_abi iap2_5703_encoder wcp_wifi_reply; do
  "$CC" "${FLAGS[@]}" -I "$ROOT/modules/wireless/source" -c \
    "$ROOT/modules/wireless/source/$unit.c" -o "$OUT/$unit.o"
done
# The pinned target binutils predates deterministic ar's D option.
# Repeatable commands do not imply byte-identical archive metadata.
"$AR" rcs "$OUT/libmibr-wireless.a" "$OUT/wcp_control.o" "$OUT/wcp_protocol.o" "$OUT/wcp_config.o" "$OUT/wcp_target_abi.o" "$OUT/iap2_5703_encoder.o" "$OUT/wcp_wifi_reply.o"
for fixture in wireless reinit protocol_overlap wifi_reply; do
  case "$fixture" in
    wireless) executable=wireless-fixtures ;;
    *) executable="wireless-$fixture" ;;
  esac
  "$CC" "${FLAGS[@]}" -I "$ROOT/modules/wireless/source" \
    "$ROOT/modules/wireless/tests/test_$fixture.c" "$OUT/libmibr-wireless.a" -o "$OUT/$executable"
  if [[ "$MODE" == host ]]; then "$OUT/$executable"; fi
done
echo "wireless $MODE compile PASS; hardware qualification absent"
