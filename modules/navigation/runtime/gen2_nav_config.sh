#!/bin/ksh
set -u

ROOT=/mnt/app/root
QUERY=$ROOT/mibr-carplay111-nav-query.enabled
SURFACE=$ROOT/mibr-carplay111-nav.surface
ETA=$ROOT/mibr-carplay111-nav.showETA
SPEED=$ROOT/mibr-carplay111-nav.showSpeedLimit
COMPASS=$ROOT/mibr-carplay111-nav.showCompass
MANEUVER=$ROOT/mibr-carplay111-nav.maneuverLayout
LEGACY_MAP=$ROOT/mibr-carplay111-url-map.enabled
VOLATILE_SURFACE=/tmp/mibr-alt111-url-mode
REACQUIRE=/tmp/mibr-alt111-gen2-reacquire
STATUS=/tmp/mibr-alt111-gen2.status

RW=0

usage(){
  cat <<'EOF'
usage:
  gen2_nav_config.sh status
  gen2_nav_config.sh enable|disable
  gen2_nav_config.sh surface {base|map|instructioncard}
  gen2_nav_config.sh eta {yes|no|user}
  gen2_nav_config.sh speed {yes|no|user}
  gen2_nav_config.sh compass {yes|no|user}
  gen2_nav_config.sh maneuver {none|left|right|top}
  gen2_nav_config.sh profile {stock|base-rich|base-right|base-left|base-top|map-rich|map-clean|maneuver-only}
  gen2_nav_config.sh use {stock|base-rich|base-right|base-left|base-top|map-rich|map-clean|maneuver-only}
  gen2_nav_config.sh live {surface|eta|speed|compass|maneuver} VALUE
  gen2_nav_config.sh apply
  gen2_nav_config.sh paths

Changes are persistent under /mnt/app/root. They do not rebuild Stream111.
'apply' requests the existing serialized GEN2 same-stream reacquire sequence
(STOP -> SHOW with the new URL -> forceKeyFrame). 'use PROFILE' stores a profile
and immediately performs that live apply, including the fresh keyframe request.
Do not use apply/use during an isolated D1/D2 recovery experiment unless that
transition is the test itself.
EOF
  exit 2
}

app_rw(){
  [ "$RW" -eq 1 ] && return 0
  mount -uw /mnt/app 2>/dev/null || {
    echo "GEN2_NAV=FAIL_MOUNT_APP_RW"
    exit 10
  }
  RW=1
}

app_ro(){
  if [ "$RW" -eq 1 ]; then
    sync 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    RW=0
  fi
}
trap app_ro 0 1 2 15

write_value(){
  target=$1
  value=$2
  tmp="$target.tmp.$$"
  echo "$value" > "$tmp" || {
    rm -f "$tmp" 2>/dev/null || true
    echo "GEN2_NAV=FAIL_WRITE path=$target"
    exit 11
  }
  mv "$tmp" "$target" || {
    rm -f "$tmp" 2>/dev/null || true
    echo "GEN2_NAV=FAIL_RENAME path=$target"
    exit 12
  }
}

read_value(){
  path=$1
  def=$2
  if [ -r "$path" ]; then
    v=$(awk 'NR==1 { sub(/[[:space:]]+$/, ""); print; exit }' "$path" 2>/dev/null)
    [ -n "$v" ] && { echo "$v"; return; }
  fi
  echo "$def"
}

canonical_tristate(){
  case "$1" in
    yes|no|user) echo "$1" ;;
    *) return 1 ;;
  esac
}

canonical_maneuver(){
  case "$1" in
    none) echo "none" ;;
    left|leftAligned) echo "left" ;;
    right|rightAligned) echo "right" ;;
    top|topAligned) echo "top" ;;
    *) return 1 ;;
  esac
}

effective_surface(){
  if [ -r "$VOLATILE_SURFACE" ]; then
    v=$(read_value "$VOLATILE_SURFACE" "")
    case "$v" in base|map|instructioncard) echo "$v"; return ;; esac
  fi
  if [ -r "$SURFACE" ]; then
    v=$(read_value "$SURFACE" "")
    case "$v" in base|map|instructioncard) echo "$v"; return ;; esac
  fi
  [ -e "$LEGACY_MAP" ] && echo map || echo base
}

base_url(){
  case "$1" in
    map) echo "maps:/car/instrumentcluster/map" ;;
    instructioncard) echo "maps:/car/instrumentcluster/instructioncard" ;;
    *) echo "maps:/car/instrumentcluster" ;;
  esac
}

maneuver_wire(){
  case "$1" in
    left|leftAligned) echo "leftAligned" ;;
    right|rightAligned) echo "rightAligned" ;;
    top|topAligned) echo "topAligned" ;;
    *) echo "" ;;
  esac
}

effective_url(){
  s=$(effective_surface)
  b=$(base_url "$s")
  if [ ! -e "$QUERY" ] || [ "$s" = "instructioncard" ]; then
    echo "$b"
    return
  fi
  speed=$(read_value "$SPEED" user)
  compass=$(read_value "$COMPASS" user)
  eta=$(read_value "$ETA" yes)
  maneuver=$(maneuver_wire "$(read_value "$MANEUVER" none)")
  echo "$b?showSpeedLimit=$speed&showCompass=$compass&showETA=$eta&maneuverLayout=$maneuver"
}

show_status(){
  s=$(effective_surface)
  [ -e "$QUERY" ] && q=enabled || q=disabled
  echo "=== GEN2 NAV CONFIG ==="
  echo "query=$q"
  echo "surface=$s"
  if [ -r "$VOLATILE_SURFACE" ]; then
    echo "volatile_surface_override=$(read_value "$VOLATILE_SURFACE" invalid)"
  else
    echo "volatile_surface_override=none"
  fi
  echo "showETA=$(read_value "$ETA" yes)"
  echo "showSpeedLimit=$(read_value "$SPEED" user)"
  echo "showCompass=$(read_value "$COMPASS" user)"
  echo "maneuverLayout=$(maneuver_wire "$(read_value "$MANEUVER" none)")"
  echo "effective_url=$(effective_url)"
  if [ "$s" = "instructioncard" ] && [ -e "$QUERY" ]; then
    echo "note=instructioncard_is_forced_bare"
  fi
  if [ -r "$STATUS" ]; then
    grep -E '^(control_session|command_ready|nav_query_enabled|nav_url)=' "$STATUS" 2>/dev/null || true
  fi
}

clear_surface_overrides(){
  rm -f "$VOLATILE_SURFACE" 2>/dev/null || true
  rm -f "$LEGACY_MAP" 2>/dev/null || true
}

set_surface(){
  case "$1" in base|map|instructioncard) ;; *) usage ;; esac
  app_rw
  write_value "$SURFACE" "$1"
  clear_surface_overrides
  app_ro
}

set_tristate(){
  path=$1
  val=$(canonical_tristate "$2") || usage
  app_rw
  write_value "$path" "$val"
  app_ro
}

set_maneuver(){
  val=$(canonical_maneuver "$1") || usage
  app_rw
  write_value "$MANEUVER" "$val"
  app_ro
}

set_profile(){
  p=$1
  app_rw
  clear_surface_overrides
  case "$p" in
    stock)
      write_value "$SURFACE" base
      write_value "$ETA" yes
      write_value "$SPEED" user
      write_value "$COMPASS" user
      write_value "$MANEUVER" none
      rm -f "$QUERY"
      ;;
    base-rich)
      write_value "$SURFACE" base
      write_value "$ETA" yes
      write_value "$SPEED" user
      write_value "$COMPASS" user
      write_value "$MANEUVER" none
      : > "$QUERY"
      ;;
    base-right)
      write_value "$SURFACE" base
      write_value "$ETA" yes
      write_value "$SPEED" user
      write_value "$COMPASS" user
      write_value "$MANEUVER" right
      : > "$QUERY"
      ;;
    base-left)
      write_value "$SURFACE" base
      write_value "$ETA" yes
      write_value "$SPEED" user
      write_value "$COMPASS" user
      write_value "$MANEUVER" left
      : > "$QUERY"
      ;;
    base-top)
      write_value "$SURFACE" base
      write_value "$ETA" yes
      write_value "$SPEED" user
      write_value "$COMPASS" user
      write_value "$MANEUVER" top
      : > "$QUERY"
      ;;
    map-rich)
      write_value "$SURFACE" map
      write_value "$ETA" yes
      write_value "$SPEED" user
      write_value "$COMPASS" user
      write_value "$MANEUVER" none
      : > "$QUERY"
      ;;
    map-clean)
      write_value "$SURFACE" map
      write_value "$ETA" no
      write_value "$SPEED" no
      write_value "$COMPASS" no
      write_value "$MANEUVER" none
      : > "$QUERY"
      ;;
    maneuver-only)
      write_value "$SURFACE" instructioncard
      write_value "$MANEUVER" none
      : > "$QUERY"
      ;;
    *)
      app_ro
      usage
      ;;
  esac
  app_ro
}

apply_live(){
  LOG=/tmp/altscreen111.log
  if [ ! -r "$STATUS" ]; then
    echo "GEN2_NAV_APPLY=NO_RUNTIME config_persisted=1"
    return 0
  fi
  ready=$(awk -F= '/^command_ready=/{print $2; exit}' "$STATUS" 2>/dev/null)
  session=$(awk -F= '/^control_session=/{print $2; exit}' "$STATUS" 2>/dev/null)
  if [ "${ready:-0}" != "1" ] || [ -z "${session:-}" ] || [ "$session" = "0" ]; then
    echo "GEN2_NAV_APPLY=NO_ACTIVE_SESSION config_persisted=1 command_ready=${ready:-0} control_session=${session:-0}"
    return 0
  fi

  before_kf=$(grep -c 'gen2 UI completion type=4 .* status=0 core_rc=0' "$LOG" 2>/dev/null || true)
  before_idr=$(awk -F= '/^source_idrs=/{print $2; exit}' "$STATUS" 2>/dev/null)
  before_kf=${before_kf:-0}
  before_idr=${before_idr:-0}

  rm -f "$REACQUIRE" 2>/dev/null || true
  touch "$REACQUIRE" || {
    echo "GEN2_NAV_APPLY=FAIL_TOUCH"
    exit 20
  }
  echo "GEN2_NAV_APPLY=REQUESTED"
  echo "effective_url=$(effective_url)"
  echo "source_idrs_before=$before_idr"

  i=0
  while [ $i -lt 30 ]; do
    [ ! -e "$REACQUIRE" ] && break
    i=$((i+1))
    if command -v usleep >/dev/null 2>&1; then
      usleep 100000
    else
      sleep 1
    fi
  done

  if [ -e "$REACQUIRE" ]; then
    echo "GEN2_NAV_APPLY=NOT_CONSUMED"
    exit 21
  fi
  echo "GEN2_NAV_APPLY=CONSUMED"

  # Reacquire completion of SHOW schedules forceKeyFrame in alt111_control.
  # Wait for the serialized type=4 completion so a live switch cannot be
  # mistaken for "applied" before its keyframe request has actually finished.
  i=0
  while [ $i -lt 60 ]; do
    now_kf=$(grep -c 'gen2 UI completion type=4 .* status=0 core_rc=0' "$LOG" 2>/dev/null || true)
    now_kf=${now_kf:-0}
    [ "$now_kf" -gt "$before_kf" ] && break
    i=$((i+1))
    if command -v usleep >/dev/null 2>&1; then
      usleep 100000
    else
      sleep 1
    fi
  done

  now_kf=$(grep -c 'gen2 UI completion type=4 .* status=0 core_rc=0' "$LOG" 2>/dev/null || true)
  now_kf=${now_kf:-0}
  if [ "$now_kf" -le "$before_kf" ]; then
    echo "GEN2_NAV_APPLY=KEYFRAME_NOT_COMPLETED"
    tail -80 "$LOG" 2>/dev/null || true
    exit 22
  fi

  echo "GEN2_NAV_APPLY=KEYFRAME_COMPLETED"

  # Give the source counter a short bounded window to expose the resulting
  # complete IDR. This does not add another keyframe request.
  i=0
  after_idr=$before_idr
  while [ $i -lt 30 ]; do
    after_idr=$(awk -F= '/^source_idrs=/{print $2; exit}' "$STATUS" 2>/dev/null)
    after_idr=${after_idr:-0}
    [ "$after_idr" -gt "$before_idr" ] && break
    i=$((i+1))
    if command -v usleep >/dev/null 2>&1; then
      usleep 100000
    else
      sleep 1
    fi
  done

  echo "source_idrs_after=$after_idr"
  if [ "$after_idr" -gt "$before_idr" ]; then
    echo "GEN2_NAV_APPLY=FRESH_IDR_OBSERVED"
  else
    echo "GEN2_NAV_APPLY=FRESH_IDR_NOT_OBSERVED"
  fi
}

set_live(){
  control=$1
  value=$2
  case "$control" in
    surface) set_surface "$value" ;;
    eta) set_tristate "$ETA" "$value" ;;
    speed) set_tristate "$SPEED" "$value" ;;
    compass) set_tristate "$COMPASS" "$value" ;;
    maneuver) set_maneuver "$value" ;;
    *) usage ;;
  esac
  show_status
  apply_live
}

show_paths(){
  echo "query_marker=$QUERY"
  echo "surface_file=$SURFACE"
  echo "eta_file=$ETA"
  echo "speed_file=$SPEED"
  echo "compass_file=$COMPASS"
  echo "maneuver_file=$MANEUVER"
  echo "apply_marker=$REACQUIRE"
}

cmd=${1:-status}
case "$cmd" in
  status)
    show_status
    ;;
  enable)
    app_rw
    : > "$QUERY" || { echo "GEN2_NAV=FAIL_ENABLE"; exit 13; }
    app_ro
    show_status
    ;;
  disable)
    app_rw
    rm -f "$QUERY"
    app_ro
    show_status
    ;;
  surface)
    [ $# -eq 2 ] || usage
    set_surface "$2"
    show_status
    ;;
  eta)
    [ $# -eq 2 ] || usage
    set_tristate "$ETA" "$2"
    show_status
    ;;
  speed)
    [ $# -eq 2 ] || usage
    set_tristate "$SPEED" "$2"
    show_status
    ;;
  compass)
    [ $# -eq 2 ] || usage
    set_tristate "$COMPASS" "$2"
    show_status
    ;;
  maneuver)
    [ $# -eq 2 ] || usage
    set_maneuver "$2"
    show_status
    ;;
  profile)
    [ $# -eq 2 ] || usage
    set_profile "$2"
    show_status
    ;;
  use)
    [ $# -eq 2 ] || usage
    set_profile "$2"
    show_status
    apply_live
    ;;
  live)
    [ $# -eq 3 ] || usage
    set_live "$2" "$3"
    ;;
  apply)
    apply_live
    ;;
  paths)
    show_paths
    ;;
  *)
    usage
    ;;
esac
