#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Guarded MU1440 long-run parity supervisor.
# It never signals stock processes. Each parity-session owns and, on exit,
# restores the temporary writev-gate route. The supervisor only waits/retries.
#
# Drive evidence is optional SD-only. Without writable SD the verified native
# Parity owner continues with diagnostics sent to /dev/null.

set -u

export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/media/gracenote/bin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin:/mnt/app/armle/usr/sbin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1

BASE=/mnt/app/root/altscreen-u2
RUNNER=$BASE/bin/parity-session
BRIDGE=$BASE/bin/direct-ts-parity
HELPER=$BASE/bin/alt111-settings
PROFILE_READY=/tmp/mibr-cpvc-profile-ready
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

STATUS_CFG_TEMP=/tmp/mibr-parity-status-enabled
STATUS_CFG_PERSIST=/mnt/app/root/mibr-parity-status-enabled
STATS_CFG_TEMP=/tmp/mibr-parity-statistics-enabled
STATS_CFG_PERSIST=/mnt/app/root/mibr-parity-statistics-enabled

CARD=/net/mmx/fs/sda0
LOGROOT=/net/mmx/fs/sda0/esd/carplay-test/logs/parity-drive
SD_RW=0
SD_LOG=0
WAIT_NEW_STREAM=0
LAST_STREAM_GEN=0
OBSERVED_DISCONNECT=0

# User pause from the input adapter and bounded same-generation reopen.
PAUSE=/tmp/mibr-parity-drive.pause
PAUSED=0
# Native gate proof loss (rc=23) may follow a descriptor or cluster-route change.
# Reopen while the same source stream remains ready, after a short cooldown.
# Only consecutive short-lived owner failures contribute to the burst limit;
# reaching that limit causes bounded backoff before retrying the live stream.
# The native owner retains proof, stop and stock-restoration authority.
REOPEN_COOLDOWN=2
REOPEN_MAX=6
REOPEN_BACKOFF=10
QUICK_SECS=20
REOPEN_COUNT=0
SESS_T0=0
SESS_DUR=0
# Initial native ownership proof can be transiently unavailable (rc=21).
# No custom payload has started in that state; retry after a bounded delay.
# The retry does not claim display activation or replace native owner admission.
OWN_RETRY=0
FASTSHOW=0
OWN_RETRY_MAX=40
OWN_RETRY_DELAY=3

# 0 means true until-stop operation. Finite 60..7200 second sessions remain
# available as a diagnostic override through MIBR_PARITY_DRIVE_SECONDS.
DEFAULT_SECONDS=0
SECONDS_PER_SESSION=${MIBR_PARITY_DRIVE_SECONDS:-$DEFAULT_SECONDS}
SEQ=0
SESSION=0
RUN=sd_logging_disabled
TIMING_ENABLE_OWNED=0
TIMING_INTERVAL_OWNED=0
STATUS_ON=1
STATS_ON=1

case "$SECONDS_PER_SESSION" in
  *[!0-9]*|'') exit 2 ;;
esac
if [ "$SECONDS_PER_SESSION" -ne 0 ]; then
  [ "$SECONDS_PER_SESSION" -ge 60 ] && [ "$SECONDS_PER_SESSION" -le 7200 ] || exit 2
fi
[ -x "$RUNNER" ] && [ -x "$BRIDGE" ] && [ -x "$HELPER" ] || exit 3

enabled(){
  [ -r "$ENABLE" ] || return 1
  V=$(cat "$ENABLE" 2>/dev/null)
  [ "$V" = "1" ]
}

cfg_bool(){
  T=$1
  P=$2
  D=$3
  if [ -r "$T" ]; then V=$(cat "$T" 2>/dev/null)
  elif [ -r "$P" ]; then V=$(cat "$P" 2>/dev/null)
  else V=$D
  fi
  case "$V" in
    1|on|yes|true) echo 1 ;;
    0|off|no|false) echo 0 ;;
    *) echo "$D" ;;
  esac
}

cfg_source(){
  T=$1
  P=$2
  [ -r "$T" ] && { echo temp; return; }
  [ -r "$P" ] && { echo persistent; return; }
  echo default
}

load_diagnostics(){
  STATUS_ON=$(cfg_bool "$STATUS_CFG_TEMP" "$STATUS_CFG_PERSIST" 1)
  STATS_ON=$(cfg_bool "$STATS_CFG_TEMP" "$STATS_CFG_PERSIST" 1)
  # Persistent statistics require the bridge's live status counters. Refuse
  # the contradictory manual file combination rather than silently fabricate.
  if [ "$STATS_ON" = "1" ] && [ "$STATUS_ON" != "1" ]; then
    STATS_ON=0
  fi
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

sd_make_rw(){
  [ -d "$CARD" ] || return 1
  # Exact MU1440/M.I.B. contract used in the vehicle: remount this SD volume
  # writable directly. Do not rely on an optional SD-side helper script.
  mount -uw /net/mmx/fs/sda0 2>/dev/null || return 1
  SD_RW=1
  mkdir -p "$LOGROOT" 2>/dev/null || { sd_make_ro >/dev/null 2>&1; return 1; }
  T="$LOGROOT/.write-test-parity-drive"
  : > "$T" 2>/dev/null || { sd_make_ro >/dev/null 2>&1; return 1; }
  [ -f "$T" ] || { sd_make_ro >/dev/null 2>&1; return 1; }
  rm -f "$T" 2>/dev/null || { sd_make_ro >/dev/null 2>&1; return 1; }
  return 0
}

sd_make_ro(){
  [ "$SD_RW" -eq 1 ] || return 0
  sync 2>/dev/null || true
  mount -ur /net/mmx/fs/sda0 2>/dev/null || return 1
  SD_RW=0
  return 0
}

configure_timing(){
  # Never remove or overwrite a foreign diagnostic setting; do not touch these
  # controls at all without SD-backed evidence collection.
  [ "$SD_LOG" -eq 1 ] || return 0
  if [ "$STATUS_ON" = "1" ] || [ "$STATS_ON" = "1" ]; then
    if [ ! -e "$SOURCE_TIMING_INTERVAL" ]; then
      echo 1000 > "$SOURCE_TIMING_INTERVAL" 2>/dev/null && TIMING_INTERVAL_OWNED=1
    fi
    if [ ! -e "$SOURCE_TIMING_ENABLE" ]; then
      : > "$SOURCE_TIMING_ENABLE" 2>/dev/null && TIMING_ENABLE_OWNED=1
    fi
  fi
}

publish_current_status(){
  OUT=$1
  SAMPLE=$2
  {
    echo "sample=$SAMPLE"
    echo "supervisor_state=$(cat "$STATE" 2>/dev/null)"
    echo "session_state=$(cat /tmp/mibr-parity-session.state 2>/dev/null)"
    echo "stream111_state=$(cat "$SOURCE_STATE" 2>/dev/null)"
    echo "stream111_heartbeat=$(cat "$SOURCE_HB" 2>/dev/null)"
    echo "--- parity ---"
    [ -r "$PARITY_STATUS" ] && cat "$PARITY_STATUS" 2>/dev/null || echo "parity_status=missing"
    echo "--- gen2 ---"
    [ -r "$GEN2_STATUS" ] && cat "$GEN2_STATUS" 2>/dev/null || echo "gen2_status=missing"
    echo "--- source timing ---"
    [ -r "$SOURCE_TIMING" ] && cat "$SOURCE_TIMING" 2>/dev/null || echo "source_timing=missing"
    echo "--- gate ---"
    [ -r "$GATE_STATUS" ] && cat "$GATE_STATUS" 2>/dev/null || echo "gate_status=missing"
  } > "$OUT" 2>/dev/null || true
}

append_raw_status(){
  OUT=$1
  SAMPLE=$2
  {
    echo "===== sample=$SAMPLE ====="
    [ -r /tmp/mibr-parity-session.state ] && echo "session_state=$(cat /tmp/mibr-parity-session.state 2>/dev/null)"
    [ -r "$SOURCE_STATE" ] && echo "stream111_state=$(cat "$SOURCE_STATE" 2>/dev/null)"
    [ -r "$SOURCE_HB" ] && echo "stream111_heartbeat=$(cat "$SOURCE_HB" 2>/dev/null)"
    echo "--- parity ---"
    [ -r "$PARITY_STATUS" ] && cat "$PARITY_STATUS" 2>/dev/null || echo "parity_status=missing"
    echo "--- gen2 ---"
    [ -r "$GEN2_STATUS" ] && cat "$GEN2_STATUS" 2>/dev/null || echo "gen2_status=missing"
    echo "--- source timing ---"
    [ -r "$SOURCE_TIMING" ] && cat "$SOURCE_TIMING" 2>/dev/null || echo "source_timing=missing"
    echo "--- gate ---"
    [ -r "$GATE_STATUS" ] && cat "$GATE_STATUS" 2>/dev/null || echo "gate_status=missing"
    echo
  } >> "$OUT" 2>/dev/null || true
}

evidence_loop(){
  RUN=$1
  TELEMETRY="$RUN/telemetry.tsv"
  SNAPSHOTS="$RUN/status-snapshots.log"
  SEEN=0
  WAIT=0
  N=0
  PREV_GA=
  PREV_PI=
  PREV_PII=
  PREV_PIN=

  if [ "$STATS_ON" = "1" ]; then
    echo "sample\telapsed_s\tstream_state\tstream_hb\tgen2_source_aus\tgen2_source_idrs\tgen2_delivered_aus\tgen2_dropped_aus\tgen2_source_fps\tparity_input_fps\tparity_input_idr_fps\tparity_input_non_idr_fps\tsource_fps_x100\tsource_input_bps\tsource_last_us\tsource_min_us\tsource_max_us\tparity_input_aus\tparity_input_idrs\tparity_input_non_idr\tparity_output_started\tparity_output_completed\tparity_output_idr_started\tparity_output_non_idr_started\tparity_output_idr_completed\tparity_output_non_idr_completed\tinput_slice_p\tinput_slice_b\tinput_slice_i\tinput_slice_unknown\toutput_slice_p_started\toutput_slice_b_started\toutput_slice_i_started\toutput_slice_unknown_started\toutput_slice_p_completed\toutput_slice_b_completed\toutput_slice_i_completed\toutput_slice_unknown_completed\tsequence_gaps\tdropped_wait_idr\tsafe_recoveries\tqueue_aus\tqueue_packets\tblocks_written\tbytes_written\twrite_eagain\twrite_errors\tlast_write_us\tmax_write_us\tgate_raw" > "$TELEMETRY" 2>/dev/null || return
  fi
  [ "$STATUS_ON" = "1" ] && : > "$SNAPSHOTS" 2>/dev/null || true

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

    if [ "$STATUS_ON" = "1" ]; then
      append_raw_status "$SNAPSHOTS" "$N"
      publish_current_status "$LATEST_STATUS" "$N"
    fi

    if [ "$STATS_ON" = "1" ]; then
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
      ISP=$(status_value "$PARITY_STATUS" input_slice_p)
      ISB=$(status_value "$PARITY_STATUS" input_slice_b)
      ISI=$(status_value "$PARITY_STATUS" input_slice_i)
      ISU=$(status_value "$PARITY_STATUS" input_slice_unknown)
      POS=$(status_value "$PARITY_STATUS" output_aus_started)
      POC=$(status_value "$PARITY_STATUS" output_aus_completed)
      POI=$(status_value "$PARITY_STATUS" output_idr_aus_started)
      PON=$(status_value "$PARITY_STATUS" output_non_idr_aus_started)
      POIC=$(status_value "$PARITY_STATUS" output_idr_aus_completed)
      PONC=$(status_value "$PARITY_STATUS" output_non_idr_aus_completed)
      OSP=$(status_value "$PARITY_STATUS" output_slice_p_started)
      OSB=$(status_value "$PARITY_STATUS" output_slice_b_started)
      OSI=$(status_value "$PARITY_STATUS" output_slice_i_started)
      OSU=$(status_value "$PARITY_STATUS" output_slice_unknown_started)
      OCP=$(status_value "$PARITY_STATUS" output_slice_p_completed)
      OCB=$(status_value "$PARITY_STATUS" output_slice_b_completed)
      OCI=$(status_value "$PARITY_STATUS" output_slice_i_completed)
      OCU=$(status_value "$PARITY_STATUS" output_slice_unknown_completed)
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
      [ -n "$PREV_GA" ] && GAFPS=$((GA-PREV_GA))
      [ -n "$PREV_PI" ] && PIFPS=$((PI-PREV_PI))
      [ -n "$PREV_PII" ] && PIIFPS=$((PII-PREV_PII))
      [ -n "$PREV_PIN" ] && PINFPS=$((PIN-PREV_PIN))
      PREV_GA=$GA
      PREV_PI=$PI
      PREV_PII=$PII
      PREV_PIN=$PIN

      GR=missing
      [ -r "$GATE_STATUS" ] && GR=$(awk '{gsub(sprintf("%c",9)," "); print}' "$GATE_STATUS" 2>/dev/null)

      echo "$N\t$N\t$SS\t$SH\t$GA\t$GI\t$GD\t$GX\t$GAFPS\t$PIFPS\t$PIIFPS\t$PINFPS\t$SF\t$SB\t$SL\t$SMIN\t$SMAX\t$PI\t$PII\t$PIN\t$POS\t$POC\t$POI\t$PON\t$POIC\t$PONC\t$ISP\t$ISB\t$ISI\t$ISU\t$OSP\t$OSB\t$OSI\t$OSU\t$OCP\t$OCB\t$OCI\t$OCU\t$PG\t$PD\t$PR\t$QA\t$QP\t$BW\t$BY\t$WE\t$WERR\t$LW\t$MW\t$GR" >> "$TELEMETRY" 2>/dev/null || true

      {
        echo "sample=$N"
        echo "stream_state=$SS"
        echo "gen2_source_fps=$GAFPS"
        echo "parity_input_fps=$PIFPS"
        echo "parity_input_idr_fps=$PIIFPS"
        echo "parity_input_non_idr_fps=$PINFPS"
        echo "source_fps_x100=$SF"
        echo "input_slice_p=$ISP"
        echo "input_slice_b=$ISB"
        echo "input_slice_i=$ISI"
        echo "parity_output_idr_completed=$POIC"
        echo "parity_output_non_idr_completed=$PONC"
        echo "output_slice_p_completed=$OCP"
        echo "output_slice_b_completed=$OCB"
        echo "output_slice_i_completed=$OCI"
        echo "output_slice_unknown_completed=$OCU"
        echo "blocks_written=$BW"
        echo "write_eagain=$WE"
        echo "write_errors=$WERR"
        echo "last_write_us=$LW"
        echo "max_write_us=$MW"
        echo "gate=$GR"
      } > "$LATEST_STATS" 2>/dev/null || true
    fi

    if [ $((N % 30)) -eq 0 ]; then sync 2>/dev/null || true; fi
    sleep 1
  done
}

cleanup(){
  [ "$TIMING_ENABLE_OWNED" -eq 0 ] || rm -f "$SOURCE_TIMING_ENABLE" 2>/dev/null || true
  [ "$TIMING_INTERVAL_OWNED" -eq 0 ] || rm -f "$SOURCE_TIMING_INTERVAL" 2>/dev/null || true
  rm -f "$HB" "$PIDFILE" 2>/dev/null || true
  publish stopped
  sd_make_ro >/dev/null 2>&1 || true
}
trap cleanup 0 1 2 15

# This PID file is diagnostic only; it is never authority for signalling.
if [ -r "$PIDFILE" ]; then
  OLD=$(cat "$PIDFILE" 2>/dev/null)
  if [ -n "$OLD" ] && pidin ar 2>/dev/null | grep -E "^[[:space:]]*$OLD[[:space:]]" | grep -F 'parity_drive_supervisor.sh' >/dev/null 2>&1; then
    echo "PARITY_DRIVE_SUPERVISOR=ALREADY_RUNNING pid=$OLD"
    exit 0
  fi
fi
SELF_PID=$(pidin ar 2>/dev/null | awk '/[p]arity_drive_supervisor.sh/ {p=$1} END {print p}')
[ -n "$SELF_PID" ] || exit 4
echo "$SELF_PID" > "$PIDFILE" 2>/dev/null || exit 4

# CPVC boot replay is synchronous, guarded and strictly before J9.
[ -e "$PROFILE_READY" ] || { publish profile_not_replayed; exit 6; }
"$HELPER" status >/dev/null 2>&1 || { publish invalid_settings; exit 6; }
# SD logging is optional for autonomous persistent operation.
MASTER_LOG=/dev/null
LATEST_STATUS=/dev/null
LATEST_STATS=/dev/null
if sd_make_rw; then
  SD_LOG=1
  MASTER_LOG="$LOGROOT/drive-supervisor.log"
  LATEST_STATUS="$LOGROOT/current.status"
  LATEST_STATS="$LOGROOT/current.statistics"
else
  SD_LOG=0
  sd_make_ro >/dev/null 2>&1 || true
fi
echo "SUPERVISOR_START pid=$SELF_PID sd_log=$SD_LOG" >> "$MASTER_LOG" 2>/dev/null || true

publish waiting_stream111

while enabled; do
  heartbeat

  # r21: explicit user pause. The Parity owner was stopped gracefully by mibr-key40d (stock is
  # restored by the owner itself). Resume = pause file removed: reopen on the live stream.
  if [ -e "$PAUSE" ]; then
    PAUSED=1
    publish paused_by_user
    # r27: poll the pause file at 0.2 s so a resume is noticed at once (was 1 s)
    sleep 0.2
    continue
  fi
  if [ "$PAUSED" -eq 1 ]; then
    PAUSED=0
    WAIT_NEW_STREAM=0
    OBSERVED_DISCONNECT=0
    FASTSHOW=1
    echo "RESUME_BY_USER" >> "$MASTER_LOG" 2>/dev/null || true
  fi

  # A parity owner already present is never disturbed by the supervisor.
  if [ -e "$SESSION_LOCK" ]; then
    publish waiting_existing_owner
    sleep 1
    continue
  fi

  CUR=missing
  [ -r "$SOURCE_STATE" ] && CUR=$(cat "$SOURCE_STATE" 2>/dev/null)

  # Only reopen on a newly observed stream generation or disconnect/reconnect.
  if [ "$WAIT_NEW_STREAM" -eq 1 ]; then
    [ "$CUR" != "streaming" ] && OBSERVED_DISCONNECT=1
    NOW_GEN=$(status_value "$GEN2_STATUS" stream_gen)
    if [ "$CUR" = "streaming" ] && {
      [ "$OBSERVED_DISCONNECT" -eq 1 ] || {
        [ "$NOW_GEN" != "0" ] && [ "$NOW_GEN" != "$LAST_STREAM_GEN" ];
      };
    }; then
      WAIT_NEW_STREAM=0
      OBSERVED_DISCONNECT=0
    else
      publish waiting_fresh_stream111
      sleep 1
      continue
    fi
  fi

  if [ "$CUR" != "streaming" ] || [ ! -r "$SOURCE_HB" ]; then
    publish waiting_stream111
    sleep 1
    continue
  fi

  load_diagnostics
  if [ "$SD_LOG" -ne 1 ]; then STATUS_ON=0; STATS_ON=0; fi
  configure_timing
  LAST_STREAM_GEN=$(status_value "$GEN2_STATUS" stream_gen)

  SESSION=$((SESSION+1))
  EPID=""
  RUN=sd_logging_disabled
  SESSION_LOG=/dev/null
  if [ "$SD_LOG" -eq 1 ]; then
    RUN="$LOGROOT/$(stamp)-session-$SESSION"
    if mkdir -p "$RUN" 2>/dev/null && : > "$RUN/.write-test" 2>/dev/null; then
      rm -f "$RUN/.write-test" 2>/dev/null || true
      SESSION_LOG="$RUN/session.log"
      if [ "$STATUS_ON" = "1" ] || [ "$STATS_ON" = "1" ]; then
        evidence_loop "$RUN" &
        EPID=$!
      fi
    else
      # A failed or removed SD must never prevent a native Parity session.
      SD_LOG=0
      MASTER_LOG=/dev/null
      sd_make_ro >/dev/null 2>&1 || true
    fi
  fi
  publish starting

  if [ "$SECONDS_PER_SESSION" -eq 0 ]; then SESSION_MODE=until-stop; else SESSION_MODE=bounded; fi
  {
    echo "PARITY_DRIVE_SESSION_START mode=$SESSION_MODE seconds=$SECONDS_PER_SESSION"
    echo "diagnostics_status=$STATUS_ON source=$(cfg_source "$STATUS_CFG_TEMP" "$STATUS_CFG_PERSIST")"
    echo "diagnostics_statistics=$STATS_ON source=$(cfg_source "$STATS_CFG_TEMP" "$STATS_CFG_PERSIST")"
    echo "sd_log_root=$LOGROOT"
  } >> "$SESSION_LOG" 2>/dev/null
  echo "SESSION_START session=$SESSION mode=$SESSION_MODE dir=$RUN" >> "$MASTER_LOG" 2>/dev/null || true

  # r29: after a resume/reopen on the SAME stream generation the cockpit is not told to show the
  # view area again (the log shows only the keyframe cadence). Ask GEN2 for the proven explicit
  # re-show (same marker the broker uses for every live setting change) shortly after the start.
  if [ "$FASTSHOW" = 1 ]; then
    FASTSHOW=0
    ( sleep 2; echo request > /tmp/mibr-alt111-gen2-reacquire; sleep 3; echo request > /tmp/mibr-alt111-gen2-reacquire ) >/dev/null 2>&1 &
  fi
  SESS_T0=$SECONDS
  "$RUNNER" "$BRIDGE" tcp://127.0.0.1:19820 /dev/mlb/isoTX2 "$SECONDS_PER_SESSION" >> "$SESSION_LOG" 2>&1
  RC=$?
  SESS_DUR=$((SECONDS-SESS_T0))
  echo "PARITY_DRIVE_SESSION_DONE rc=$RC" >> "$SESSION_LOG" 2>/dev/null
  echo "SESSION_DONE session=$SESSION rc=$RC dir=$RUN" >> "$MASTER_LOG" 2>/dev/null || true

  [ -z "$EPID" ] || wait "$EPID" 2>/dev/null || true
  if [ "$SD_LOG" -eq 1 ]; then
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
      echo "diagnostics_status=$STATUS_ON"
      echo "diagnostics_statistics=$STATS_ON"
      echo "stream_state=$(cat "$SOURCE_STATE" 2>/dev/null)"
      echo "parity_state=$(cat /tmp/mibr-parity-session.state 2>/dev/null)"
    } > "$RUN/summary.txt" 2>/dev/null || true
    sync 2>/dev/null || true
  fi

  # Anchor the reopening barrier to the generation at EXIT, not start.
  # A generation change during the previous owner session does not justify
  # reopening immediately against the still-running same generation.
  LAST_STREAM_GEN=$(status_value "$GEN2_STATUS" stream_gen)
  WAIT_NEW_STREAM=1
  OBSERVED_DISCONNECT=0
  if [ -e "$SESSION_LOCK" ]; then
    publish quarantined
    # Fail closed: never retry over an owner that did not relinquish its lock.
    while enabled && [ -e "$SESSION_LOCK" ]; do heartbeat; sleep 2; done
  else
    publish stock
    # On disconnect/bridge exit, wait for the next valid Stream-111 session.
    sleep 1
    if [ "$RC" -eq 21 ] && [ ! -e "$PAUSE" ] && [ ! -e "$SESSION_LOCK" ]; then
      OWN_RETRY=$((OWN_RETRY+1))
      if [ "$OWN_RETRY" -le "$OWN_RETRY_MAX" ]; then
        WAIT_NEW_STREAM=0
        OBSERVED_DISCONNECT=0
        publish retry_ownership_unproven
        echo "RETRY_OWNERSHIP_UNPROVEN try=$OWN_RETRY" >> "$MASTER_LOG" 2>/dev/null || true
        sleep "$OWN_RETRY_DELAY"
        continue
      fi
    else
      OWN_RETRY=0
    fi
    # r21: the Parity owner ended with the stock route confirmed (no owner lock) while the very
    # same Stream-111 generation keeps running (the VC loses CarPlay, the main display does not).
    # Reopen after a cooldown, at most REOPEN_MAX times per REOPEN_WINDOW seconds, then fall back
    # to the old rule (wait for a new stream generation).
    if [ ! -e "$PAUSE" ] && [ ! -e "$SESSION_LOCK" ]; then
      sleep "$REOPEN_COOLDOWN"
      CUR2=missing
      [ -r "$SOURCE_STATE" ] && CUR2=$(cat "$SOURCE_STATE" 2>/dev/null)
      if [ "$CUR2" = "streaming" ] && [ ! -e "$PAUSE" ] && [ ! -e "$SESSION_LOCK" ]; then
        # An owner that ran long enough was healthy: its end is a new event, not a failure loop.
        if [ "$SESS_DUR" -ge "$QUICK_SECS" ]; then REOPEN_COUNT=0; fi
        REOPEN_COUNT=$((REOPEN_COUNT+1))
        if [ "$REOPEN_COUNT" -gt "$REOPEN_MAX" ]; then
          echo "REOPEN_BACKOFF count=$REOPEN_COUNT dur=$SESS_DUR" >> "$MASTER_LOG" 2>/dev/null || true
          sleep "$REOPEN_BACKOFF"
        fi
        WAIT_NEW_STREAM=0
        OBSERVED_DISCONNECT=0
        FASTSHOW=1
        echo "REOPEN_SAME_GENERATION count=$REOPEN_COUNT gen=$LAST_STREAM_GEN dur=$SESS_DUR rc=$RC" >> "$MASTER_LOG" 2>/dev/null || true
        publish reopening_same_generation
      fi
    fi
  fi
done

publish disabled
exit 0
