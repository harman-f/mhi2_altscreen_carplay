#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

NAME=mibr-carplay111-keyframes.conf
TEMP=/tmp/$NAME
PERSIST=/mnt/app/root/$NAME
STATUS=/tmp/mibr-alt111-gen2.status

DEFAULT_ENABLED=1
DEFAULT_EVENT_DELAY_MS=250
DEFAULT_MIN_GAP_MS=1000
DEFAULT_WATCHDOG_MS=1000

usage(){
  echo "usage:"
  echo "  $0 status"
  echo "  $0 on|off                         # temporary"
  echo "  $0 temp on|off"
  echo "  $0 persist on|off"
  echo "  $0 timing EVENT MIN_GAP WATCHDOG  # temporary"
  echo "  $0 temp timing EVENT MIN_GAP WATCHDOG"
  echo "  $0 persist timing EVENT MIN_GAP WATCHDOG"
  echo "  $0 clear-temp|clear-persist|default"
  echo "watchdog_ms=0 disables only the periodic source-IDR watchdog"
  exit 2
}

is_uint(){
  case "${1:-}" in ''|*[!0-9]*) return 1 ;; *) return 0 ;; esac
}

source_file(){
  [ -r "$TEMP" ] && { echo "$TEMP"; return; }
  [ -r "$PERSIST" ] && { echo "$PERSIST"; return; }
  echo ""
}

source_name(){
  [ -r "$TEMP" ] && { echo temp; return; }
  [ -r "$PERSIST" ] && { echo persistent; return; }
  echo default
}

field(){
  F=$1
  K=$2
  D=$3
  if [ -n "$F" ] && [ -r "$F" ]; then
    V=$(awk -F= -v k="$K" '$1==k {print substr($0,index($0,"=")+1); exit}' "$F" 2>/dev/null)
    [ -n "$V" ] && { echo "$V"; return; }
  fi
  echo "$D"
}

load_effective(){
  F=$(source_file)
  E=$(field "$F" enabled "$DEFAULT_ENABLED")
  D=$(field "$F" event_delay_ms "$DEFAULT_EVENT_DELAY_MS")
  G=$(field "$F" min_gap_ms "$DEFAULT_MIN_GAP_MS")
  W=$(field "$F" watchdog_ms "$DEFAULT_WATCHDOG_MS")
  case "$E" in 0|1) ;; *) E=$DEFAULT_ENABLED ;; esac
  is_uint "$D" || D=$DEFAULT_EVENT_DELAY_MS
  is_uint "$G" || G=$DEFAULT_MIN_GAP_MS
  is_uint "$W" || W=$DEFAULT_WATCHDOG_MS
  [ "$D" -le 5000 ] || D=$DEFAULT_EVENT_DELAY_MS
  [ "$G" -le 60000 ] || G=$DEFAULT_MIN_GAP_MS
  [ "$W" -le 60000 ] || W=$DEFAULT_WATCHDOG_MS
}

validate_timing(){
  is_uint "$1" && is_uint "$2" && is_uint "$3" || return 1
  [ "$1" -le 5000 ] && [ "$2" -le 60000 ] && [ "$3" -le 60000 ]
}

write_file(){
  LAYER=$1
  ENABLED=$2
  EVENT=$3
  GAP=$4
  WATCHDOG=$5

  case "$ENABLED" in 0|1) ;; *) usage ;; esac
  validate_timing "$EVENT" "$GAP" "$WATCHDOG" || {
    echo "GEN2_D2=FAIL timing_range event=0..5000 min_gap=0..60000 watchdog=0..60000"
    exit 3
  }

  case "$LAYER" in
    temp)
      TARGET=$TEMP
      ;;
    persistent)
      TARGET=$PERSIST
      mount -uw /mnt/app 2>/dev/null || { echo "GEN2_D2=FAIL mount_rw"; exit 4; }
      ;;
    *) usage ;;
  esac

  T="$TARGET.new.$$"
  {
    echo "enabled=$ENABLED"
    echo "event_delay_ms=$EVENT"
    echo "min_gap_ms=$GAP"
    echo "watchdog_ms=$WATCHDOG"
  } > "$T" || {
    rm -f "$T" 2>/dev/null || true
    [ "$LAYER" = persistent ] && mount -ur /mnt/app 2>/dev/null || true
    echo "GEN2_D2=FAIL write layer=$LAYER"
    exit 5
  }
  mv "$T" "$TARGET" || {
    rm -f "$T" 2>/dev/null || true
    [ "$LAYER" = persistent ] && mount -ur /mnt/app 2>/dev/null || true
    echo "GEN2_D2=FAIL replace layer=$LAYER"
    exit 6
  }
  chmod 644 "$TARGET" 2>/dev/null || true
  if [ "$LAYER" = persistent ]; then
    sync
    mount -ur /mnt/app 2>/dev/null || true
  fi
  echo "GEN2_D2=SET layer=$LAYER enabled=$ENABLED event_delay_ms=$EVENT min_gap_ms=$GAP watchdog_ms=$WATCHDOG"
  echo "applied=live"
}

clear_layer(){
  LAYER=$1
  case "$LAYER" in
    temp)
      rm -f "$TEMP" 2>/dev/null || true
      ;;
    persistent)
      mount -uw /mnt/app 2>/dev/null || { echo "GEN2_D2=FAIL mount_rw"; exit 4; }
      rm -f "$PERSIST" 2>/dev/null || true
      sync
      mount -ur /mnt/app 2>/dev/null || true
      ;;
    *) usage ;;
  esac
  echo "GEN2_D2=CLEAR layer=$LAYER"
  echo "effective_source=$(source_name)"
}

show_status(){
  load_effective
  echo "=== GEN2 D2 KEYFRAME POLICY ==="
  echo "default_enabled=$DEFAULT_ENABLED"
  echo "default_event_delay_ms=$DEFAULT_EVENT_DELAY_MS"
  echo "default_min_gap_ms=$DEFAULT_MIN_GAP_MS"
  echo "default_watchdog_ms=$DEFAULT_WATCHDOG_MS"
  echo "effective_source=$(source_name)"
  echo "effective_enabled=$E"
  echo "effective_event_delay_ms=$D"
  echo "effective_min_gap_ms=$G"
  echo "effective_watchdog_ms=$W"
  echo "temporary_path=$TEMP"
  [ -r "$TEMP" ] && { echo "temporary_config=present"; cat "$TEMP"; } || echo "temporary_config=none"
  echo "persistent_path=$PERSIST"
  [ -r "$PERSIST" ] && { echo "persistent_config=present"; cat "$PERSIST"; } || echo "persistent_config=none"
  echo "note=controls receiver-requested forceKeyFrame recovery, not Apple's native GOP"
  if [ -r "$STATUS" ]; then
    grep '^d2_' "$STATUS" 2>/dev/null || true
    grep '^resync_' "$STATUS" 2>/dev/null || true
    grep '^source_idrs=' "$STATUS" 2>/dev/null || true
  else
    echo "GEN2_CORE_STATUS=NOT_AVAILABLE"
  fi
}

cmd=${1:-status}
case "$cmd" in
  status)
    show_status
    ;;
  on|off)
    load_effective
    [ "$cmd" = on ] && E=1 || E=0
    write_file temp "$E" "$D" "$G" "$W"
    ;;
  timing)
    [ "$#" -eq 4 ] || usage
    load_effective
    write_file temp "$E" "$2" "$3" "$4"
    ;;
  temp|persist)
    [ "$#" -ge 2 ] || usage
    [ "$cmd" = temp ] && L=temp || L=persistent
    sub=$2
    case "$sub" in
      on|off)
        [ "$#" -eq 2 ] || usage
        load_effective
        [ "$sub" = on ] && E=1 || E=0
        write_file "$L" "$E" "$D" "$G" "$W"
        ;;
      timing)
        [ "$#" -eq 5 ] || usage
        load_effective
        write_file "$L" "$E" "$3" "$4" "$5"
        ;;
      *) usage ;;
    esac
    ;;
  clear-temp|default)
    clear_layer temp
    ;;
  clear-persist)
    clear_layer persistent
    ;;
  *)
    usage
    ;;
esac
