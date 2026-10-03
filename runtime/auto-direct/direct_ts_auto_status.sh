#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init || { echo "AUTO_DIRECT_STATUS=FAIL_RUNTIME"; exit 3; }

SUPPID=/tmp/mibr-direct-auto-supervisor.pid
WDPID=/tmp/mibr-direct-auto-watchdog.pid
BRIDGEPID=/tmp/mibr-direct-auto-bridge.pid

echo "=== AUTO DIRECT ==="
echo "enabled=$(runtime_cfg_bool "$AUTODIRECT_CONFIG_NAME" 1)"
echo "config_source=$(runtime_cfg_source "$AUTODIRECT_CONFIG_NAME")"
echo "temporary_path=$MIBR_CFG_TEMP_ROOT/$AUTODIRECT_CONFIG_NAME"
echo "persistent_path=$MIBR_CFG_PERSIST_ROOT/$AUTODIRECT_CONFIG_NAME"
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
echo "=== FRAME PACING / FRAMING ==="
EFFECTIVE_SOURCE_FPS=$(runtime_cfg_get "$FPS_CONFIG_NAME" "${ALTSCREEN111_FPS:-30}")
echo "source_base_fps=${ALTSCREEN111_FPS:-UNKNOWN}"
echo "source_max_fps=$EFFECTIVE_SOURCE_FPS"
echo "fps_config_source=$(runtime_cfg_source "$FPS_CONFIG_NAME")"
echo "fps_temp=$MIBR_CFG_TEMP_ROOT/$FPS_CONFIG_NAME"
echo "fps_persistent=$MIBR_CFG_PERSIST_ROOT/$FPS_CONFIG_NAME"
echo "direct_output_fps=${DIRECT_OUTPUT_FPS:-UNKNOWN}"
echo "direct_pace=${DIRECT_PACE:-UNKNOWN}"
echo "direct_pace_buffer=${DIRECT_PACE_BUFFER:-UNKNOWN}"
echo "source_timing_debug=${ALTSCREEN111_TIMING_DEBUG:-UNKNOWN}"
echo "source_timing_interval_ms=${ALTSCREEN111_TIMING_INTERVAL_MS:-UNKNOWN}"
echo "direct_telemetry=${DIRECT_TELEMETRY:-UNKNOWN}"
case "${DIRECT_SOURCE_FRAMING:-0}" in 1) F=m1au ;; *) F=raw ;; esac
echo "direct_source_framing=$F"
echo "framing_config_source=$(runtime_cfg_source "$FRAMING_CONFIG_NAME")"
echo "framing_temp=$MIBR_CFG_TEMP_ROOT/$FRAMING_CONFIG_NAME"
echo "framing_persistent=$MIBR_CFG_PERSIST_ROOT/$FRAMING_CONFIG_NAME"

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
