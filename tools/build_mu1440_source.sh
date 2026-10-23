#!/usr/bin/env bash
# Build the current MU1440 source stack inside an already running QNX 6.5 image.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
QNX_CC=${QNX_CC:-arm-unknown-nto-qnx6.5.0eabi-gcc}
OUT=${1:-build/mu1440-source}
if [[ "$OUT" != /* ]]; then OUT="$ROOT/$OUT"; fi
mkdir -p "$OUT"
cd "$ROOT"

command -v "$QNX_CC" >/dev/null || { echo "Missing QNX compiler: $QNX_CC" >&2; exit 2; }

QCC="$QNX_CC" bash tools/build_altscreen111_gen2.sh "$OUT/libaltscreen111.so"
CC="$QNX_CC" bash tools/build_alt111_settings.sh "$OUT/alt111-settings"
CC="$QNX_CC" bash tools/build_direct_ts_parity.sh \
  src/native/direct-ts-parity/direct_ts_parity.c "$OUT/direct-ts-parity"
BRIDGE_IDENTITY_PATH="$OUT/direct-ts-parity" CC="$QNX_CC" \
  bash tools/build_parity_session.sh \
  src/native/parity-session/parity_session.c "$OUT/parity-session"
CC="$QNX_CC" bash tools/build_native_isotx2_guard.sh \
  "$OUT/libmibr_isotx2_guard.so"

# The older, separately owned DisplayManager gate is installed stripped. Build
# and strip in container-local /tmp; the QNX binutils cannot reliably operate
# on a Windows-backed output mount.
TMP_GATE="/tmp/mu1440-libmibr_isotx2_gate-$$.so"
trap 'rm -f "$TMP_GATE"' EXIT
"$QNX_CC" -shared -fPIC -mfloat-abi=softfp -O2 -std=gnu99 -Wall -Wextra \
  src/native/isotx2-gate/isotx2_gate.c \
  -Wl,-soname,libmibr_isotx2_gate.so -o "$TMP_GATE"
arm-unknown-nto-qnx6.5.0eabi-strip -s "$TMP_GATE"
cp "$TMP_GATE" "$OUT/libmibr_isotx2_gate.so"
rm -f "$TMP_GATE"

MIBR_CONTROL_OUT="$OUT/mibr-control" \
ALT111_SOURCE_ROOT="$ROOT/src/native" \
  bash tools/build_mibr_control.sh qnx-container

(
  cd "$OUT"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
  cat SHA256SUMS
)
echo "MU1440_SOURCE_QNX_BUILD=PASS output=$OUT (build-only; not vehicle-qualified)"
