#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

NAME=mibr-carplay111-nav.conf
TEMP=/tmp/$NAME
PERSIST=/mnt/app/root/$NAME
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
  F=$1; K=$2; D=$3
  if [ -n "$F" ] && [ -r "$F" ]; then
    V=$(awk -F= -v k="$K" '$1==k {print substr($0,index($0,"=")+1); exit}' "$F" 2>/dev/null)
    [ -n "$V" ] && { echo "$V"; return; }
  fi
  echo "$D"
}

load_effective(){
  F=$(source_file)
  Q=$(field "$F" query 0)
  S=$(field "$F" surface base)
  E=$(field "$F" showETA yes)
  P=$(field "$F" showSpeedLimit user)
  C=$(field "$F" showCompass user)
  M=$(field "$F" maneuverLayout none)
}

canonical(){
  case "$1:$2" in
    query:0|query:1) echo "$2" ;;
    query:on|query:yes|query:true) echo 1 ;;
    query:off|query:no|query:false) echo 0 ;;
    surface:base|surface:map|surface:instructioncard) echo "$2" ;;
    eta:yes|eta:no|eta:user|speed:yes|speed:no|speed:user|compass:yes|compass:no|compass:user) echo "$2" ;;
    maneuver:none) echo none ;;
    maneuver:left|maneuver:leftAligned) echo left ;;
    maneuver:right|maneuver:rightAligned) echo right ;;
    maneuver:top|maneuver:topAligned) echo top ;;
    *) return 1 ;;
  esac
}

write_config(){
  L=$1
  [ "$L" = persistent ] && { app_rw; TGT=$PERSIST; } || TGT=$TEMP
  T="$TGT.new.$$"
  {
    echo "query=$Q"
    echo "surface=$S"
    echo "showETA=$E"
    echo "showSpeedLimit=$P"
    echo "showCompass=$C"
    echo "maneuverLayout=$M"
  } > "$T" || { rm -f "$T" 2>/dev/null || true; echo "GEN2_NAV=FAIL_WRITE"; exit 11; }
  mv "$T" "$TGT" || { rm -f "$T" 2>/dev/null || true; echo "GEN2_NAV=FAIL_RENAME"; exit 12; }
  chmod 644 "$TGT" 2>/dev/null || true
  [ "$L" = persistent ] && app_ro
}

set_field(){
  L=$1; K=$2; RAW=$3
  V=$(canonical "$K" "$RAW") || usage
  load_effective
  case "$K" in
    query) Q=$V ;;
    surface) S=$V ;;
    eta) E=$V ;;
    speed) P=$V ;;
    compass) C=$V ;;
    maneuver) M=$V ;;
    *) usage ;;
  esac
  write_config "$L"
}

set_profile(){
  L=$1
  case "$2" in
    stock) Q=0; S=base; E=yes; P=user; C=user; M=none ;;
    base-rich) Q=1; S=base; E=yes; P=user; C=user; M=none ;;
    base-right) Q=1; S=base; E=yes; P=user; C=user; M=right ;;
    base-left) Q=1; S=base; E=yes; P=user; C=user; M=left ;;
    base-top) Q=1; S=base; E=yes; P=user; C=user; M=top ;;
    map-rich) Q=1; S=map; E=yes; P=user; C=user; M=none ;;
    map-clean) Q=1; S=map; E=no; P=no; C=no; M=none ;;
    maneuver-only) Q=1; S=instructioncard; E=yes; P=user; C=user; M=none ;;
    *) usage ;;
  esac
  write_config "$L"
}

wire_maneuver(){
  case "$1" in left) echo leftAligned ;; right) echo rightAligned ;; top) echo topAligned ;; *) echo "" ;; esac
}
base_url(){
  case "$1" in map) echo "maps:/car/instrumentcluster/map" ;; instructioncard) echo "maps:/car/instrumentcluster/instructioncard" ;; *) echo "maps:/car/instrumentcluster" ;; esac
}
effective_url(){
  load_effective
  B=$(base_url "$S")
  [ "$Q" = 1 ] || { echo "$B"; return; }
  [ "$S" = instructioncard ] && { echo "$B"; return; }
  echo "$B?showSpeedLimit=$P&showCompass=$C&showETA=$E&maneuverLayout=$(wire_maneuver "$M")"
}

show_status(){
  load_effective
  echo "=== GEN2 NAV CONFIG ==="
  echo "source=$(source_name)"
  echo "query=$Q"
  echo "surface=$S"
  echo "showETA=$E"
  echo "showSpeedLimit=$P"
  echo "showCompass=$C"
  echo "maneuverLayout=$M"
  echo "generated_url=$(effective_url)"
  echo "temporary_path=$TEMP"
  echo "persistent_path=$PERSIST"
  echo "apply_class=presentation"
  [ -r "$STATUS" ] && grep -E '^(control_session|command_ready|nav_query_enabled|nav_url)=' "$STATUS" 2>/dev/null || true
}

clear_layer(){
  case "$1" in
    temp) rm -f "$TEMP" 2>/dev/null || true ;;
    persistent) app_rw; rm -f "$PERSIST" 2>/dev/null || true; app_ro ;;
  esac
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
    set_field "$cmd" "$2" "$3"
    show_status
    ;;
  temp-profile|persist-profile)
    [ "$#" -eq 2 ] || usage
    [ "$cmd" = temp-profile ] && L=temp || L=persistent
    set_profile "$L" "$2"
    show_status
    ;;
  use-temp|use-persist)
    [ "$#" -eq 2 ] || usage
    [ "$cmd" = use-temp ] && L=temp || L=persistent
    set_profile "$L" "$2"
    show_status
    apply_live
    ;;
  clear-temp) clear_layer temp; show_status ;;
  clear-persist) clear_layer persistent; show_status ;;
  apply) apply_live ;;
  *) usage ;;
esac
