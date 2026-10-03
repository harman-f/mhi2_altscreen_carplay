#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

NAME=mibr-carplay111-safearea.conf
TEMP=/tmp/$NAME
PERSIST=/mnt/app/root/$NAME
FULL_W=1010
FULL_H=376
RW=0

usage(){
  echo "usage:"
  echo "  gen2_safearea.sh status"
  echo "  gen2_safearea.sh full|set X Y W H|bottom PIXELS|inset L T R B     # temporary"
  echo "  gen2_safearea.sh temp {full|set X Y W H|bottom PIXELS|inset L T R B}"
  echo "  gen2_safearea.sh persist {full|set X Y W H|bottom PIXELS|inset L T R B}"
  echo "  gen2_safearea.sh clear-temp|clear-persist|clear"
  exit 2
}

app_rw(){
  [ "$RW" -eq 1 ] && return 0
  mount -uw /mnt/app 2>/dev/null || { echo "GEN2_SAFEAREA=FAIL_MOUNT_APP_RW"; exit 10; }
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

is_uint(){
  case "$1" in ''|*[!0-9]*) return 1 ;; *) return 0 ;; esac
}

validate_rect(){
  x=$1; y=$2; w=$3; h=$4
  is_uint "$x" && is_uint "$y" && is_uint "$w" && is_uint "$h" || return 1
  [ "$w" -gt 0 ] && [ "$h" -gt 0 ] || return 1
  [ "$x" -lt "$FULL_W" ] && [ "$y" -lt "$FULL_H" ] || return 1
  [ $((x+w)) -le "$FULL_W" ] && [ $((y+h)) -le "$FULL_H" ]
}

source_name(){
  [ -r "$TEMP" ] && { echo temp; return; }
  [ -r "$PERSIST" ] && { echo persistent; return; }
  echo default
}

effective_file(){
  [ -r "$TEMP" ] && { echo "$TEMP"; return; }
  [ -r "$PERSIST" ] && { echo "$PERSIST"; return; }
  echo ""
}

write_rect(){
  layer=$1; x=$2; y=$3; w=$4; h=$5
  validate_rect "$x" "$y" "$w" "$h" || {
    echo "GEN2_SAFEAREA=FAIL_RANGE x=$x y=$y w=$w h=$h full=$FULL_W x $FULL_H"
    exit 11
  }
  [ "$layer" = persistent ] && { app_rw; target=$PERSIST; } || target=$TEMP
  tmp="$target.tmp.$$"
  {
    echo "x=$x"; echo "y=$y"; echo "w=$w"; echo "h=$h"
  } > "$tmp" || { rm -f "$tmp" 2>/dev/null || true; echo "GEN2_SAFEAREA=FAIL_WRITE"; exit 12; }
  mv "$tmp" "$target" || { rm -f "$tmp" 2>/dev/null || true; echo "GEN2_SAFEAREA=FAIL_RENAME"; exit 13; }
  chmod 644 "$target" 2>/dev/null || true
  [ "$layer" = persistent ] && app_ro
  echo "GEN2_SAFEAREA=STORED layer=$layer x=$x y=$y w=$w h=$h"
  echo "apply=next_altScreen_info_handshake"
  echo "first_try=reconnect_carplay"
}

run_rect(){
  layer=$1
  shift
  sub=$1
  shift
  case "$sub" in
    full) [ "$#" -eq 0 ] || usage; write_rect "$layer" 0 0 "$FULL_W" "$FULL_H" ;;
    set) [ "$#" -eq 4 ] || usage; write_rect "$layer" "$1" "$2" "$3" "$4" ;;
    bottom)
      [ "$#" -eq 1 ] || usage; is_uint "$1" || usage; [ "$1" -lt "$FULL_H" ] || usage
      write_rect "$layer" 0 0 "$FULL_W" $((FULL_H-$1))
      ;;
    inset)
      [ "$#" -eq 4 ] || usage
      l=$1; t=$2; r=$3; b=$4
      is_uint "$l" && is_uint "$t" && is_uint "$r" && is_uint "$b" || usage
      write_rect "$layer" "$l" "$t" $((FULL_W-l-r)) $((FULL_H-t-b))
      ;;
    *) usage ;;
  esac
}

show_status(){
  echo "=== GEN2 SAFEAREA ==="
  echo "default=x=0,y=0,w=$FULL_W,h=$FULL_H"
  echo "effective_source=$(source_name)"
  echo "temporary_path=$TEMP"
  [ -r "$TEMP" ] && { echo "temporary_config=present"; cat "$TEMP"; } || echo "temporary_config=none"
  echo "persistent_path=$PERSIST"
  [ -r "$PERSIST" ] && { echo "persistent_config=present"; cat "$PERSIST"; } || echo "persistent_config=none"
  F=$(effective_file)
  if [ -n "$F" ]; then
    echo "effective_config:"
    cat "$F"
  else
    echo "effective_config:"
    echo "x=0"; echo "y=0"; echo "w=$FULL_W"; echo "h=$FULL_H"
  fi
  echo "apply=next_altScreen_info_handshake"
}

case "${1:-status}" in
  status) show_status ;;
  temp|persist)
    layer=$1
    shift
    [ "$#" -ge 1 ] || usage
    run_rect "$layer" "$@"
    ;;
  full|set|bottom|inset)
    run_rect temp "$@"
    ;;
  clear|clear-temp)
    rm -f "$TEMP" 2>/dev/null || true
    echo "GEN2_SAFEAREA=CLEARED layer=temp effective_source=$(source_name)"
    ;;
  clear-persist)
    app_rw
    rm -f "$PERSIST" 2>/dev/null || true
    app_ro
    echo "GEN2_SAFEAREA=CLEARED layer=persistent effective_source=$(source_name)"
    ;;
  *) usage ;;
esac
