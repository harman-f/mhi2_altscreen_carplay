#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

# BEGIN_TARGET_ENV -- proven installed MU1440 runtime paths
export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/media/gracenote/bin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin:/mnt/app/armle/usr/sbin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1
# END_TARGET_ENV
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
  ''|*[!0-9]*) echo "usage: $0 [SECONDS 0|5..7200]|stop|restore-stock"; exit 2 ;;
  *) LIMIT=${1:-120} ;;
esac
# No tuning scalar is hard-coded here. The shared validator reads one complete
# layered snapshot; the native owner independently freezes its backend.
if [ "$LIMIT" -ne 0 ]; then
  [ "$LIMIT" -eq 0 ] || { [ "$LIMIT" -ge 5 ] && [ "$LIMIT" -le 7200 ]; } || exit 2
fi
"$HELPER" status || exit 20
[ "$LIMIT" -eq 0 ] && MODE=until-stop || MODE=bounded
echo "PARITY_SESSION=PREFLIGHT mode=$MODE seconds=$LIMIT"
exec "$RUNNER" "$BRIDGE" tcp://127.0.0.1:19820 /dev/mlb/isoTX2 "$LIMIT"
