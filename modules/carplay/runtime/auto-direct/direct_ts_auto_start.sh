#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init || { echo "AUTO_DIRECT_START=FAIL_RUNTIME"; exit 3; }

ENABLED=/mnt/app/root/mibr-carplay-autodirect.enabled
SUP=$BASE/scripts/direct_ts_auto_supervisor.sh
WD=$BASE/scripts/direct_ts_auto_watchdog.sh
SUPPID=/tmp/mibr-direct-auto-supervisor.pid
WDPID=/tmp/mibr-direct-auto-watchdog.pid
D2_PERSIST=/mnt/app/root/mibr-alt111-keyframe-policy.enabled
D2_SESSION=/tmp/mibr-alt111-keyframe-policy.enabled

# Compatibility bridge: current source reads the persistent marker directly;
# older vehicle-tested GEN2 binaries read the volatile session marker.
if [ -e "$D2_PERSIST" ]; then
  touch "$D2_SESSION" 2>/dev/null || true
else
  rm -f "$D2_SESSION" 2>/dev/null || true
fi

[ -e "$ENABLED" ] || {
  echo "AUTO_DIRECT_START=DISABLED"
  exit 20
}
[ -x "$SUP" ] || { echo "AUTO_DIRECT_START=FAIL_SUPERVISOR_MISSING"; exit 21; }
[ -x "$WD" ] || { echo "AUTO_DIRECT_START=FAIL_WATCHDOG_MISSING"; exit 22; }
[ -x "$BASE/bin/direct-ts-remux" ] || { echo "AUTO_DIRECT_START=FAIL_BRIDGE_MISSING"; exit 23; }
[ -x "$BASE/scripts/writev_gate.sh" ] || { echo "AUTO_DIRECT_START=FAIL_GATE_CONTROL_MISSING"; exit 24; }

if ! runtime_find_cmd on >/dev/null 2>&1; then
  echo "AUTO_DIRECT_START=FAIL_ON_MISSING"
  exit 25
fi

SUPLIVE=0
if [ -r "$SUPPID" ]; then
  P=$(cat "$SUPPID" 2>/dev/null)
  [ -n "$P" ] && kill -0 "$P" 2>/dev/null && SUPLIVE=1
fi
if [ "$SUPLIVE" -eq 0 ]; then
  rm -f "$SUPPID" 2>/dev/null || true
  on -d -f mmx /bin/ksh "$SUP" >/tmp/mibr-direct-auto-supervisor-launch.log 2>&1 || {
    echo "AUTO_DIRECT_START=FAIL_SUPERVISOR_LAUNCH"
    exit 26
  }
fi

WDLIVE=0
if [ -r "$WDPID" ]; then
  P=$(cat "$WDPID" 2>/dev/null)
  [ -n "$P" ] && kill -0 "$P" 2>/dev/null && WDLIVE=1
fi
if [ "$WDLIVE" -eq 0 ]; then
  rm -f "$WDPID" 2>/dev/null || true
  on -d -f mmx /bin/ksh "$WD" >/tmp/mibr-direct-auto-watchdog-launch.log 2>&1 || {
    echo "AUTO_DIRECT_START=FAIL_WATCHDOG_LAUNCH"
    exit 27
  }
fi

N=0
while [ "$N" -lt 8 ]; do
  SUPLIVE=0
  WDLIVE=0
  if [ -r "$SUPPID" ]; then
    P=$(cat "$SUPPID" 2>/dev/null)
    [ -n "$P" ] && kill -0 "$P" 2>/dev/null && SUPLIVE=1
  fi
  if [ -r "$WDPID" ]; then
    P=$(cat "$WDPID" 2>/dev/null)
    [ -n "$P" ] && kill -0 "$P" 2>/dev/null && WDLIVE=1
  fi
  [ "$SUPLIVE" -eq 1 ] && [ "$WDLIVE" -eq 1 ] && {
    echo "AUTO_DIRECT_START=PASS"
    cat "$SUPPID" 2>/dev/null | awk '{print "supervisor_pid="$1}'
    cat "$WDPID" 2>/dev/null | awk '{print "watchdog_pid="$1}'
    exit 0
  }
  sleep 1
  N=$((N+1))
done

echo "AUTO_DIRECT_START=FAIL_NOT_ALIVE supervisor=$SUPLIVE watchdog=$WDLIVE"
exit 28
