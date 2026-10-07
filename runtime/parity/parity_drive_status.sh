#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

ENABLE=/mnt/app/root/mibr-parity-drive.enabled
STATUS_T=/tmp/mibr-parity-status-enabled
STATUS_P=/mnt/app/root/mibr-parity-status-enabled
STATS_T=/tmp/mibr-parity-statistics-enabled
STATS_P=/mnt/app/root/mibr-parity-statistics-enabled
APP_RW=0

usage(){
  echo "usage: $0 [status|status-on|status-off|statistics-on|statistics-off|all-on|all-off|clear-temp] [temp|persistent]"
  exit 2
}

cfg_read(){
  T=$1
  P=$2
  D=$3
  if [ -r "$T" ]; then V=$(cat "$T" 2>/dev/null); SRC=temp
  elif [ -r "$P" ]; then V=$(cat "$P" 2>/dev/null); SRC=persistent
  else V=$D; SRC=default
  fi
  case "$V" in 1|on|yes|true) V=1 ;; 0|off|no|false) V=0 ;; *) V=$D ;; esac
  echo "$V:$SRC"
}

app_rw(){
  [ "$APP_RW" -eq 1 ] && return 0
  mount -uw /mnt/app 2>/dev/null || return 1
  APP_RW=1
}

app_ro(){
  [ "$APP_RW" -eq 1 ] || return 0
  sync 2>/dev/null || true
  mount -ur /mnt/app 2>/dev/null || return 1
  APP_RW=0
}

write_cfg(){
  NAME=$1
  VALUE=$2
  LAYER=$3
  case "$NAME:$LAYER" in
    status:temp) P=$STATUS_T ;;
    status:persistent) P=$STATUS_P ;;
    statistics:temp) P=$STATS_T ;;
    statistics:persistent) P=$STATS_P ;;
    *) return 2 ;;
  esac
  if [ "$LAYER" = "persistent" ]; then app_rw || return 3; fi
  echo "$VALUE" > "$P" 2>/dev/null || return 4
  [ "$LAYER" = "persistent" ] && chmod 644 "$P" 2>/dev/null || true
  return 0
}

diagnostics_status(){
  S=$(cfg_read "$STATUS_T" "$STATUS_P" 1)
  T=$(cfg_read "$STATS_T" "$STATS_P" 1)
  SV=${S%%:*}
  SS=${S#*:}
  TV=${T%%:*}
  TS=${T#*:}
  [ "$TV" = "1" ] && [ "$SV" != "1" ] && TE=0 || TE=$TV
  echo "status_logging=$SV"
  echo "status_logging_source=$SS"
  echo "statistics=$TE"
  echo "statistics_source=$TS"
  echo "statistics_requires_status=1"
  echo "diagnostics_apply=next_parity_session"
}

CMD=${1:-status}
LAYER=${2:-temp}
case "$LAYER" in temp|persistent) ;; *) usage ;; esac

case "$CMD" in
  status) ;;
  status-on) write_cfg status 1 "$LAYER" || exit $? ;;
  status-off)
    write_cfg status 0 "$LAYER" || exit $?
    write_cfg statistics 0 "$LAYER" || exit $?
    ;;
  statistics-on)
    write_cfg status 1 "$LAYER" || exit $?
    write_cfg statistics 1 "$LAYER" || exit $?
    ;;
  statistics-off) write_cfg statistics 0 "$LAYER" || exit $? ;;
  all-on)
    write_cfg status 1 "$LAYER" || exit $?
    write_cfg statistics 1 "$LAYER" || exit $?
    ;;
  all-off)
    write_cfg statistics 0 "$LAYER" || exit $?
    write_cfg status 0 "$LAYER" || exit $?
    ;;
  clear-temp)
    rm -f "$STATUS_T" "$STATS_T" 2>/dev/null || true
    ;;
  *) usage ;;
esac

app_ro >/dev/null 2>&1 || true
APP_RW=0

echo "=== PARITY DRIVE ==="
if [ -r "$ENABLE" ]; then
  echo "enabled=$(cat "$ENABLE" 2>/dev/null)"
else
  echo "enabled=0"
fi
[ -r /tmp/mibr-parity-drive-supervisor.pid ] && echo "supervisor_pid=$(cat /tmp/mibr-parity-drive-supervisor.pid 2>/dev/null)" || echo "supervisor_pid=none"
[ -r /tmp/mibr-parity-drive.state ] && echo "supervisor_state=$(cat /tmp/mibr-parity-drive.state 2>/dev/null)" || echo "supervisor_state=none"
[ -r /tmp/mibr-parity-drive.heartbeat ] && echo "supervisor_heartbeat=$(cat /tmp/mibr-parity-drive.heartbeat 2>/dev/null)" || echo "supervisor_heartbeat=none"

echo
echo "=== DIAGNOSTICS ==="
diagnostics_status
echo "sd_log_root=/net/mmx/fs/sda0/esd/carplay-test/logs/parity-drive"

echo
echo "=== PARITY SESSION ==="
for F in /tmp/mibr-parity-session.state /tmp/mibr-parity-session.pid /tmp/mibr-parity-session-bridge.pid /tmp/mibr-parity-session-watchdog.pid; do
  if [ -r "$F" ]; then echo "$F=$(cat "$F" 2>/dev/null)"; else echo "$F=none"; fi
done
[ -e /tmp/mibr-parity-session.lock ] && echo "session_lock=present" || echo "session_lock=none"

echo
echo "=== PARITY TRANSPORT ==="
if [ -r /tmp/mibr-parity-ts.status ]; then
  grep -E '^(state|input_records|input_idrs|input_non_idr_aus|input_slice_p|input_slice_b|input_slice_i|input_slice_unknown|output_aus_started|output_aus_completed|output_idr_aus_started|output_non_idr_aus_started|output_idr_aus_completed|output_non_idr_aus_completed|output_slice_p_started|output_slice_b_started|output_slice_i_started|output_slice_unknown_started|output_slice_p_completed|output_slice_b_completed|output_slice_i_completed|output_slice_unknown_completed|sequence_gaps|dropped_wait_idr|safe_recoveries|blocks_written|bytes_written|write_eagain|write_errors|last_write_us|max_write_us|queue_aus|queue_packets)=' /tmp/mibr-parity-ts.status 2>/dev/null || true
else
  echo "parity_transport_status=missing"
fi

echo
echo "=== SOURCE / GEN2 ==="
[ -r /tmp/mibr-carplay111.state ] && echo "stream111_state=$(cat /tmp/mibr-carplay111.state 2>/dev/null)" || echo "stream111_state=missing"
[ -r /tmp/mibr-carplay111.heartbeat ] && echo "stream111_heartbeat=$(cat /tmp/mibr-carplay111.heartbeat 2>/dev/null)" || echo "stream111_heartbeat=missing"
if [ -r /tmp/mibr-alt111-gen2.status ]; then
  grep -E '^(source_aus|source_idrs|delivered_aus|dropped_aus|queue_count|queue_bytes|stream_gen|codec_gen|consumer_gen)=' /tmp/mibr-alt111-gen2.status 2>/dev/null || true
fi
if [ -r /tmp/mibr-alt111-source-timing.status ]; then
  grep -E '^(configured_max_fps|frames_total|source_arrival_fps_x100|source_input_bps|source_arrival_last_us|source_arrival_min_us|source_arrival_max_us)=' /tmp/mibr-alt111-source-timing.status 2>/dev/null || true
fi

echo
echo "=== GATE ==="
[ -r /tmp/mibr-alt111-native-gate.status ] && cat /tmp/mibr-alt111-native-gate.status || echo "gate_status=missing"

echo
echo "=== SD EVIDENCE ==="
SDROOT=/net/mmx/fs/sda0/esd/carplay-test/logs/parity-drive
if [ -d "$SDROOT" ]; then
  echo "sd_logs=present"
  echo "sd_log_root=$SDROOT"
  [ -r "$SDROOT/current.status" ] && echo "current_status=$SDROOT/current.status" || echo "current_status=missing"
  [ -r "$SDROOT/current.statistics" ] && {
    echo "current_statistics=$SDROOT/current.statistics"
    cat "$SDROOT/current.statistics" 2>/dev/null || true
  } || echo "current_statistics=missing"
  ls -lt "$SDROOT" 2>/dev/null | head -8 || true
else
  echo "sd_logs=missing"
fi

[ "$CMD" = "status" ] || echo "PARITY_DIAGNOSTICS_CHANGE=PASS command=$CMD layer=$LAYER"
exit 0
