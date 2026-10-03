#!/bin/ksh
set -u

SESSION_MARKER=/tmp/mibr-alt111-keyframe-policy.enabled
PERSIST_MARKER=/mnt/app/root/mibr-alt111-keyframe-policy.enabled
TIMING_CONFIG=/mnt/app/root/mibr-carplay111-keyframes.conf
STATUS=/tmp/mibr-alt111-gen2.status

DEFAULT_EVENT_DELAY_MS=250
DEFAULT_MIN_GAP_MS=1000
DEFAULT_WATCHDOG_MS=1000

usage(){
  echo "usage: $0 status|on|off|session-on|session-off|timing EVENT_DELAY_MS MIN_GAP_MS WATCHDOG_MS|timing-default"
  echo "       watchdog_ms=0 disables only the periodic source-IDR watchdog"
  exit 2
}

enabled(){
  [ -e "$SESSION_MARKER" ] || [ -e "$PERSIST_MARKER" ]
}

is_uint(){
  case "${1:-}" in
    ''|*[!0-9]*) return 1 ;;
    *) return 0 ;;
  esac
}

show_timing(){
  echo "timing_config=$TIMING_CONFIG"
  if [ -r "$TIMING_CONFIG" ]; then
    echo "timing_config_state=file"
    cat "$TIMING_CONFIG" 2>/dev/null || true
  else
    echo "timing_config_state=default"
    echo "event_delay_ms=$DEFAULT_EVENT_DELAY_MS"
    echo "min_gap_ms=$DEFAULT_MIN_GAP_MS"
    echo "watchdog_ms=$DEFAULT_WATCHDOG_MS"
  fi
  echo "watchdog_note=0 disables watchdog; event/suggestUI recovery remains active"
  if [ -r "$STATUS" ]; then
    grep '^d2_event_delay_ms=' "$STATUS" 2>/dev/null || true
    grep '^d2_min_gap_ms=' "$STATUS" 2>/dev/null || true
    grep '^d2_watchdog_ms=' "$STATUS" 2>/dev/null || true
    grep '^d2_watchdog_enabled=' "$STATUS" 2>/dev/null || true
    grep '^d2_timing_source=' "$STATUS" 2>/dev/null || true
  fi
}

write_timing(){
  EVENT=$1
  GAP=$2
  WATCHDOG=$3
  is_uint "$EVENT" && is_uint "$GAP" && is_uint "$WATCHDOG" || usage
  [ "$EVENT" -le 5000 ] || { echo "GEN2_D2_TIMING=FAIL event_delay_ms_range_0_5000"; exit 3; }
  [ "$GAP" -le 60000 ] || { echo "GEN2_D2_TIMING=FAIL min_gap_ms_range_0_60000"; exit 3; }
  [ "$WATCHDOG" -le 60000 ] || { echo "GEN2_D2_TIMING=FAIL watchdog_ms_range_0_60000"; exit 3; }

  mount -uw /mnt/app 2>/dev/null || { echo "GEN2_D2_TIMING=FAIL mount_rw"; exit 4; }
  TMP="$TIMING_CONFIG.new.$$"
  {
    echo "event_delay_ms=$EVENT"
    echo "min_gap_ms=$GAP"
    echo "watchdog_ms=$WATCHDOG"
  } > "$TMP" || {
    rm -f "$TMP" 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    echo "GEN2_D2_TIMING=FAIL write"
    exit 5
  }
  mv "$TMP" "$TIMING_CONFIG" || {
    rm -f "$TMP" 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    echo "GEN2_D2_TIMING=FAIL replace"
    exit 6
  }
  chmod 644 "$TIMING_CONFIG" 2>/dev/null || true
  sync
  mount -ur /mnt/app 2>/dev/null || true
  echo "GEN2_D2_TIMING=SET event_delay_ms=$EVENT min_gap_ms=$GAP watchdog_ms=$WATCHDOG"
  [ "$WATCHDOG" -eq 0 ] && echo "GEN2_D2_WATCHDOG=DISABLED"
  echo "Applied live; no CarPlay reconnect or unit reboot required."
}

case "${1:-status}" in
  status)
    enabled && echo "GEN2_D2_KEYFRAMES=ENABLED" || echo "GEN2_D2_KEYFRAMES=DISABLED"
    if [ -e "$PERSIST_MARKER" ]; then
      echo "GEN2_D2_MODE=persistent"
    elif [ -e "$SESSION_MARKER" ]; then
      echo "GEN2_D2_MODE=session"
    else
      echo "GEN2_D2_MODE=off"
    fi
    echo "persistent_marker=$PERSIST_MARKER"
    echo "session_marker=$SESSION_MARKER"
    show_timing
    if [ -r "$STATUS" ]; then
      grep '^d2_' "$STATUS" 2>/dev/null || true
      grep '^resync_' "$STATUS" 2>/dev/null || true
      grep '^source_idrs=' "$STATUS" 2>/dev/null || true
    else
      echo "GEN2_CORE_STATUS=NOT_AVAILABLE"
    fi
    ;;
  on)
    touch "$PERSIST_MARKER" || exit 1
    touch "$SESSION_MARKER" 2>/dev/null || true
    sync
    echo "GEN2_D2_KEYFRAMES=ENABLED"
    echo "GEN2_D2_MODE=persistent"
    show_timing
    echo "Persistent across unit reboot. No reboot required for the current session."
    ;;
  off)
    rm -f "$PERSIST_MARKER" "$SESSION_MARKER"
    sync
    echo "GEN2_D2_KEYFRAMES=DISABLED"
    echo "GEN2_D2_MODE=off"
    echo "No reboot required. Manual Candidate-D controls remain separate."
    ;;
  session-on)
    touch "$SESSION_MARKER" || exit 1
    sync
    echo "GEN2_D2_KEYFRAMES=ENABLED"
    echo "GEN2_D2_MODE=session"
    show_timing
    echo "Volatile session-only enable; cleared by reboot."
    ;;
  session-off)
    rm -f "$SESSION_MARKER"
    sync
    if [ -e "$PERSIST_MARKER" ]; then
      echo "GEN2_D2_KEYFRAMES=ENABLED"
      echo "GEN2_D2_MODE=persistent"
    else
      echo "GEN2_D2_KEYFRAMES=DISABLED"
      echo "GEN2_D2_MODE=off"
    fi
    ;;
  timing)
    [ "$#" -eq 4 ] || usage
    write_timing "$2" "$3" "$4"
    ;;
  timing-default)
    mount -uw /mnt/app 2>/dev/null || { echo "GEN2_D2_TIMING=FAIL mount_rw"; exit 4; }
    rm -f "$TIMING_CONFIG" || {
      mount -ur /mnt/app 2>/dev/null || true
      echo "GEN2_D2_TIMING=FAIL remove"
      exit 5
    }
    sync
    mount -ur /mnt/app 2>/dev/null || true
    echo "GEN2_D2_TIMING=DEFAULT event_delay_ms=$DEFAULT_EVENT_DELAY_MS min_gap_ms=$DEFAULT_MIN_GAP_MS watchdog_ms=$DEFAULT_WATCHDOG_MS"
    echo "Applied live; no CarPlay reconnect or unit reboot required."
    ;;
  *)
    usage
    ;;
esac
