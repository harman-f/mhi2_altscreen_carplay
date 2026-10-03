#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
NAME=mibr-carplay111-enabled
TEMP=/tmp/$NAME
PERSIST=/mnt/app/root/$NAME

usage(){
  echo "usage: $0 status|on|off|temp {on|off}|persist {on|off}|clear-temp|clear-persist"
  echo "bare on/off writes a temporary override; reconnect CarPlay to renegotiate"
  exit 2
}
val(){ case "$1" in on|1) echo 1 ;; off|0) echo 0 ;; *) usage ;; esac; }
source_name(){
  [ -r "$TEMP" ] && { echo temp; return; }
  [ -r "$PERSIST" ] && { echo persistent; return; }
  echo default
}
effective(){
  [ -r "$TEMP" ] && { cat "$TEMP"; return; }
  [ -r "$PERSIST" ] && { cat "$PERSIST"; return; }
  echo 1
}
write_temp(){ echo "$1" > "$TEMP.new.$$" && mv "$TEMP.new.$$" "$TEMP" || exit 10; }
write_persist(){
  mount -uw /mnt/app 2>/dev/null || exit 12
  echo "$1" > "$PERSIST.new.$$" || { mount -ur /mnt/app 2>/dev/null || true; exit 13; }
  mv "$PERSIST.new.$$" "$PERSIST" || { mount -ur /mnt/app 2>/dev/null || true; exit 14; }
  chmod 644 "$PERSIST" 2>/dev/null || true
  sync
  mount -ur /mnt/app 2>/dev/null || true
}
status(){
  echo "=== GEN2 ALTSCREEN MASTER ==="
  echo "default=1"
  echo "effective=$(effective)"
  echo "source=$(source_name)"
  echo "temporary_path=$TEMP"
  echo "persistent_path=$PERSIST"
  echo "apply_class=reconnect"
}
case "${1:-status}" in
  status) status ;;
  on|off) write_temp "$(val "$1")"; status ;;
  temp|persist)
    [ "$#" -eq 2 ] || usage
    V=$(val "$2")
    [ "$1" = temp ] && write_temp "$V" || write_persist "$V"
    status
    ;;
  clear-temp) rm -f "$TEMP" 2>/dev/null || true; status ;;
  clear-persist)
    mount -uw /mnt/app 2>/dev/null || exit 12
    rm -f "$PERSIST" 2>/dev/null || true
    sync
    mount -ur /mnt/app 2>/dev/null || true
    status
    ;;
  *) usage ;;
esac
