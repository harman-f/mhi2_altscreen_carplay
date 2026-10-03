#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

TMPROOT=/tmp
ROOT=/mnt/app/root
PREFIX=mibr-carplay111-nav
QUERY_NAME=$PREFIX-query
SURFACE_NAME=$PREFIX.surface
ETA_NAME=$PREFIX.showETA
SPEED_NAME=$PREFIX.showSpeedLimit
COMPASS_NAME=$PREFIX.showCompass
MANEUVER_NAME=$PREFIX.maneuverLayout
REACQUIRE=/tmp/mibr-alt111-gen2-reacquire
STATUS=/tmp/mibr-alt111-gen2.status
RW=0

usage(){
  cat <<'EOF'
usage:
  gen2_nav_config.sh status
  gen2_nav_config.sh temp FIELD VALUE
  gen2_nav_config.sh persist FIELD VALUE
  gen2_nav_config.sh temp-profile PROFILE
  gen2_nav_config.sh persist-profile PROFILE
  gen2_nav_config.sh use-temp PROFILE
  gen2_nav_config.sh use-persist PROFILE
  gen2_nav_config.sh clear-temp|clear-persist
  gen2_nav_config.sh apply

Compatibility aliases:
  enable|disable, surface/eta/speed/compass/maneuver, profile, use -> persistent
  live FIELD VALUE -> temporary + apply

FIELD:
  query {0|1}
  surface {base|map|instructioncard}
  eta|speed|compass {yes|no|user}
  maneuver {none|left|right|top}

PROFILE:
  stock|base-rich|base-right|base-left|base-top|map-rich|map-clean|maneuver-only
EOF
  exit 2
}

app_rw(){
  [ "$RW" -eq 1 ] && return 0
  mount -uw /mnt/app 2>/dev/null || { echo "GEN2_NAV=FAIL_MOUNT_APP_RW"; exit 10; }
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

path_for(){
  layer=$1; name=$2
  [ "$layer" = temp ] && echo "$TMPROOT/$name" || echo "$ROOT/$name"
}

effective_path(){
  name=$1
  [ -r "$TMPROOT/$name" ] && { echo "$TMPROOT/$name"; return; }
  [ -r "$ROOT/$name" ] && { echo "$ROOT/$name"; return; }
  echo ""
}

source_for(){
  name=$1
  [ -r "$TMPROOT/$name" ] && { echo temp; return; }
  [ -r "$ROOT/$name" ] && { echo persistent; return; }
  echo default
}

read_file(){
  p=$1; d=$2
  if [ -n "$p" ] && [ -r "$p" ]; then
    v=$(awk 'NR==1 { sub(/[[:space:]]+$/, ""); print; exit }' "$p" 2>/dev/null)
    [ -n "$v" ] && { echo "$v"; return; }
  fi
  echo "$d"
}

read_setting(){
  name=$1; d=$2
  read_file "$(effective_path "$name")" "$d"
}

canonical(){
  field=$1; value=$2
  case "$field" in
    query)
      case "$value" in 0|1) echo "$value" ;; on|yes|true) echo 1 ;; off|no|false) echo 0 ;; *) return 1 ;; esac ;;
    surface)
      case "$value" in base|map|instructioncard) echo "$value" ;; *) return 1 ;; esac ;;
    eta|speed|compass)
      case "$value" in yes|no|user) echo "$value" ;; *) return 1 ;; esac ;;
    maneuver)
      case "$value" in
        none) echo none ;;
        left|leftAligned) echo left ;;
        right|rightAligned) echo right ;;
        top|topAligned) echo top ;;
        *) return 1 ;;
      esac ;;
    *) return 1 ;;
  esac
}

name_for(){
  case "$1" in
    query) echo "$QUERY_NAME" ;;
    surface) echo "$SURFACE_NAME" ;;
    eta) echo "$ETA_NAME" ;;
    speed) echo "$SPEED_NAME" ;;
    compass) echo "$COMPASS_NAME" ;;
    maneuver) echo "$MANEUVER_NAME" ;;
    *) return 1 ;;
  esac
}

write_setting(){
  layer=$1; field=$2; raw=$3
  name=$(name_for "$field") || usage
  value=$(canonical "$field" "$raw") || usage
  target=$(path_for "$layer" "$name")
  [ "$layer" = persistent ] && app_rw
  t="$target.tmp.$$"
  echo "$value" > "$t" || { rm -f "$t" 2>/dev/null || true; echo "GEN2_NAV=FAIL_WRITE path=$target"; exit 11; }
  mv "$t" "$target" || { rm -f "$t" 2>/dev/null || true; echo "GEN2_NAV=FAIL_RENAME path=$target"; exit 12; }
  chmod 644 "$target" 2>/dev/null || true
  [ "$layer" = persistent ] && app_ro
}

maneuver_wire(){
  case "$1" in
    left|leftAligned) echo leftAligned ;;
    right|rightAligned) echo rightAligned ;;
    top|topAligned) echo topAligned ;;
    *) echo "" ;;
  esac
}

effective_surface(){ read_setting "$SURFACE_NAME" base; }

base_url(){
  case "$1" in
    map) echo "maps:/car/instrumentcluster/map" ;;
    instructioncard) echo "maps:/car/instrumentcluster/instructioncard" ;;
    *) echo "maps:/car/instrumentcluster" ;;
  esac
}

effective_url(){
  s=$(effective_surface)
  b=$(base_url "$s")
  q=$(read_setting "$QUERY_NAME" 0)
  if [ "$q" != 1 ] || [ "$s" = instructioncard ]; then
    echo "$b"; return
  fi
  speed=$(read_setting "$SPEED_NAME" user)
  compass=$(read_setting "$COMPASS_NAME" user)
  eta=$(read_setting "$ETA_NAME" yes)
  maneuver=$(maneuver_wire "$(read_setting "$MANEUVER_NAME" none)")
  echo "$b?showSpeedLimit=$speed&showCompass=$compass&showETA=$eta&maneuverLayout=$maneuver"
}

show_one(){
  label=$1; name=$2; def=$3
  echo "$label=$(read_setting "$name" "$def") source=$(source_for "$name")"
}

show_status(){
  echo "=== GEN2 NAV CONFIG ==="
  show_one query "$QUERY_NAME" 0
  show_one surface "$SURFACE_NAME" base
  show_one showETA "$ETA_NAME" yes
  show_one showSpeedLimit "$SPEED_NAME" user
  show_one showCompass "$COMPASS_NAME" user
  show_one maneuverLayout "$MANEUVER_NAME" none
  echo "effective_url=$(effective_url)"
  echo "temporary_root=$TMPROOT"
  echo "persistent_root=$ROOT"
  if [ -r "$STATUS" ]; then
    grep -E '^(control_session|command_ready|nav_query_enabled|nav_url)=' "$STATUS" 2>/dev/null || true
  fi
}

set_profile(){
  layer=$1; p=$2
  case "$p" in
    stock)
      q=0; surface=base; eta=yes; speed=user; compass=user; maneuver=none ;;
    base-rich)
      q=1; surface=base; eta=yes; speed=user; compass=user; maneuver=none ;;
    base-right)
      q=1; surface=base; eta=yes; speed=user; compass=user; maneuver=right ;;
    base-left)
      q=1; surface=base; eta=yes; speed=user; compass=user; maneuver=left ;;
    base-top)
      q=1; surface=base; eta=yes; speed=user; compass=user; maneuver=top ;;
    map-rich)
      q=1; surface=map; eta=yes; speed=user; compass=user; maneuver=none ;;
    map-clean)
      q=1; surface=map; eta=no; speed=no; compass=no; maneuver=none ;;
    maneuver-only)
      q=1; surface=instructioncard; eta=yes; speed=user; compass=user; maneuver=none ;;
    *) usage ;;
  esac
  [ "$layer" = persistent ] && app_rw
  for spec in "query:$q" "surface:$surface" "eta:$eta" "speed:$speed" "compass:$compass" "maneuver:$maneuver"; do
    field=${spec%%:*}; value=${spec#*:}
    name=$(name_for "$field")
    target=$(path_for "$layer" "$name")
    t="$target.tmp.$$"
    echo "$value" > "$t" || { rm -f "$t" 2>/dev/null || true; echo "GEN2_NAV=FAIL_PROFILE_WRITE"; exit 13; }
    mv "$t" "$target" || { rm -f "$t" 2>/dev/null || true; echo "GEN2_NAV=FAIL_PROFILE_RENAME"; exit 14; }
    chmod 644 "$target" 2>/dev/null || true
  done
  [ "$layer" = persistent ] && app_ro
  echo "GEN2_NAV_PROFILE=SET layer=$layer profile=$p"
}

clear_layer(){
  layer=$1
  [ "$layer" = persistent ] && app_rw
  for name in "$QUERY_NAME" "$SURFACE_NAME" "$ETA_NAME" "$SPEED_NAME" "$COMPASS_NAME" "$MANEUVER_NAME"; do
    rm -f "$(path_for "$layer" "$name")" 2>/dev/null || true
  done
  [ "$layer" = persistent ] && app_ro
  echo "GEN2_NAV=CLEAR layer=$layer"
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


cmd=${1:-status}
case "$cmd" in
  status) show_status ;;
  temp|persist)
    [ "$#" -eq 3 ] || usage
    write_setting "$cmd" "$2" "$3"
    show_status
    ;;
  temp-profile|persist-profile)
    [ "$#" -eq 2 ] || usage
    [ "$cmd" = temp-profile ] && layer=temp || layer=persistent
    set_profile "$layer" "$2"
    show_status
    ;;
  use-temp|use-persist)
    [ "$#" -eq 2 ] || usage
    [ "$cmd" = use-temp ] && layer=temp || layer=persistent
    set_profile "$layer" "$2"
    show_status
    apply_live
    ;;
  clear-temp) clear_layer temp; show_status ;;
  clear-persist) clear_layer persistent; show_status ;;
  apply) apply_live ;;
  live)
    [ "$#" -eq 3 ] || usage
    write_setting temp "$2" "$3"
    show_status
    apply_live
    ;;
  enable|disable)
    [ "$cmd" = enable ] && v=1 || v=0
    write_setting persistent query "$v"
    show_status
    ;;
  surface|eta|speed|compass|maneuver)
    [ "$#" -eq 2 ] || usage
    write_setting persistent "$cmd" "$2"
    show_status
    ;;
  profile)
    [ "$#" -eq 2 ] || usage
    set_profile persistent "$2"
    show_status
    ;;
  use)
    [ "$#" -eq 2 ] || usage
    set_profile persistent "$2"
    show_status
    apply_live
    ;;
  paths)
    for name in "$QUERY_NAME" "$SURFACE_NAME" "$ETA_NAME" "$SPEED_NAME" "$COMPASS_NAME" "$MANEUVER_NAME"; do
      echo "temporary=$TMPROOT/$name persistent=$ROOT/$name"
    done
    ;;
  *) usage ;;
esac
