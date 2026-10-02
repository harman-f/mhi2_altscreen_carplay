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
EFFECTIVE_SOURCE_FPS=${ALTSCREEN111_FPS:-UNKNOWN}
if [ -r "$SOURCE_FPS_OVERRIDE_FILE" ]; then
  V=$(cat "$SOURCE_FPS_OVERRIDE_FILE" 2>/dev/null)
  case "$V" in 20|25|30|40) EFFECTIVE_SOURCE_FPS=$V ;; esac
fi
echo "source_base_fps=${ALTSCREEN111_FPS:-UNKNOWN}"
echo "source_max_fps=$EFFECTIVE_SOURCE_FPS"
echo "direct_output_fps=${DIRECT_OUTPUT_FPS:-UNKNOWN}"
echo "direct_pace=${DIRECT_PACE:-UNKNOWN}"
echo "direct_pace_buffer=${DIRECT_PACE_BUFFER:-UNKNOWN}"
echo "source_timing_debug=${ALTSCREEN111_TIMING_DEBUG:-UNKNOWN}"
echo "source_timing_interval_ms=${ALTSCREEN111_TIMING_INTERVAL_MS:-UNKNOWN}"
echo "direct_telemetry=${DIRECT_TELEMETRY:-UNKNOWN}"
echo "direct_source_framing=${DIRECT_SOURCE_FRAMING:-UNKNOWN}"
[ -r "$DIRECT_FPS_OVERRIDE_FILE" ] && echo "direct_fps_override=$(cat "$DIRECT_FPS_OVERRIDE_FILE" 2>/dev/null)" || echo "direct_fps_override=none"
[ -r "$SOURCE_FPS_OVERRIDE_FILE" ] && echo "source_fps_override=$(cat "$SOURCE_FPS_OVERRIDE_FILE" 2>/dev/null)" || echo "source_fps_override=none"

echo
echo "=== SOURCE TIMING ==="
if [ -r /tmp/mibr-alt111-source-timing.status ]; then
  cat /tmp/mibr-alt111-source-timing.status
else
  echo "source_timing_status=missing"
fi

echo
echo "=== REMUX / MOST TIMING ==="
if [ -r /tmp/mibr-direct-remux.status ]; then
  grep -E '^(input_mode|m1au_|input_bps|most_bps|pace_|last_input_interval_us|min_input_interval_us|max_input_interval_us|last_emit_interval_us|max_emit_jitter_us|write_eagain|write_timeouts|write_errors|last_write_call_us|last_block_wait_us|max_block_wait_us|over20ms_blocks)=' /tmp/mibr-direct-remux.status 2>/dev/null || true
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
