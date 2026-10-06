#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Guarded MU1440 long-run parity supervisor.
# It never signals stock processes. Each parity-session owns and, on exit,
# restores the temporary writev-gate route. The supervisor only waits/retries.

set -u

export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/media/gracenote/bin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin:/mnt/app/armle/usr/sbin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1

BASE=/mnt/app/root/altscreen-u2
RUNNER=$BASE/bin/parity-session
BRIDGE=$BASE/bin/direct-ts-parity
ENABLE=/mnt/app/root/mibr-parity-drive.enabled
STATE=/tmp/mibr-parity-drive.state
HB=/tmp/mibr-parity-drive.heartbeat
PIDFILE=/tmp/mibr-parity-drive-supervisor.pid
SESSION_LOCK=/tmp/mibr-parity-session.lock
SOURCE_STATE=/tmp/mibr-carplay111.state
SOURCE_HB=/tmp/mibr-carplay111.heartbeat
GEN2_STATUS=/tmp/mibr-alt111-gen2.status
SOURCE_TIMING=/tmp/mibr-alt111-source-timing.status
SOURCE_TIMING_ENABLE=/tmp/mibr-alt111-source-timing.enabled
SOURCE_TIMING_INTERVAL=/tmp/mibr-alt111-source-timing-interval-ms
PARITY_STATUS=/tmp/mibr-parity-ts.status
GATE_STATUS=/tmp/mibr-alt111-native-gate.status
DEFAULT_SECONDS=0
SECONDS_PER_SESSION=${MIBR_PARITY_DRIVE_SECONDS:-$DEFAULT_SECONDS}
SEQ=0
SESSION=0

case "$SECONDS_PER_SESSION" in
  *[!0-9]*|'') exit 2 ;;
esac
[ "$SECONDS_PER_SESSION" -eq 0 ] || { [ "$SECONDS_PER_SESSION" -ge 60 ] && [ "$SECONDS_PER_SESSION" -le 7200 ]; } || exit 2
[ -x "$RUNNER" ] && [ -x "$BRIDGE" ] || exit 3

enabled(){
  [ -r "$ENABLE" ] || return 1
  V=$(cat "$ENABLE" 2>/dev/null)
  [ "$V" = "1" ]
}

stamp(){
  if [ -x /net/rcc/usr/bin/date ]; then
    /net/rcc/usr/bin/date +%Y%m%d-%H%M%S 2>/dev/null && return 0
  fi
  echo "run-$$-$SESSION"
}

publish(){
  echo "$1" > "$STATE" 2>/dev/null || true
}

heartbeat(){
  SEQ=$((SEQ+1))
  echo "$$:$SEQ" > "$HB" 2>/dev/null || true
}

status_value(){
  F=$1
  K=$2
  [ -r "$F" ] || { echo 0; return; }
  V=$(awk -F= -v k="$K" '$1==k {print substr($0,index($0,"=")+1); exit}' "$F" 2>/dev/null)
  [ -n "$V" ] && echo "$V" || echo 0
}

choose_log_root(){
  [ -d /net/mmx/fs/sda0 ] && mount -uw /net/mmx/fs/sda0 2>/dev/null || true
  for R in /net/mmx/fs/sda0/esd/mibr-parity-drive-logs /mnt/app/root/mibr-parity-drive-logs /tmp/mibr-parity-drive-logs; do
    mkdir -p "$R" 2>/dev/null || continue
    T="$R/.write-test-$$"
    if : > "$T" 2>/dev/null; then
      rm -f "$T" 2>/dev/null || true
      echo "$R"
      return 0
    fi
  done
  return 1
}

telemetry_loop(){
  OUT=$1
  SEEN=0
  WAIT=0
  echo "sample\telapsed_s\tstream_state\tstream_hb\tgen2_source_aus\tgen2_source_idrs\tgen2_delivered_aus\tgen2_dropped_aus\tgen2_source_fps\tparity_input_fps\tparity_input_idr_fps\tparity_input_non_idr_fps\tsource_fps_x100\tsource_input_bps\tsource_last_us\tsource_min_us\tsource_max_us\tparity_input_aus\tparity_input_idrs\tparity_input_non_idr\tparity_output_started\tparity_output_completed\tparity_output_idr_started\tparity_output_non_idr_started\tsequence_gaps\tdropped_wait_idr\tsafe_recoveries\tqueue_aus\tqueue_packets\tblocks_written\tbytes_written\twrite_eagain\twrite_errors\tlast_write_us\tmax_write_us\tgate_raw" > "$OUT" 2>/dev/null || return
  N=0
  PREV_GA=
  PREV_PI=
  PREV_PII=
  PREV_PIN=
  while :; do
    if [ -e "$SESSION_LOCK" ]; then
      SEEN=1
    elif [ "$SEEN" -eq 1 ]; then
      break
    else
      WAIT=$((WAIT+1))
      [ "$WAIT" -ge 20 ] && break
    fi

    N=$((N+1))
    SS=missing
    SH=0
    [ -r "$SOURCE_STATE" ] && SS=$(cat "$SOURCE_STATE" 2>/dev/null)
    [ -r "$SOURCE_HB" ] && SH=$(cat "$SOURCE_HB" 2>/dev/null)

    GA=$(status_value "$GEN2_STATUS" source_aus)
    GI=$(status_value "$GEN2_STATUS" source_idrs)
    GD=$(status_value "$GEN2_STATUS" delivered_aus)
    GX=$(status_value "$GEN2_STATUS" dropped_aus)

    SF=$(status_value "$SOURCE_TIMING" source_arrival_fps_x100)
    SB=$(status_value "$SOURCE_TIMING" source_input_bps)
    SL=$(status_value "$SOURCE_TIMING" source_arrival_last_us)
    SMIN=$(status_value "$SOURCE_TIMING" source_arrival_min_us)
    SMAX=$(status_value "$SOURCE_TIMING" source_arrival_max_us)

    PI=$(status_value "$PARITY_STATUS" input_records)
    PII=$(status_value "$PARITY_STATUS" input_idrs)
    PIN=$(status_value "$PARITY_STATUS" input_non_idr_aus)
    POS=$(status_value "$PARITY_STATUS" output_aus_started)
    POC=$(status_value "$PARITY_STATUS" output_aus_completed)
    POI=$(status_value "$PARITY_STATUS" output_idr_aus_started)
    PON=$(status_value "$PARITY_STATUS" output_non_idr_aus_started)
    PG=$(status_value "$PARITY_STATUS" sequence_gaps)
    PD=$(status_value "$PARITY_STATUS" dropped_wait_idr)
    PR=$(status_value "$PARITY_STATUS" safe_recoveries)
    QA=$(status_value "$PARITY_STATUS" queue_aus)
    QP=$(status_value "$PARITY_STATUS" queue_packets)
    BW=$(status_value "$PARITY_STATUS" blocks_written)
    BY=$(status_value "$PARITY_STATUS" bytes_written)
    WE=$(status_value "$PARITY_STATUS" write_eagain)
    WERR=$(status_value "$PARITY_STATUS" write_errors)
    LW=$(status_value "$PARITY_STATUS" last_write_us)
    MW=$(status_value "$PARITY_STATUS" max_write_us)
    GAFPS=0
    PIFPS=0
    PIIFPS=0
    PINFPS=0
    case "$GA:$PREV_GA" in *[!0-9:]*|:*) ;; *) [ -n "$PREV_GA" ] && GAFPS=$((GA-PREV_GA)) ;; esac
    case "$PI:$PREV_PI" in *[!0-9:]*|:*) ;; *) [ -n "$PREV_PI" ] && PIFPS=$((PI-PREV_PI)) ;; esac
    case "$PII:$PREV_PII" in *[!0-9:]*|:*) ;; *) [ -n "$PREV_PII" ] && PIIFPS=$((PII-PREV_PII)) ;; esac
    case "$PIN:$PREV_PIN" in *[!0-9:]*|:*) ;; *) [ -n "$PREV_PIN" ] && PINFPS=$((PIN-PREV_PIN)) ;; esac
    PREV_GA=$GA
    PREV_PI=$PI
    PREV_PII=$PII
    PREV_PIN=$PIN

    GR=missing
    [ -r "$GATE_STATUS" ] && GR=$(cat "$GATE_STATUS" 2>/dev/null | tr '\t' ' ')

    echo "$N\t$N\t$SS\t$SH\t$GA\t$GI\t$GD\t$GX\t$GAFPS\t$PIFPS\t$PIIFPS\t$PINFPS\t$SF\t$SB\t$SL\t$SMIN\t$SMAX\t$PI\t$PII\t$PIN\t$POS\t$POC\t$POI\t$PON\t$PG\t$PD\t$PR\t$QA\t$QP\t$BW\t$BY\t$WE\t$WERR\t$LW\t$MW\t$GR" >> "$OUT" 2>/dev/null || true

    {
      echo "sample=$N"
      echo "stream_state=$SS"
      echo "stream_heartbeat=$SH"
      echo "gen2_source_aus=$GA"
      echo "gen2_source_idrs=$GI"
      echo "gen2_delivered_aus=$GD"
      echo "gen2_dropped_aus=$GX"
      echo "gen2_source_fps=$GAFPS"
      echo "parity_input_fps=$PIFPS"
      echo "parity_input_idr_fps=$PIIFPS"
      echo "parity_input_non_idr_fps=$PINFPS"
      echo "source_fps_x100=$SF"
      echo "source_input_bps=$SB"
      echo "parity_input_aus=$PI"
      echo "parity_input_idrs=$PII"
      echo "parity_input_non_idr=$PIN"
      echo "parity_output_started=$POS"
      echo "parity_output_completed=$POC"
      echo "parity_output_idr_started=$POI"
      echo "parity_output_non_idr_started=$PON"
      echo "sequence_gaps=$PG"
      echo "dropped_wait_idr=$PD"
      echo "safe_recoveries=$PR"
      echo "queue_aus=$QA"
      echo "queue_packets=$QP"
      echo "blocks_written=$BW"
      echo "bytes_written=$BY"
      echo "write_eagain=$WE"
      echo "write_errors=$WERR"
      echo "last_write_us=$LW"
      echo "max_write_us=$MW"
      echo "gate=$GR"
    } > "$LATEST_STATUS" 2>/dev/null || true

    sleep 1
  done
}

cleanup(){
  rm -f "$SOURCE_TIMING_ENABLE" "$SOURCE_TIMING_INTERVAL" "$HB" "$PIDFILE" 2>/dev/null || true
  publish stopped
}
trap cleanup 0 1 2 15

# This PID file is diagnostic only; it is never authority for signalling.
echo "$$" > "$PIDFILE" 2>/dev/null || exit 4
echo 1000 > "$SOURCE_TIMING_INTERVAL" 2>/dev/null || true
: > "$SOURCE_TIMING_ENABLE" 2>/dev/null || true

ROOT=$(choose_log_root) || exit 5
MASTER_LOG="$ROOT/drive-supervisor.log"
LATEST_STATUS="$ROOT/current.status"
echo "PARITY_DRIVE_SUPERVISOR_START pid=$ log_root=$ROOT" >> "$MASTER_LOG" 2>/dev/null || true
sync 2>/dev/null || true
publish waiting_stream111

while enabled; do
  heartbeat

  # A parity owner already present is never disturbed by the supervisor.
  if [ -e "$SESSION_LOCK" ]; then
    publish waiting_existing_owner
    sleep 1
    continue
  fi

  CUR=missing
  [ -r "$SOURCE_STATE" ] && CUR=$(cat "$SOURCE_STATE" 2>/dev/null)
  if [ "$CUR" != "streaming" ] || [ ! -r "$SOURCE_HB" ]; then
    publish waiting_stream111
    sleep 1
    continue
  fi

  SESSION=$((SESSION+1))
  RUN="$ROOT/$(stamp)-session-$SESSION"
  mkdir -p "$RUN" 2>/dev/null || { publish log_error; sleep 2; continue; }
  SESSION_LOG="$RUN/session.log"
  TELEMETRY="$RUN/telemetry.tsv"

  publish starting
  telemetry_loop "$TELEMETRY" &
  TPID=$!

  if [ "$SECONDS_PER_SESSION" -eq 0 ]; then SESSION_MODE=until-stop; else SESSION_MODE=bounded; fi
  echo "PARITY_DRIVE_SESSION_START mode=$SESSION_MODE seconds=$SECONDS_PER_SESSION" >> "$SESSION_LOG" 2>/dev/null
  echo "SESSION_START session=$SESSION dir=$RUN mode=$SESSION_MODE seconds=$SECONDS_PER_SESSION" >> "$MASTER_LOG" 2>/dev/null || true
  "$RUNNER" "$BRIDGE" tcp://127.0.0.1:19820 /dev/mlb/isoTX2 "$SECONDS_PER_SESSION" >> "$SESSION_LOG" 2>&1
  RC=$?
  echo "PARITY_DRIVE_SESSION_DONE rc=$RC" >> "$SESSION_LOG" 2>/dev/null
  echo "SESSION_DONE session=$SESSION rc=$RC dir=$RUN" >> "$MASTER_LOG" 2>/dev/null || true

  wait "$TPID" 2>/dev/null || true
  [ -r "$PARITY_STATUS" ] && cp "$PARITY_STATUS" "$RUN/parity-final.status" 2>/dev/null || true
  [ -r "$GEN2_STATUS" ] && cp "$GEN2_STATUS" "$RUN/gen2-final.status" 2>/dev/null || true
  [ -r "$SOURCE_TIMING" ] && cp "$SOURCE_TIMING" "$RUN/source-timing-final.status" 2>/dev/null || true
  [ -r /tmp/altscreen111.log ] && cp /tmp/altscreen111.log "$RUN/altscreen111.log" 2>/dev/null || true
  [ -r "$GATE_STATUS" ] && cp "$GATE_STATUS" "$RUN/gate-final.status" 2>/dev/null || true

  {
    echo "session=$SESSION"
    echo "rc=$RC"
    echo "mode=$SESSION_MODE"
    echo "seconds_limit=$SECONDS_PER_SESSION"
    echo "log_root=$ROOT"
    echo "stream_state=$(cat "$SOURCE_STATE" 2>/dev/null)"
    echo "parity_state=$(cat /tmp/mibr-parity-session.state 2>/dev/null)"
  } > "$RUN/summary.txt" 2>/dev/null || true
  sync 2>/dev/null || true

  if [ -e "$SESSION_LOCK" ]; then
    publish quarantined
    # Fail closed: never retry over an owner that did not relinquish its lock.
    while enabled && [ -e "$SESSION_LOCK" ]; do heartbeat; sleep 2; done
  else
    publish stock
    # If CarPlay remains connected after a bounded session, loop and reacquire.
    sleep 2
  fi
done

publish disabled
exit 0
