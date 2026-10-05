#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

NAME=mibr-carplay111-url
TEMP=/tmp/$NAME
PERSIST=/mnt/app/root/$NAME
NAV=/mnt/app/root/altscreen-u2/scripts/gen2_nav_config.sh

usage(){
  echo "usage: $0 status|VALUE|temp VALUE|persist VALUE|clear-temp|clear-persist|apply"
  echo "VALUE=auto or an exact CarPlay URL such as maps:/car/instrumentcluster/map"
  echo "bare VALUE writes a temporary override"
  exit 2
}
source_name(){
  [ -r "$TEMP" ] && { echo temp; return; }
  [ -r "$PERSIST" ] && { echo persistent; return; }
  echo default
}
effective(){
  [ -r "$TEMP" ] && { cat "$TEMP"; return; }
  [ -r "$PERSIST" ] && { cat "$PERSIST"; return; }
  echo auto
}
valid(){
  [ "$1" = auto ] && return 0
  case "$1" in *:*) return 0 ;; *) return 1 ;; esac
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
status(){
  echo "=== GEN2 RAW URL ==="
  echo "default=auto"
  echo "effective=$(effective)"
  echo "source=$(source_name)"
  echo "temporary_path=$TEMP"
  echo "persistent_path=$PERSIST"
  echo "apply_class=presentation"
  echo "note=when_effective_auto_nav.conf_generates_the_URL"
}
apply(){
  [ -x "$NAV" ] || { echo "GEN2_URL_APPLY=NO_NAV_HELPER"; exit 20; }
  "$NAV" apply
}
case "${1:-status}" in
  status) status ;;
  temp|persist)
    [ "$#" -eq 2 ] || usage
    valid "$2" || usage
    [ "$1" = temp ] && write_temp "$2" || write_persist "$2"
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
  *)
    [ "$#" -eq 1 ] || usage
    valid "$1" || usage
    write_temp "$1"
    status
    ;;
esac
