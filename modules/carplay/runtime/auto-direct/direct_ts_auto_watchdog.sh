#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init || exit 3

ENABLED=/mnt/app/root/mibr-carplay-autodirect.enabled
PIDFILE=/tmp/mibr-direct-auto-watchdog.pid
SUPHB=/tmp/mibr-direct-auto.heartbeat
DIRECT=/tmp/mibr-isotx2-gate.direct
WATCHLOG=/tmp/mibr-direct-auto-watchdog.log
STALE=0
LAST=""

watch_log(){
  echo "$(timestamp_now) $*" >> "$WATCHLOG" 2>/dev/null || true
}

cleanup(){
  rm -f "$PIDFILE" 2>/dev/null || true
}
trap cleanup 0 1 2 15

if [ -r "$PIDFILE" ]; then
  OLD=$(cat "$PIDFILE" 2>/dev/null)
  if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
    echo "AUTO_DIRECT_WATCHDOG=ALREADY_RUNNING pid=$OLD"
    exit 0
  fi
fi
echo "$$" > "$PIDFILE" || exit 4
watch_log "watchdog started pid=$$"

while [ -e "$ENABLED" ]; do
  if [ -e "$DIRECT" ]; then
    CUR=
    [ -r "$SUPHB" ] && CUR=$(cat "$SUPHB" 2>/dev/null)
    if [ -n "$CUR" ] && [ "$CUR" != "$LAST" ]; then
      LAST=$CUR
      STALE=0
    else
      STALE=$((STALE+1))
    fi

    if [ "$STALE" -ge 5 ]; then
      rm -f "$DIRECT" 2>/dev/null || true
      watch_log "FAILSAFE restored STOCK: supervisor heartbeat stale"
      STALE=0
      LAST=""
    fi
  else
    STALE=0
    [ -r "$SUPHB" ] && LAST=$(cat "$SUPHB" 2>/dev/null)
  fi
  sleep 1
done

rm -f "$DIRECT" 2>/dev/null || true
watch_log "watchdog leaving: enable marker absent; STOCK requested"
exit 0
