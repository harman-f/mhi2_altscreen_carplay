#!/usr/bin/env bash
# Reproducible host and QNX6.5 source builds for the MIBR/3 controller.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SRC="$ROOT/src/native/mibr-control"
ALT_ROOT=${ALT111_SOURCE_ROOT:-"$ROOT/src/native"}
OUT=${MIBR_CONTROL_OUT:-"$ROOT/build/mibr-control"}
MODE=${1:-host}
CC=${CC:-cc}
QNX_IMAGE=${MIBR_QNX_IMAGE:-mibr-qnx65-temp:4.9}
QNX_CC=arm-unknown-nto-qnx6.5.0eabi-gcc
INC="-I$ALT_ROOT/altscreen111-gen2/include -I$ALT_ROOT/alt111-settings/include"
CORE=(
  "$ALT_ROOT/alt111-settings/settings_core.c"
  "$ALT_ROOT/alt111-settings/settings_posix.c"
  "$ALT_ROOT/altscreen111-gen2/src/alt111_policy.c"
  "$ALT_ROOT/sha256sum-compat/sha256sum_compat.c"
)
SERVICE=(
  "$SRC/mibr_v3_readonly.c"
  "$SRC/mibr_v3_profile_store.c"
  "$SRC/mibr_v3_recovery_gate.c"
  "$SRC/mibr_v3_runtime_observer.c"
  "$SRC/mibr_v3_qnx_mount.c"
  "$SRC/mibr_v3_service.c"
  "$SRC/mibr_v3_key40.c"
  "$SRC/mibr_v3_input_bridge.c"
  "$SRC/mibr_v3_route_gateway.c"
  "$SRC/mibr_v3_owner_lifecycle.c"
)
HOST_SERVICE=(
  "$SRC/mibr_v3_readonly.c"
  "$SRC/mibr_v3_profile_store.c"
  "$SRC/mibr_v3_recovery_gate.c"
  "$SRC/mibr_v3_runtime_observer.c"
  "$SRC/mibr_v3_service.c"
  "$SRC/mibr_v3_key40.c"
  "$SRC/mibr_v3_input_bridge.c"
  "$SRC/mibr_v3_route_gateway.c"
  "$SRC/mibr_v3_owner_lifecycle.c"
)

mkdir -p "$OUT"
for file in "${CORE[@]}"; do
  [[ -f "$file" ]] || { echo "Missing canonical settings dependency: $file" >&2; exit 2; }
done

case "$MODE" in
  host)
    "$CC" -O2 -g -std=gnu99 -Wall -Wextra -Werror \
      -DALT111_SETTINGS_TEST -DMIBR_SHA256_LIBRARY_ONLY \
      $INC "${HOST_SERVICE[@]}" "${CORE[@]}" -o "$OUT/mibr-v3-service-host"
    "$CC" -O2 -g -std=gnu99 -Wall -Wextra -Werror \
      "$SRC/mibr_v3_client.c" -o "$OUT/mibrctl-v3-host"
    "$CC" -O2 -g -std=gnu99 -Wall -Wextra -Werror \
      "$SRC/mibr_v3_genkey.c" -o "$OUT/mibr-v3-genkey-host"
    echo "HOST_BUILD=PASS output=$OUT"
    ;;
  qnx)
    command -v docker >/dev/null || { echo 'Docker is required for the QNX cross-build.' >&2; exit 2; }
    docker image inspect "$QNX_IMAGE" >/dev/null 2>&1 || {
      echo "QNX image not found: $QNX_IMAGE (see the module build notes)." >&2; exit 2;
    }
    DOCKER_ROOT=$ROOT
    DOCKER_OUT=$OUT
    if command -v cygpath >/dev/null 2>&1; then
      DOCKER_ROOT=$(cygpath -w "$ROOT")
      DOCKER_OUT=$(cygpath -w "$OUT")
    fi
    MSYS_NO_PATHCONV=1 docker run --rm --platform=linux/amd64 \
      -v "$DOCKER_ROOT:/repo:ro" -v "$DOCKER_OUT:/out" \
      --entrypoint /bin/bash "$QNX_IMAGE" -ec '
        R=/repo; S=$R/src/native/mibr-control; A=$R/src/native; T=/tmp/mibr-control-out
        mkdir -p "$T"
        C=arm-unknown-nto-qnx6.5.0eabi-gcc
        I="-I$A/altscreen111-gen2/include -I$A/alt111-settings/include"
        F="-include stddef.h -D_QNX_SOURCE -DMIBR_SHA256_LIBRARY_ONLY -DMIBR_V3_TARGET_STORAGE_QUALIFIED -O2 -std=gnu99 -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16"
        $C $F $I \
          "$S/mibr_v3_readonly.c" "$S/mibr_v3_profile_store.c" \
          "$S/mibr_v3_recovery_gate.c" "$S/mibr_v3_runtime_observer.c" \
          "$S/mibr_v3_qnx_mount.c" "$S/mibr_v3_service.c" \
          "$S/mibr_v3_key40.c" "$S/mibr_v3_input_bridge.c" \
          "$S/mibr_v3_route_gateway.c" "$S/mibr_v3_owner_lifecycle.c" \
          "$A/alt111-settings/settings_core.c" "$A/alt111-settings/settings_posix.c" \
          "$A/altscreen111-gen2/src/alt111_policy.c" \
          "$A/sha256sum-compat/sha256sum_compat.c" \
          -lsocket -lc -o "$T/mibr-v3-service-QNX65-ARMv7-NOT-INSTALL-READY"
        $C -include stddef.h -D_QNX_SOURCE -O2 -std=gnu99 -march=armv7-a \
          -mfloat-abi=softfp -mfpu=vfpv3-d16 "$S/mibr_v3_client.c" \
          -lsocket -lc -o "$T/mibrctl-v3-QNX65-ARMv7-NOT-INSTALL-READY"
        $C -include stddef.h -D_QNX_SOURCE -O2 -std=gnu99 -march=armv7-a \
          -mfloat-abi=softfp -mfpu=vfpv3-d16 "$S/mibr_v3_genkey.c" \
          -lc -o "$T/mibr-v3-genkey-QNX65-ARMv7-NOT-INSTALL-READY"
        $C -include stddef.h -D_QNX_SOURCE -O2 -std=gnu99 -Wall -Wextra -Werror \
          -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 -I"$S" \
          "$S/mibr_key40d.c" "$S/mibr_v3_key40.c" \
          -lsocket -lc -o "$T/mibr-key40d-QNX65-ARMv7-NOT-INSTALL-READY"
        arm-unknown-nto-qnx6.5.0eabi-readelf -h "$T/mibr-v3-service-QNX65-ARMv7-NOT-INSTALL-READY" > /out/SERVICE_ELF_HEADER.txt
        grep -q "Machine:.*ARM" /out/SERVICE_ELF_HEADER.txt
        for f in "$T"/*; do cp "$f" /out/; done
      '
    sha256sum "$OUT"/*QNX65*
    echo "QNX_BUILD=PASS output=$OUT (build-only; not vehicle-qualified)"
    ;;
  qnx-container)
    # Run this mode from inside the pinned QNX toolchain container. It lets a
    # workspace-level build orchestrator share one container invocation across
    # modules instead of starting Docker from inside Docker.
    command -v "$QNX_CC" >/dev/null || { echo "Missing QNX compiler: $QNX_CC" >&2; exit 2; }
    T=${TMPDIR:-/tmp}/mibr-control-out-$$
    mkdir -p "$T"
    F=(-include stddef.h -D_QNX_SOURCE -DMIBR_SHA256_LIBRARY_ONLY
      -DMIBR_V3_TARGET_STORAGE_QUALIFIED -O2 -std=gnu99 -march=armv7-a
      -mfloat-abi=softfp -mfpu=vfpv3-d16)
    "$QNX_CC" "${F[@]}" -I"$ALT_ROOT/altscreen111-gen2/include" \
      -I"$ALT_ROOT/alt111-settings/include" \
      "${SERVICE[@]}" "${CORE[@]}" -lsocket -lc \
      -o "$T/mibr-v3-service-QNX65-ARMv7-NOT-INSTALL-READY"
    "$QNX_CC" -include stddef.h -D_QNX_SOURCE -O2 -std=gnu99 -march=armv7-a \
      -mfloat-abi=softfp -mfpu=vfpv3-d16 "$SRC/mibr_v3_client.c" \
      -lsocket -lc -o "$T/mibrctl-v3-QNX65-ARMv7-NOT-INSTALL-READY"
    "$QNX_CC" -include stddef.h -D_QNX_SOURCE -O2 -std=gnu99 -march=armv7-a \
      -mfloat-abi=softfp -mfpu=vfpv3-d16 "$SRC/mibr_v3_genkey.c" \
      -lc -o "$T/mibr-v3-genkey-QNX65-ARMv7-NOT-INSTALL-READY"
    "$QNX_CC" -include stddef.h -D_QNX_SOURCE -O2 -std=gnu99 -Wall -Wextra -Werror \
      -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 -I"$SRC" \
      "$SRC/mibr_key40d.c" "$SRC/mibr_v3_key40.c" \
      -lsocket -lc -o "$T/mibr-key40d-QNX65-ARMv7-NOT-INSTALL-READY"
    arm-unknown-nto-qnx6.5.0eabi-readelf -h \
      "$T/mibr-v3-service-QNX65-ARMv7-NOT-INSTALL-READY" > "$T/SERVICE_ELF_HEADER.txt"
    grep -q "Machine:.*ARM" "$T/SERVICE_ELF_HEADER.txt"
    cp "$T"/* "$OUT/"
    sha256sum "$OUT"/*QNX65*
    echo "QNX_BUILD=PASS output=$OUT (container mode; build-only; not vehicle-qualified)"
    ;;
  *) echo "Usage: $0 [host|qnx|qnx-container]" >&2; exit 2 ;;
esac
