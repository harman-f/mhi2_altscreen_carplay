#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init || { echo "AUTO_DIRECT_STATUS=FAIL_RUNTIME"; exit 3; }

ENABLED=/mnt/app/root/mibr-carplay-autodirect.enabled
SUPPID=/tmp/mibr-direct-auto-supervisor.pid
WDPID=/tmp/mibr-direct-auto-watchdog.pid
BRIDGEPID=/tmp/mibr-direct-auto-bridge.pid

echo "=== AUTO DIRECT ==="
[ -e "$ENABLED" ] && echo "enabled=1" || echo "enabled=0"
[ -r /tmp/mibr-direct-auto.state ] && echo "state=$(cat /tmp/mibr-direct-auto.state 2>/dev/null)" || echo "state=missing"

for X in supervisor:$SUPPID watchdog:$WDPID bridge:$BRIDGEPID; do
  NAME=${X%%:*}
  PF=${X#*:}
  P=
  [ -r "$PF" ] && P=$(cat "$PF" 2>/dev/null)
  if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then
    echo "${NAME}_pid=$P alive=1"
  else
    echo "${NAME}_pid=${P:-NONE} alive=0"
  fi
done

load_altscreen_config >/dev/null 2>&1 || true

echo
echo "=== FRAME PACING ==="
echo "source_max_fps=${ALTSCREEN111_FPS:-UNKNOWN}"
echo "direct_output_fps=${DIRECT_OUTPUT_FPS:-UNKNOWN}"
echo "direct_pace=${DIRECT_PACE:-UNKNOWN}"
echo "direct_pace_buffer=${DIRECT_PACE_BUFFER:-UNKNOWN}"
[ -r "$DIRECT_FPS_OVERRIDE_FILE" ] && echo "direct_fps_override=$(cat "$DIRECT_FPS_OVERRIDE_FILE" 2>/dev/null)" || echo "direct_fps_override=none"
[ -r "$SOURCE_FPS_OVERRIDE_FILE" ] && echo "source_fps_override=$(cat "$SOURCE_FPS_OVERRIDE_FILE" 2>/dev/null)" || echo "source_fps_override=none"
if [ -r /tmp/mibr-direct-remux.status ]; then
  grep -E '^(pace_|last_input_interval_us|min_input_interval_us|max_input_interval_us|last_emit_interval_us|max_emit_jitter_us)=' /tmp/mibr-direct-remux.status 2>/dev/null || true
else
  echo "remux_pace_status=missing"
fi

echo
echo "=== SOURCE ==="
if [ -r /tmp/mibr-carplay111.state ]; then
  echo "stream111_state=$(cat /tmp/mibr-carplay111.state 2>/dev/null)"
else
  echo "stream111_state=missing"
fi
if [ -r /tmp/mibr-carplay111.heartbeat ]; then
  echo "stream111_heartbeat=$(cat /tmp/mibr-carplay111.heartbeat 2>/dev/null)"
else
  echo "stream111_heartbeat=missing"
fi

echo
echo "=== NAVIGNORE ==="
if pidin ar 2>/dev/null | grep '[j]9' | grep -Fq 'MIBR-NavIgnore.jar'; then
  echo "navignore_loaded=1"
else
  echo "navignore_loaded=0"
fi

echo
echo "=== GATE ==="
if [ -r /tmp/mibr-isotx2-gate.stats ]; then
  cat /tmp/mibr-isotx2-gate.stats
else
  echo "gate_stats=missing"
fi
[ -e /tmp/mibr-isotx2-gate.direct ] && echo "direct_marker=1" || echo "direct_marker=0"

echo "AUTO_DIRECT_STATUS=PASS"
exit 0
