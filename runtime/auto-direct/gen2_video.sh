#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init || { echo "GEN2_VIDEO=FAIL_RUNTIME"; exit 3; }

NAME=$VIDEO_CONFIG_NAME
TEMP=$MIBR_CFG_TEMP_ROOT/$NAME
PERSIST=$MIBR_CFG_PERSIST_ROOT/$NAME
BRIDGEPID=/tmp/mibr-direct-auto-bridge.pid

usage(){
  echo "usage: $0 status|temp PACE BUFFER|persist PACE BUFFER|clear-temp|clear-persist|apply"
  echo "PACE=0|1 BUFFER=1..6"
  exit 2
}
valid(){
  case "$1" in 0|1) ;; *) return 1 ;; esac
  case "$2" in 1|2|3|4|5|6) ;; *) return 1 ;; esac
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
  F=$1; K=$2; D=$3
  if [ -n "$F" ]; then
    V=$(awk -F= -v k="$K" '$1==k {print substr($0,index($0,"=")+1); exit}' "$F" 2>/dev/null)
    [ -n "$V" ] && { echo "$V"; return; }
  fi
  echo "$D"
}
status(){
  F=$(source_file)
  echo "=== GEN2 VIDEO PACING ==="
  echo "source=$(source_name)"
  echo "pace=$(field "$F" pace 1)"
  echo "pace_buffer=$(field "$F" pace_buffer 3)"
  echo "temporary_path=$TEMP"
  echo "persistent_path=$PERSIST"
  echo "apply_class=bridge"
}
write_cfg(){
  L=$1; P=$2; B=$3
  valid "$P" "$B" || usage
  [ "$L" = persistent ] && { mount -uw /mnt/app 2>/dev/null || exit 12; TGT=$PERSIST; } || TGT=$TEMP
  T="$TGT.new.$$"
  { echo "pace=$P"; echo "pace_buffer=$B"; } > "$T" || exit 13
  mv "$T" "$TGT" || exit 14
  chmod 644 "$TGT" 2>/dev/null || true
  [ "$L" = persistent ] && { sync; mount -ur /mnt/app 2>/dev/null || true; }
}
apply(){
  P=
  [ -r "$BRIDGEPID" ] && P=$(cat "$BRIDGEPID" 2>/dev/null)
  if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then
    kill "$P" 2>/dev/null || true
    echo "GEN2_VIDEO_APPLY=BRIDGE_RESTART_REQUESTED"
  else
    echo "GEN2_VIDEO_APPLY=NO_ACTIVE_BRIDGE"
  fi
}
case "${1:-status}" in
  status) status ;;
  temp|persist)
    [ "$#" -eq 3 ] || usage
    write_cfg "$@"
    status
    ;;
  clear-temp)
    rm -f "$TEMP" 2>/dev/null || true
    status
    ;;
  clear-persist)
    mount -uw /mnt/app 2>/dev/null || exit 12
    rm -f "$PERSIST" 2>/dev/null || true
    sync
    mount -ur /mnt/app 2>/dev/null || true
    status
    ;;
  apply) apply ;;
  *) usage ;;
esac
