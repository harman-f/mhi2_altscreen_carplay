#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
. /mnt/app/root/altscreen-u2/scripts/common.sh

MARKER=/tmp/mibr-isotx2-gate.direct
RESET=/tmp/mibr-isotx2-gate.reset
STATS=/tmp/mibr-isotx2-gate.stats
LOGFILE=/tmp/mibr-isotx2-gate.log

case "${1:-status}" in
  direct)
    [ -r "$STATS" ] || {
      echo "FAIL gate stats absent; DisplayManager interposer not proven loaded"
      exit 20
    }
    grep -q '^loaded=1$' "$STATS" || {
      echo "FAIL gate stats do not report loaded=1"
      exit 21
    }
    touch "$MARKER" || exit 22
    echo "isoTX2 gate: DIRECT requested"
    ;;
  stock)
    rm -f "$MARKER" 2>/dev/null || true
    echo "isoTX2 gate: STOCK requested"
    ;;
  reset)
    touch "$RESET" || exit 23
    echo "isoTX2 gate: counter reset requested"
    ;;
  status)
    ;;
  *)
    echo "Usage: $0 {direct|stock|reset|status}"
    exit 2
    ;;
esac

[ -e "$MARKER" ] && echo "requested_mode=DIRECT" || echo "requested_mode=STOCK"
if [ -r "$STATS" ]; then
  echo "--- gate stats ---"
  cat "$STATS"
else
  echo "gate_stats=absent"
fi
if [ -r "$LOGFILE" ]; then
  echo "--- gate log tail ---"
  tail -20 "$LOGFILE" 2>/dev/null || cat "$LOGFILE"
fi
