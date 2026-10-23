#!/usr/bin/env bash
set -euo pipefail

QCC="${QCC:-qcc}"
SRC_ROOT="${SRC_ROOT:-src/native/altscreen111-gen2}"
VDATA="${VDATA:-src/native/vehicle-data}"
OUT="${1:-build/libaltscreen111.so}"

mkdir -p "$(dirname "$OUT")"

# r35: upstream recipe plus the vehicle-data module (iap2_gps_data_send interposer, default off).
"$QCC" -shared -fPIC -mfloat-abi=softfp -O2 -g -std=gnu99 -Wall -Wextra \
  -DMIBR_SHA256_LIBRARY_ONLY -I"$SRC_ROOT/include" -Isrc/native/alt111-settings/include -I"$VDATA" \
  "$SRC_ROOT/libaltscreen111_gen2.c" "$SRC_ROOT/src/alt111_profile.c" \
  "$SRC_ROOT/src/alt111_control.c" "$SRC_ROOT/src/alt111_zoom.c" \
  "$SRC_ROOT/src/alt111_zoom_debugspi.c" "$SRC_ROOT/src/alt111_policy.c" \
  "$SRC_ROOT/src/alt111_video.c" "$SRC_ROOT/src/alt111_resync.c" \
  "$VDATA/mvs_core.c" "$VDATA/mibr_vdata.c" "$VDATA/mibr_vstatus.c" "$VDATA/mibr_vdata_hook.c" \
  src/native/alt111-settings/settings_core.c src/native/alt111-settings/settings_posix.c \
  src/native/sha256sum-compat/sha256sum_compat.c \
  -Wl,-soname,libaltscreen111.so -lsocket -o "$OUT"

# Deliberately do not strip the developer artifact.
