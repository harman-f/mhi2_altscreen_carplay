#!/usr/bin/env bash
# Compile existing pure/native adapter regressions against the published core.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
CC=${CC:-cc}
OUT=${GEN2_HOST_OUT:-build/gen2-host}
mkdir -p "$OUT"
G=modules/carplay/source/altscreen111-gen2
I=(-I"$G/include" -Imodules/carplay/source/alt111-settings/include -Imodules/carplay/source/vehicle-data -Imodules/carplay/source/display-scaling)
F=(-O2 -g -std=gnu99 -Wall -Wextra -Werror -DALT111_SETTINGS_TEST -DMIBR_SHA256_LIBRARY_ONLY)
CORE=(modules/carplay/source/alt111-settings/settings_core.c modules/carplay/source/alt111-settings/settings_posix.c
      "$G/src/alt111_policy.c" modules/carplay/source/display-scaling/mibr_display_scaling.c
      modules/carplay/source/sha256sum-compat/sha256sum_compat.c)
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
# The lock-diagnostics test includes settings_posix.c itself, so it is built without CORE.
"$CC" "${F[@]}" "${I[@]}" tests/alt111_settings_lock_diagnostics_test.c \
  "${CORE[0]}" "${CORE[@]:2}" -pthread -ldl -lm -o "$OUT/settings_lock_diagnostics"
"$OUT/settings_lock_diagnostics"
# QNX /dev/shmem errno behaviour (vehicle 2026-11-06), injected through an lstat redirect.
"$CC" "${F[@]}" "${I[@]}" tests/alt111_settings_shmem_errno_test.c \
  "${CORE[0]}" "${CORE[@]:2}" -pthread -ldl -lm -o "$OUT/settings_shmem_errno"
"$OUT/settings_shmem_errno"
# SEAT steering-wheel zoom bridge (harman-f PR 72 port; env-gated, Skoda default unchanged).
"$CC" -std=c99 -Wall -Wextra -Werror -I"$G/include" tests/seat_zoom_epoch_test.c -o "$OUT/seat_zoom_epoch"
"$OUT/seat_zoom_epoch"
"$CC" -std=c99 -Wall -Wextra -Werror -pthread -I"$G/include" tests/seat_zoom_auto_context_test.c \
  "$G/src/alt111_zoom.c" -o "$OUT/seat_zoom_auto_context"
"$OUT/seat_zoom_auto_context"
bash tools/test_alt111_zoom_host.sh
python3 -B tests/alt111_settings_integration.py
python3 -B tests/seat_mu1409_platform_defaults_test.py
echo 'GEN2_COMPONENTS_HOST=PASS host_only=1'
