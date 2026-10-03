#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

NAME=mibr-carplay111-sourceversion
TEMP=/tmp/$NAME
PERSIST=/mnt/app/root/$NAME
DEFAULT=1005.8.1

usage(){
  echo "usage: $0 status|VALUE|temp VALUE|persist VALUE|clear-temp|clear-persist|default"
  echo "VALUE = stock or a dotted numeric AirPlay sourceVersion"
  echo "bare VALUE writes a temporary override"
  exit 2
}

valid(){
  [ "$1" = stock ] && return 0
  echo "$1" | awk '
    BEGIN { ok=0 }
    /^[0-9]+\.[0-9]+(\.[0-9]+)?(\.[0-9]+)?$/ { ok=1 }
    END { exit ok ? 0 : 1 }
  '
}

source_name(){
  [ -r "$TEMP" ] && { echo temp; return; }
  [ -r "$PERSIST" ] && { echo persistent; return; }
  echo default
}

effective(){
  [ -r "$TEMP" ] && { cat "$TEMP"; return; }
  [ -r "$PERSIST" ] && { cat "$PERSIST"; return; }
  echo "$DEFAULT"
}

write_temp(){
  V=$1
  echo "$V" > "$TEMP.new.$$" || exit 10
  mv "$TEMP.new.$$" "$TEMP" || exit 11
}

write_persist(){
  V=$1
  mount -uw /mnt/app 2>/dev/null || exit 12
  echo "$V" > "$PERSIST.new.$$" || { mount -ur /mnt/app 2>/dev/null || true; exit 13; }
  mv "$PERSIST.new.$$" "$PERSIST" || { mount -ur /mnt/app 2>/dev/null || true; exit 14; }
  chmod 644 "$PERSIST" 2>/dev/null || true
  sync
  mount -ur /mnt/app 2>/dev/null || true
}

status(){
  echo "=== GEN2 SOURCEVERSION ==="
  echo "default=$DEFAULT"
  echo "effective=$(effective)"
  echo "source=$(source_name)"
  echo "temporary_path=$TEMP"
  [ -r "$TEMP" ] && echo "temporary_value=$(cat "$TEMP")" || echo "temporary_value=none"
  echo "persistent_path=$PERSIST"
  [ -r "$PERSIST" ] && echo "persistent_value=$(cat "$PERSIST")" || echo "persistent_value=none"
  echo "apply=CarPlay_reconnect_required"
}

case "${1:-status}" in
  status) status ;;
  temp|persist)
    [ "$#" -eq 2 ] || usage
    valid "$2" || usage
    [ "$1" = temp ] && write_temp "$2" || write_persist "$2"
    status
    ;;
  clear-temp|default)
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
  *)
    [ "$#" -eq 1 ] || usage
    valid "$1" || usage
    write_temp "$1"
    status
    ;;
esac
