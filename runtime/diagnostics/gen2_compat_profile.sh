#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

NAME=mibr-carplay111-compat-profile
TEMP=/tmp/$NAME
PERSIST=/mnt/app/root/$NAME

usage(){
  echo "usage: $0 status|mibr|omonob790|temp {mibr|omonob790}|persist {mibr|omonob790}|clear-temp|clear-persist|default"
  echo "changes require a fresh CarPlay negotiation"
  exit 2
}

valid(){
  case "$1" in mibr|omonob790) return 0 ;; *) return 1 ;; esac
}

source_name(){
  [ -r "$TEMP" ] && { echo temp; return; }
  [ -r "$PERSIST" ] && { echo persistent; return; }
  echo default
}

effective(){
  [ -r "$TEMP" ] && { cat "$TEMP"; return; }
  [ -r "$PERSIST" ] && { cat "$PERSIST"; return; }
  echo mibr
}

write_temp(){
  V=$1
  T="$TEMP.new.$$"
  echo "$V" > "$T" || exit 10
  mv "$T" "$TEMP" || { rm -f "$T" 2>/dev/null || true; exit 11; }
}

write_persist(){
  V=$1
  mount -uw /mnt/app 2>/dev/null || exit 12
  T="$PERSIST.new.$$"
  echo "$V" > "$T" || { rm -f "$T" 2>/dev/null || true; mount -ur /mnt/app 2>/dev/null || true; exit 13; }
  mv "$T" "$PERSIST" || { rm -f "$T" 2>/dev/null || true; mount -ur /mnt/app 2>/dev/null || true; exit 14; }
  chmod 644 "$PERSIST" 2>/dev/null || true
  sync
  mount -ur /mnt/app 2>/dev/null || true
}

status(){
  echo "=== GEN2 COMPATIBILITY PROFILE ==="
  echo "effective=$(effective)"
  echo "source=$(source_name)"
  echo "temporary_path=$TEMP"
  [ -r "$TEMP" ] && echo "temporary_value=$(cat "$TEMP")" || echo "temporary_value=none"
  echo "persistent_path=$PERSIST"
  [ -r "$PERSIST" ] && echo "persistent_value=$(cat "$PERSIST")" || echo "persistent_value=none"
  echo "omonob790=features10+primaryInputDevice3+iAPChannel+no_altScreenSuggestUIURLs"
  echo "apply=CarPlay_reconnect_required"
}

case "${1:-status}" in
  status) status ;;
  mibr|omonob790)
    write_temp "$1"
    status
    ;;
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
  *) usage ;;
esac
