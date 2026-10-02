#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init_durable || exit 3
load_altscreen_config || exit 4

ENABLED=/mnt/app/root/mibr-carplay-autodirect.enabled
PIDFILE=/tmp/mibr-direct-auto-supervisor.pid
BRIDGEPID=/tmp/mibr-direct-auto-bridge.pid
AUTOHB=/tmp/mibr-direct-auto.heartbeat
AUTOSTATE=/tmp/mibr-direct-auto.state
SOURCE_STATE=/tmp/mibr-carplay111.state
SOURCE_HB=/tmp/mibr-carplay111.heartbeat
GATE_STATS=/tmp/mibr-isotx2-gate.stats
SOURCE_TIMING_STATUS=/tmp/mibr-alt111-source-timing.status
SOURCE_TIMING_ENABLE=/tmp/mibr-alt111-source-timing.enabled
SOURCE_TIMING_INTERVAL=/tmp/mibr-alt111-source-timing-interval-ms
REMUX_STATUS=/tmp/mibr-direct-remux.status
GATE=$BASE/scripts/writev_gate.sh
BRIDGE=$BASE/bin/direct-ts-remux
BRIDGE_PID=""
GATE_DIRECT=0
HBSEQ=0
SESSION=0

auto_log(){
  direct_log "AUTO-DIRECT $*"
}

status_value(){
  F=$1
  K=$2
  [ -r "$F" ] || return 1
  awk -F= -v k="$K" '$1==k { print substr($0,index($0,"=")+1); exit }' "$F" 2>/dev/null
}

fps_bucket(){
  V=${1:-0}
  case "$V" in *[!0-9]*|'') echo 0; return ;; esac
  if [ "$V" -ge 3600 ]; then echo 40
  elif [ "$V" -ge 2750 ]; then echo 30
  elif [ "$V" -ge 2250 ]; then echo 25
  elif [ "$V" -ge 1750 ]; then echo 20
  elif [ "$V" -ge 1250 ]; then echo 15
  elif [ "$V" -gt 0 ]; then echo other
  else echo 0
  fi
}

configure_source_timing(){
  if [ "${ALTSCREEN111_TIMING_DEBUG:-0}" = "1" ]; then
    echo "${ALTSCREEN111_TIMING_INTERVAL_MS:-1000}" > "$SOURCE_TIMING_INTERVAL" 2>/dev/null || true
    : > "$SOURCE_TIMING_ENABLE" 2>/dev/null || true
  else
    rm -f "$SOURCE_TIMING_ENABLE" "$SOURCE_TIMING_INTERVAL" "$SOURCE_TIMING_STATUS" 2>/dev/null || true
  fi
}

telemetry_init(){
  TELEMETRY=$RUN/telemetry.tsv
  TELEMETRY_EVENTS=$RUN/telemetry-events.log
  TELEMETRY_SEQ=0
  LAST_SOURCE_BUCKET=0
  LAST_SOURCE_SAMPLE_SEQ=0
  PENDING_SOURCE_BUCKET=0
  PENDING_SOURCE_BUCKET_COUNT=0
  [ "${DIRECT_TELEMETRY:-0}" = "1" ] || return 0
  echo "sample	time	source_sample_seq	source_sample_stale	source_max_fps	source_fps_x100	source_bucket	source_frames_total	source_input_bps	source_last_us	source_min_us	source_max_us	source_ts_word1	source_ts_word2	remux_input_bps	most_bps	remux_input_us	pace_underflows	pace_late_frames	pace_backpressure_waits	write_eagain	last_block_wait_us	max_block_wait_us	max_emit_jitter_us" > "$TELEMETRY"
}

telemetry_sample(){
  [ "${DIRECT_TELEMETRY:-0}" = "1" ] || return 0
  TELEMETRY_SEQ=$((TELEMETRY_SEQ+1))
  SCONF=$(status_value "$SOURCE_TIMING_STATUS" configured_max_fps)
  if [ -z "$SCONF" ]; then
    SCONF=$ALTSCREEN111_FPS
    if [ -r "$SOURCE_FPS_OVERRIDE_FILE" ]; then
      V=$(cat "$SOURCE_FPS_OVERRIDE_FILE" 2>/dev/null)
      case "$V" in 20|25|30|40) SCONF=$V ;; esac
    fi
  fi
  SSEQ=$(status_value "$SOURCE_TIMING_STATUS" sample_seq); SSEQ=${SSEQ:-0}
  if [ "$SSEQ" != "0" ] && [ "$SSEQ" = "$LAST_SOURCE_SAMPLE_SEQ" ]; then
    SSTALE=1
  else
    SSTALE=0
    LAST_SOURCE_SAMPLE_SEQ=$SSEQ
  fi
  SFPS=$(status_value "$SOURCE_TIMING_STATUS" source_arrival_fps_x100); SFPS=${SFPS:-0}
  SBUCKET=$(fps_bucket "$SFPS")
  SFRAMES=$(status_value "$SOURCE_TIMING_STATUS" frames_total); SFRAMES=${SFRAMES:-0}
  SBPS=$(status_value "$SOURCE_TIMING_STATUS" source_input_bps); SBPS=${SBPS:-0}
  SLAST=$(status_value "$SOURCE_TIMING_STATUS" source_arrival_last_us); SLAST=${SLAST:-0}
  SMIN=$(status_value "$SOURCE_TIMING_STATUS" source_arrival_min_us); SMIN=${SMIN:-0}
  SMAX=$(status_value "$SOURCE_TIMING_STATUS" source_arrival_max_us); SMAX=${SMAX:-0}
  STS1=$(status_value "$SOURCE_TIMING_STATUS" source_ts_word1); [ -n "$STS1" ] || STS1=-
  STS2=$(status_value "$SOURCE_TIMING_STATUS" source_ts_word2); [ -n "$STS2" ] || STS2=-
  RIBPS=$(status_value "$REMUX_STATUS" input_bps); RIBPS=${RIBPS:-0}
  MBPS=$(status_value "$REMUX_STATUS" most_bps); MBPS=${MBPS:-0}
  RINT=$(status_value "$REMUX_STATUS" last_input_interval_us); RINT=${RINT:-0}
  PU=$(status_value "$REMUX_STATUS" pace_underflows); PU=${PU:-0}
  PL=$(status_value "$REMUX_STATUS" pace_late_frames); PL=${PL:-0}
  PB=$(status_value "$REMUX_STATUS" pace_backpressure_waits); PB=${PB:-0}
  WE=$(status_value "$REMUX_STATUS" write_eagain); WE=${WE:-0}
  LBW=$(status_value "$REMUX_STATUS" last_block_wait_us); LBW=${LBW:-0}
  MBW=$(status_value "$REMUX_STATUS" max_block_wait_us); MBW=${MBW:-0}
  MEJ=$(status_value "$REMUX_STATUS" max_emit_jitter_us); MEJ=${MEJ:-0}
  echo "$TELEMETRY_SEQ	$(timestamp_now)	$SSEQ	$SSTALE	$SCONF	$SFPS	$SBUCKET	$SFRAMES	$SBPS	$SLAST	$SMIN	$SMAX	$STS1	$STS2	$RIBPS	$MBPS	$RINT	$PU	$PL	$PB	$WE	$LBW	$MBW	$MEJ" >> "$TELEMETRY" 2>/dev/null || true

  if [ "$SSTALE" = "0" ] && [ "$SBUCKET" != "0" ] && [ "$SBUCKET" != "other" ] && [ "$SBUCKET" != "$LAST_SOURCE_BUCKET" ]; then
    if [ "$SBUCKET" = "$PENDING_SOURCE_BUCKET" ]; then
      PENDING_SOURCE_BUCKET_COUNT=$((PENDING_SOURCE_BUCKET_COUNT+1))
    else
      PENDING_SOURCE_BUCKET=$SBUCKET
      PENDING_SOURCE_BUCKET_COUNT=1
    fi
    if [ "$PENDING_SOURCE_BUCKET_COUNT" -ge 2 ]; then
      echo "$(timestamp_now) source_fps_bucket old=$LAST_SOURCE_BUCKET new=$SBUCKET measured_x100=$SFPS source_bps=$SBPS most_bps=$MBPS" >> "$TELEMETRY_EVENTS" 2>/dev/null || true
      LAST_SOURCE_BUCKET=$SBUCKET
      PENDING_SOURCE_BUCKET=0
      PENDING_SOURCE_BUCKET_COUNT=0
    fi
  else
    PENDING_SOURCE_BUCKET=0
    PENDING_SOURCE_BUCKET_COUNT=0
  fi
}

publish_auto_hb(){
  HBSEQ=$((HBSEQ+1))
  echo "$$:$HBSEQ" > "$AUTOHB" 2>/dev/null || true
}

publish_auto_state(){
  echo "$1" > "$AUTOSTATE" 2>/dev/null || true
}

gate_stock(){
  "$GATE" stock >/dev/null 2>&1 || rm -f /tmp/mibr-isotx2-gate.direct 2>/dev/null || true
  GATE_DIRECT=0
}

stop_bridge(){
  if [ -n "$BRIDGE_PID" ] && kill -0 "$BRIDGE_PID" 2>/dev/null; then
    kill "$BRIDGE_PID" 2>/dev/null || true
    sleep 1
    kill -0 "$BRIDGE_PID" 2>/dev/null && kill -9 "$BRIDGE_PID" 2>/dev/null || true
  fi
  [ -n "$BRIDGE_PID" ] && wait "$BRIDGE_PID" 2>/dev/null || true
  BRIDGE_PID=""
  rm -f "$BRIDGEPID" 2>/dev/null || true
}

cleanup(){
  stop_bridge
  gate_stock
  rm -f "$SOURCE_TIMING_ENABLE" "$SOURCE_TIMING_INTERVAL" 2>/dev/null || true
  publish_auto_state "stopped"
  rm -f "$AUTOHB" "$PIDFILE" "$BRIDGEPID" 2>/dev/null || true
}
trap cleanup 0 1 2 15

if [ -r "$PIDFILE" ]; then
  OLD=$(cat "$PIDFILE" 2>/dev/null)
  if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
    echo "AUTO_DIRECT_SUPERVISOR=ALREADY_RUNNING pid=$OLD"
    exit 0
  fi
fi
echo "$$" > "$PIDFILE" || exit 5
publish_auto_state "starting"
publish_auto_hb
configure_source_timing

[ -x "$BRIDGE" ] || { auto_log "FAIL missing bridge $BRIDGE"; exit 10; }
[ -x "$GATE" ] || { auto_log "FAIL missing gate control $GATE"; exit 11; }

auto_log "supervisor started pid=$$ source=tcp://127.0.0.1:$ALTSCREEN111_TEE_PORT output=/dev/mlb/isoTX2"

while [ -e "$ENABLED" ]; do
  publish_auto_hb

  if [ ! -r "$GATE_STATS" ] || ! grep -q '^loaded=1$' "$GATE_STATS" 2>/dev/null; then
    publish_auto_state "waiting_gate"
    gate_stock
    sleep 1
    continue
  fi

  if ! pidin ar 2>/dev/null | grep '[j]9' | grep -Fq 'MIBR-NavIgnore.jar'; then
    publish_auto_state "waiting_navignore"
    gate_stock
    sleep 1
    continue
  fi

  if ! carplay_stack_health; then
    publish_auto_state "waiting_carplay"
    gate_stock
    sleep 1
    continue
  fi

  CUR=missing
  [ -r "$SOURCE_STATE" ] && CUR=$(cat "$SOURCE_STATE" 2>/dev/null)
  if [ "$CUR" != "streaming" ] || [ ! -r "$SOURCE_HB" ]; then
    publish_auto_state "waiting_stream111"
    gate_stock
    sleep 1
    continue
  fi

  # A validated video frame has already been observed when state=streaming and
  # the heartbeat file exists. Do not require it to advance for another full
  # second here: iPhone may already have entered static-screen idle. The bridge
  # connection below requests a fresh keyframe; that post-connect activity is
  # the stronger proof that the source can feed a new DIRECT session.
  HB_BEFORE=$(cat "$SOURCE_HB" 2>/dev/null)
  [ -n "$HB_BEFORE" ] || {
    publish_auto_state "waiting_stream111"
    gate_stock
    sleep 1
    continue
  }

  SESSION=$((SESSION+1))
  RUN=$(direct_new_run auto-direct-$SESSION) || {
    auto_log "FAIL cannot allocate session log directory"
    sleep 2
    continue
  }
  BRIDGELOG=$RUN/bridge.log
  SUMMARY=$RUN/SUMMARY.txt
  telemetry_init
  DM_BEFORE=$(pidin ar 2>/dev/null | awk '/pps\/displaymanager/ && !/awk/ {print $1; exit}')
  if [ -z "${DM_BEFORE:-}" ]; then
    publish_auto_state "waiting_displaymanager"
    sleep 1
    continue
  fi

  "$GATE" reset >/dev/null 2>&1 || true
  "$GATE" direct >/dev/null 2>&1 || {
    auto_log "FAIL cannot enter DIRECT session=$SESSION"
    publish_auto_state "gate_failed"
    sleep 2
    continue
  }
  GATE_DIRECT=1
  publish_auto_state "direct_starting"
  auto_log "session=$SESSION DIRECT entered displaymanager_pid=$DM_BEFORE heartbeat_before=$HB_BEFORE"

  # Reload the runtime FPS override for every DIRECT session. The source-side
  # descriptor remains independent; this rate owns remux timestamps and pacing.
  load_altscreen_config || {
    auto_log "FAIL invalid direct FPS/pacing configuration"
    gate_stock
    publish_auto_state "config_failed"
    sleep 2
    continue
  }
  configure_source_timing
  MIBR_PACE="$DIRECT_PACE" MIBR_PACE_BUFFER="$DIRECT_PACE_BUFFER" \
  "$BRIDGE" "tcp://127.0.0.1:$ALTSCREEN111_TEE_PORT" /dev/mlb/isoTX2 \
      "$DIRECT_OUTPUT_FPS" 0 0 0x11 > "$BRIDGELOG" 2>&1 &
  BRIDGE_PID=$!
  echo "$BRIDGE_PID" > "$BRIDGEPID" 2>/dev/null || true
  publish_auto_state "direct_starting"

  # Connecting direct-ts-remux to the tee makes Run127 request forceKeyFrame.
  # Require resulting source activity before declaring the automatic takeover
  # established. This covers a stream that had already gone idle before the
  # supervisor noticed it without mixing a probe stream with stock isoTX2.
  POST_READY=0
  POST_N=0
  LAST_SOURCE_HB=$HB_BEFORE
  while [ "$POST_N" -lt 5 ] && kill -0 "$BRIDGE_PID" 2>/dev/null; do
    publish_auto_hb
    CUR=missing
    [ -r "$SOURCE_STATE" ] && CUR=$(cat "$SOURCE_STATE" 2>/dev/null)
    NOW_HB=
    [ -r "$SOURCE_HB" ] && NOW_HB=$(cat "$SOURCE_HB" 2>/dev/null)
    if [ "$CUR" != "streaming" ]; then
      break
    fi
    if [ -n "$NOW_HB" ] && [ "$NOW_HB" != "$HB_BEFORE" ]; then
      POST_READY=1
      LAST_SOURCE_HB=$NOW_HB
      break
    fi
    sleep 1
    POST_N=$((POST_N+1))
  done

  if [ "$POST_READY" -ne 1 ]; then
    STOP_REASON=no_post_connect_video
    auto_log "session=$SESSION no post-connect video after forceKeyFrame window; returning STOCK state=$CUR heartbeat_before=$HB_BEFORE heartbeat_now=${NOW_HB:-NONE}"
    stop_bridge
    gate_stock
    publish_auto_state "stock"
    sleep 2
    continue
  fi

  publish_auto_state "direct"
  auto_log "session=$SESSION DIRECT source confirmed heartbeat_after=$LAST_SOURCE_HB"
  IDLE_SECONDS=0
  STOP_REASON=bridge_exit

  while [ -e "$ENABLED" ] && kill -0 "$BRIDGE_PID" 2>/dev/null; do
    publish_auto_hb
    CUR=missing
    [ -r "$SOURCE_STATE" ] && CUR=$(cat "$SOURCE_STATE" 2>/dev/null)
    NOW_HB=
    [ -r "$SOURCE_HB" ] && NOW_HB=$(cat "$SOURCE_HB" 2>/dev/null)

    if [ "$CUR" != "streaming" ]; then
      STOP_REASON=stream_state_$CUR
      break
    fi

    # Do not treat a quiet video heartbeat as route end. CarPlay is allowed to
    # stop re-encoding an unchanged secondary screen while keeping stream 111
    # connected; the VC should keep the last decoded frame in that state.
    # A post-connect keyframe/heartbeat gates DIRECT establishment. After that,
    # session teardown/disconnect or bridge exit owns the automatic STOCK transition.
    if [ -z "$NOW_HB" ] || [ "$NOW_HB" = "$LAST_SOURCE_HB" ]; then
      IDLE_SECONDS=$((IDLE_SECONDS+1))
    else
      IDLE_SECONDS=0
      LAST_SOURCE_HB=$NOW_HB
    fi

    telemetry_sample
    sleep 1
  done

  if [ ! -e "$ENABLED" ]; then
    STOP_REASON=disabled
  elif ! kill -0 "$BRIDGE_PID" 2>/dev/null; then
    STOP_REASON=bridge_exit
  fi

  telemetry_sample
  stop_bridge
  gate_stock
  publish_auto_state "stock"
  sleep 1
  [ -r "$SOURCE_TIMING_STATUS" ] && cp "$SOURCE_TIMING_STATUS" "$RUN/source-timing-final.status" 2>/dev/null || true
  [ -r "$REMUX_STATUS" ] && cp "$REMUX_STATUS" "$RUN/remux-final.status" 2>/dev/null || true

  DM_AFTER=$(pidin ar 2>/dev/null | awk '/pps\/displaymanager/ && !/awk/ {print $1; exit}')
  BLOCKS=$(awk '
    /REMUX_DONE/ {
      for(i=1;i<=NF;i++) if($i ~ /^most_blocks=/) { split($i,a,"="); v=a[2] }
    }
    END { print v+0 }
  ' "$BRIDGELOG" 2>/dev/null)
  WRITE_SIZE=$(awk '
    /REMUX_DONE/ {
      for(i=1;i<=NF;i++) if($i ~ /^write_size=/) { split($i,a,"="); v=a[2] }
    }
    END { print v+0 }
  ' "$BRIDGELOG" 2>/dev/null)

  {
    echo "mode=auto-direct"
    echo "session=$SESSION"
    echo "stop_reason=$STOP_REASON"
    echo "input=tcp://127.0.0.1:$ALTSCREEN111_TEE_PORT"
    echo "output=/dev/mlb/isoTX2"
    EFFECTIVE_SOURCE_FPS=$(status_value "$SOURCE_TIMING_STATUS" configured_max_fps)
    [ -n "$EFFECTIVE_SOURCE_FPS" ] || EFFECTIVE_SOURCE_FPS=$ALTSCREEN111_FPS
    echo "source_max_fps=$EFFECTIVE_SOURCE_FPS"
    echo "source_base_fps=$ALTSCREEN111_FPS"
    echo "direct_output_fps=$DIRECT_OUTPUT_FPS"
    echo "direct_pace=$DIRECT_PACE"
    echo "direct_pace_buffer=$DIRECT_PACE_BUFFER"
    echo "source_timing_debug=$ALTSCREEN111_TIMING_DEBUG"
    echo "source_timing_interval_ms=$ALTSCREEN111_TIMING_INTERVAL_MS"
    echo "direct_telemetry=$DIRECT_TELEMETRY"
    echo "telemetry_file=${TELEMETRY:-disabled}"
    echo "most_blocks=$BLOCKS"
    echo "most_write_size=$WRITE_SIZE"
    echo "displaymanager_pid_before=$DM_BEFORE"
    echo "displaymanager_pid_after=${DM_AFTER:-NONE}"
    echo "gate=stock"
  } > "$SUMMARY"

  auto_log "session=$SESSION stopped reason=$STOP_REASON blocks=$BLOCKS write_size=$WRITE_SIZE displaymanager_before=$DM_BEFORE after=${DM_AFTER:-NONE}"

  [ "$STOP_REASON" = "bridge_exit" ] && sleep 3
done

auto_log "supervisor leaving: enable marker absent"
exit 0
