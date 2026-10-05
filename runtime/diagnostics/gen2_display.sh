#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

NAME=mibr-carplay111-display.conf
TEMP=/tmp/$NAME
PERSIST=/mnt/app/root/$NAME
DEF_UUID=b7e6c5a0-2222-4000-8000-000000000002

usage(){
  echo "usage: $0 status|temp W H W_MM H_MM UUID|persist W H W_MM H_MM UUID|clear-temp|clear-persist"
  echo "changes require a fresh CarPlay negotiation"
  exit 2
}
is_uint(){ case "$1" in ''|*[!0-9]*) return 1 ;; *) return 0 ;; esac; }
validate(){
  is_uint "$1" && is_uint "$2" && is_uint "$3" && is_uint "$4" || return 1
  [ "$1" -gt 0 ] && [ "$1" -le 4096 ] || return 1
  [ "$2" -gt 0 ] && [ "$2" -le 2160 ] || return 1
  [ "$3" -gt 0 ] && [ "$3" -le 2000 ] || return 1
  [ "$4" -gt 0 ] && [ "$4" -le 2000 ] || return 1
  [ ${#5} -eq 36 ] || return 1
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
status(){
  echo "=== GEN2 DISPLAY DESCRIPTOR ==="
  echo "source=$(source_name)"
  F=$(source_file)
  if [ -n "$F" ]; then
    cat "$F"
  else
    echo "widthPixels=1010"
    echo "heightPixels=376"
    echo "widthPhysical=200"
    echo "heightPhysical=74"
    echo "uuid=$DEF_UUID"
  fi
  echo "temporary_path=$TEMP"
  echo "persistent_path=$PERSIST"
  echo "apply_class=reconnect"
}
write_config(){
  L=$1; W=$2; H=$3; WM=$4; HM=$5; UUID=$6
  validate "$W" "$H" "$WM" "$HM" "$UUID" || usage
  if [ "$L" = persistent ]; then
    mount -uw /mnt/app 2>/dev/null || exit 12
    TGT=$PERSIST
  else
    TGT=$TEMP
  fi
  T="$TGT.new.$$"
  {
    echo "widthPixels=$W"
    echo "heightPixels=$H"
    echo "widthPhysical=$WM"
    echo "heightPhysical=$HM"
    echo "uuid=$UUID"
  } > "$T" || exit 13
  mv "$T" "$TGT" || exit 14
  chmod 644 "$TGT" 2>/dev/null || true
  if [ "$L" = persistent ]; then sync; mount -ur /mnt/app 2>/dev/null || true; fi
}
case "${1:-status}" in
  status) status ;;
  temp|persist)
    [ "$#" -eq 6 ] || usage
    write_config "$@"
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
  *) usage ;;
esac
