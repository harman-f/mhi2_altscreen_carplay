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
GATE=$BASE/scripts/writev_gate.sh
BRIDGE=$BASE/bin/direct-ts-remux
BRIDGE_PID=""
GATE_DIRECT=0
HBSEQ=0
SESSION=0

auto_log(){
  direct_log "AUTO-DIRECT $*"
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

    sleep 1
  done

  if [ ! -e "$ENABLED" ]; then
    STOP_REASON=disabled
  elif ! kill -0 "$BRIDGE_PID" 2>/dev/null; then
    STOP_REASON=bridge_exit
  fi

  stop_bridge
  gate_stock
  publish_auto_state "stock"
  sleep 1

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
    echo "source_max_fps=$ALTSCREEN111_FPS"
    echo "direct_output_fps=$DIRECT_OUTPUT_FPS"
    echo "direct_pace=$DIRECT_PACE"
    echo "direct_pace_buffer=$DIRECT_PACE_BUFFER"
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
