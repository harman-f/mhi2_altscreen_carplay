#!/usr/bin/env bash
# Compile existing pure/native adapter regressions against the published core.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
CC=${CC:-cc}
OUT=${GEN2_HOST_OUT:-build/gen2-host}
mkdir -p "$OUT"
G=src/native/altscreen111-gen2
I=(-I"$G/include" -Isrc/native/alt111-settings/include -Isrc/native/vehicle-data)
F=(-O2 -g -std=gnu99 -Wall -Wextra -Werror -DALT111_SETTINGS_TEST -DMIBR_SHA256_LIBRARY_ONLY)
CORE=(src/native/alt111-settings/settings_core.c src/native/alt111-settings/settings_posix.c
      "$G/src/alt111_policy.c" src/native/sha256sum-compat/sha256sum_compat.c)
PURE=("$G/src/alt111_profile.c" "$G/src/alt111_control.c" "$G/src/alt111_resync.c"
      "$G/src/alt111_video.c" "$G/src/alt111_zoom.c" "$G/src/alt111_zoom_debugspi.c")
for name in settings_core gen2_settings_session policy video_queue_recovery resync_bridge tcp_nodelay; do
  EXTRA=()
  if [[ "$name" == gen2_settings_session ]]; then
    # The included target adapter has optional diagnostic writes and bounded
    # snprintf copies reported by modern fortified host libc. Keep these
    # existing warnings visible; the constructor is unused in the host harness.
    EXTRA=(-Wno-error=unused-result -Wno-error=format-truncation -Wno-unused-function)
  fi
  "$CC" "${F[@]}" "${EXTRA[@]}" "${I[@]}" "tests/alt111_${name}_test.c" "${CORE[@]}" "${PURE[@]}" \
    -pthread -ldl -lm -o "$OUT/$name"
  "$OUT/$name"
done
bash tools/test_alt111_zoom_host.sh
python3 -B tests/alt111_settings_integration.py
echo 'GEN2_COMPONENTS_HOST=PASS host_only=1'
