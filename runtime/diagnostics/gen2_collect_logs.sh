#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

SELF_DIR=$(cd "$(dirname "$0")" 2>/dev/null && pwd)
MIBR_ROOT=${MIBR_ROOT:-/mnt/app/root/mibr}
OUTDIR=${MIBR_REPORT_DIR:-/mnt/app/root/mibr-gen2-reports}
DIRECT_ROOT=$MIBR_ROOT/logs/direct-ts
STAMP=$(date +%Y%m%d-%H%M%S 2>/dev/null || echo report-$$)
mkdir -p "$OUTDIR" 2>/dev/null || { echo "GEN2_COLLECT_LOGS=FAIL_OUTDIR"; exit 2; }

OUT=$OUTDIR/gen2-report-$STAMP.txt
FULL_ALT=$OUTDIR/altscreen111-$STAMP.log
STATUS_SNAPSHOT=$OUTDIR/gen2-status-$STAMP.txt

[ -r /tmp/altscreen111.log ] && cp /tmp/altscreen111.log "$FULL_ALT" 2>/dev/null || true
[ -r /tmp/mibr-alt111-gen2.status ] && cp /tmp/mibr-alt111-gen2.status "$STATUS_SNAPSHOT" 2>/dev/null || true

{
  echo "=== GEN2 REPORT ==="
  date 2>/dev/null || true
  echo
  [ -x "$SELF_DIR/gen2_status.sh" ] && "$SELF_DIR/gen2_status.sh" 2>/dev/null || true

  echo
  echo "=== dio_manager environment ==="
  DIO=$(pidin ar 2>/dev/null | awk '/[d]io_manager/ {print $1; exit}')
  [ -n "$DIO" ] && pidin -p "$DIO" environment 2>/dev/null |
    grep -E 'LD_PRELOAD|ALTSCREEN111_|IPL_CONFIG' || true

  echo
  echo "=== Auto-Direct runtime ==="
  for p in /tmp/mibr-direct-auto.state /tmp/mibr-direct-auto.heartbeat            /tmp/mibr-direct-auto-supervisor.pid /tmp/mibr-direct-auto-bridge.pid            /tmp/mibr-isotx2-gate.stats; do
    if [ -r "$p" ]; then
      echo "--- $p ---"
      cat "$p" 2>/dev/null || true
    fi
  done

  echo
  echo "=== recent AltScreen log ==="
  tail -400 /tmp/altscreen111.log 2>/dev/null || true

  echo
  echo "=== Auto-Direct master log ==="
  tail -240 "$DIRECT_ROOT/DIRECT-TS.log" 2>/dev/null || true

  echo
  echo "=== newest Auto-Direct run directories ==="
  if [ -d "$DIRECT_ROOT" ]; then
    ls -1dt "$DIRECT_ROOT"/*-auto-direct-* 2>/dev/null | awk 'NR<=4' |
    while read D; do
      [ -n "$D" ] || continue
      echo
      echo "--- RUN $D ---"
      [ -r "$D/SUMMARY.txt" ] && cat "$D/SUMMARY.txt" 2>/dev/null || true
      [ -r "$D/bridge.log" ] && {
        echo "--- bridge.log tail ---"
        tail -160 "$D/bridge.log" 2>/dev/null || true
      }
    done
  fi
} > "$OUT"

sync 2>/dev/null || true
echo "GEN2_COLLECT_LOGS=PASS"
echo "report=$OUT"
[ -r "$FULL_ALT" ] && echo "full_altscreen_log=$FULL_ALT"
[ -r "$STATUS_SNAPSHOT" ] && echo "status_snapshot=$STATUS_SNAPSHOT"
