#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

NAME=mibr-carplay111-ui-urls.conf
TEMP=/tmp/$NAME
PERSIST=/mnt/app/root/$NAME

usage(){
  echo "usage: $0 status|temp URL [URL...]|persist URL [URL...]|clear-temp|clear-persist"
  echo "maximum 8 URLs; changes require a fresh CarPlay negotiation"
  exit 2
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
  echo "=== GEN2 ADVERTISED UI URLS ==="
  echo "source=$(source_name)"
  F=$(source_file)
  if [ -n "$F" ]; then
    cat "$F"
  else
    echo "url0=maps:/car/instrumentcluster"
    echo "url1=maps:/car/instrumentcluster/map"
    echo "url2=maps:/car/instrumentcluster/instructioncard"
  fi
  echo "temporary_path=$TEMP"
  echo "persistent_path=$PERSIST"
  echo "apply_class=reconnect"
}
write_urls(){
  L=$1
  shift
  [ "$#" -ge 1 ] && [ "$#" -le 8 ] || usage
  if [ "$L" = persistent ]; then
    mount -uw /mnt/app 2>/dev/null || exit 12
    TGT=$PERSIST
  else
    TGT=$TEMP
  fi
  T="$TGT.new.$$"
  : > "$T" || exit 13
  I=0
  for U in "$@"; do
    case "$U" in *:*) ;; *) rm -f "$T"; [ "$L" = persistent ] && mount -ur /mnt/app 2>/dev/null || true; usage ;; esac
    echo "url$I=$U" >> "$T" || exit 14
    I=$((I+1))
  done
  mv "$T" "$TGT" || exit 15
  chmod 644 "$TGT" 2>/dev/null || true
  if [ "$L" = persistent ]; then
    sync
    mount -ur /mnt/app 2>/dev/null || true
  fi
}
case "${1:-status}" in
  status) status ;;
  temp|persist)
    L=$1; shift
    write_urls "$L" "$@"
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
