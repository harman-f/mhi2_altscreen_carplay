#!/usr/bin/env bash
# Workstation-only regressions. No target commands or vehicle access.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
CC=${CC:-cc}
OUT=${PARITY_HOST_OUT:-build/parity-host}
mkdir -p "$OUT"
"$CC" -O2 -g -std=gnu99 -Wall -Wextra -Werror \
  src/native/direct-ts-parity/direct_ts_parity.c -pthread -lm -o "$OUT/direct-ts-parity"
"$OUT/direct-ts-parity" --self-test
for name in regressions clock_review; do
  "$CC" -O2 -g -std=gnu99 -Wall -Wextra -Werror \
    "tests/direct_ts_parity_$name.c" -pthread -lm -o "$OUT/$name"
  "$OUT/$name"
done
for name in host_integration recovery_integration eof_integration exit_review; do
  python3 -B "tests/direct_ts_parity_$name.py" "$OUT/direct-ts-parity"
done
python3 -B tests/parity_session_lifecycle.py
python3 -B tests/alt111_native_gate_integration.py
python3 -B tests/parity_session_logging.py
python3 -B tools/check_mu1440_target_shell.py --self-test --check \
  runtime/parity/parity_drive_supervisor.sh runtime/parity/parity_drive_enable.sh \
  runtime/parity/parity_drive_disable.sh runtime/parity/parity_drive_status.sh \
  runtime/parity/parity_status.sh runtime/parity/parity_profile.sh \
  runtime/parity/parity_session.sh runtime/parity/master-script-basenames.sh \
  deployment/mu1440-parity-drive-v1/session-logging.sh
if command -v ffmpeg >/dev/null 2>&1; then
  python3 -B tests/direct_ts_parity_decode_integration.py "$OUT/direct-ts-parity" "$OUT/decode"
else
  echo 'PARITY_DECODE_INTEGRATION=NOT_RUN requires ffmpeg with libx264'
fi
echo 'PARITY_HOST_SOURCE=PASS host_only=1'
