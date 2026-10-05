#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
BASE=/mnt/app/root/altscreen-u2
RUNNER=$BASE/bin/parity-session
BRIDGE=$BASE/bin/direct-ts-parity
HELPER=$BASE/bin/alt111-settings
[ -x "$RUNNER" ] && [ -x "$BRIDGE" ] && [ -x "$HELPER" ] || {
  echo "PARITY_SESSION=FAIL missing_native_component"; exit 10;
}
case "${1:-120}" in
  stop) exec "$RUNNER" --stop ;;
  restore-stock) exec "$RUNNER" --restore-stock ;;
  ''|*[!0-9]*) echo "usage: $0 [SECONDS 5..600]|stop|restore-stock"; exit 2 ;;
  *) LIMIT=${1:-120} ;;
esac
# No tuning scalar is hard-coded here. The shared validator reads one complete
# layered snapshot; the native owner independently freezes its backend.
[ "$LIMIT" -ge 5 ] && [ "$LIMIT" -le 600 ] || exit 2
"$HELPER" status || exit 20
echo "PARITY_SESSION=PREFLIGHT seconds=$LIMIT"
exec "$RUNNER" "$BRIDGE" tcp://127.0.0.1:19820 /dev/mlb/isoTX2 "$LIMIT"
