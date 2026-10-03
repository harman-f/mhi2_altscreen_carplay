#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init_durable || { echo "FAIL runtime/log bootstrap"; exit 3; }

NAME=mibr-carplay111-viewareas
TEMP=/tmp/$NAME
PERSIST=/mnt/app/root/$NAME
DEFAULT=1

usage(){
  echo "usage: $0 status|on|off|temp {on|off}|persist {on|off}|clear-temp|clear-persist"
  echo "bare on/off writes a temporary override"
  exit 2
}

effective(){
  runtime_cfg_bool "$NAME" "$DEFAULT"
}

status(){
  echo "=== GEN2 VIEWAREAS ==="
  echo "default=$DEFAULT"
  echo "effective=$(effective)"
  echo "source=$(runtime_cfg_source "$NAME")"
  echo "temporary_path=$TEMP"
  [ -r "$TEMP" ] && echo "temporary_value=$(cat "$TEMP" 2>/dev/null)" || echo "temporary_value=none"
  echo "persistent_path=$PERSIST"
  [ -r "$PERSIST" ] && echo "persistent_value=$(cat "$PERSIST" 2>/dev/null)" || echo "persistent_value=none"
  echo "apply=next_altScreen_info_handshake"
}

write_temp(){
  echo "$1" > "$TEMP.new.$$" || exit 10
  mv "$TEMP.new.$$" "$TEMP" || exit 11
}

write_persist(){
  mount -uw /mnt/app 2>/dev/null || exit 12
  echo "$1" > "$PERSIST.new.$$" || { mount -ur /mnt/app 2>/dev/null || true; exit 13; }
  mv "$PERSIST.new.$$" "$PERSIST" || { mount -ur /mnt/app 2>/dev/null || true; exit 14; }
  chmod 644 "$PERSIST" 2>/dev/null || true
  sync
  mount -ur /mnt/app 2>/dev/null || true
}

val(){
  case "$1" in on|1) echo 1 ;; off|0) echo 0 ;; *) usage ;; esac
}

case "${1:-status}" in
  status) status ;;
  on|off)
    write_temp "$(val "$1")"
    status
    ;;
  temp|persist)
    [ "$#" -eq 2 ] || usage
    v=$(val "$2")
    [ "$1" = temp ] && write_temp "$v" || write_persist "$v"
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
