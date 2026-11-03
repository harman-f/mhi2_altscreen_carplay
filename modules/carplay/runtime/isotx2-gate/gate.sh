#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
MARKER=/tmp/mibr-isotx2-gate.direct
RESET=/tmp/mibr-isotx2-gate.reset
STATS=/tmp/mibr-isotx2-gate.stats
LOG=/tmp/mibr-isotx2-gate.log

case "${1:-status}" in
  direct)
    touch "$MARKER" || exit 10
    echo "isoTX2 gate: DIRECT requested (stock DisplayManager writev payloads will be swallowed)"
    ;;
  stock)
    rm -f "$MARKER" 2>/dev/null || true
    echo "isoTX2 gate: STOCK requested (DisplayManager writev payloads pass through)"
    ;;
  reset)
    touch "$RESET" || exit 11
    echo "isoTX2 gate: counter reset requested; applied on next tracked open/writev"
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
  echo "gate_stats=absent (interposer not loaded or no stats published yet)"
fi
if [ -r "$LOG" ]; then
  echo "--- gate log tail ---"
  tail -20 "$LOG" 2>/dev/null || cat "$LOG"
fi
