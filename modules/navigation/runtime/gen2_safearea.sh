#!/bin/ksh
set -u

ROOT=/mnt/app/root
CONF=$ROOT/mibr-carplay111-safearea.conf
FULL_W=1010
FULL_H=376
RW=0

usage(){
  echo "usage:"
  echo "  gen2_safearea.sh status"
  echo "  gen2_safearea.sh full"
  echo "  gen2_safearea.sh set X Y W H"
  echo "  gen2_safearea.sh bottom PIXELS"
  echo "  gen2_safearea.sh inset LEFT TOP RIGHT BOTTOM"
  echo "  gen2_safearea.sh clear"
  exit 2
}

app_rw(){
  [ "$RW" -eq 1 ] && return 0
  mount -uw /mnt/app 2>/dev/null || {
    echo "GEN2_SAFEAREA=FAIL_MOUNT_APP_RW"
    exit 10
  }
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
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
    *) return 0 ;;
  esac
}

validate_rect(){
  x=$1
  y=$2
  w=$3
  h=$4

  is_uint "$x" || return 1
  is_uint "$y" || return 1
  is_uint "$w" || return 1
  is_uint "$h" || return 1

  [ "$w" -gt 0 ] || return 1
  [ "$h" -gt 0 ] || return 1
  [ "$x" -lt "$FULL_W" ] || return 1
  [ "$y" -lt "$FULL_H" ] || return 1
  [ $((x+w)) -le "$FULL_W" ] || return 1
  [ $((y+h)) -le "$FULL_H" ] || return 1
  return 0
}

write_rect(){
  x=$1
  y=$2
  w=$3
  h=$4
  validate_rect "$x" "$y" "$w" "$h" || {
    echo "GEN2_SAFEAREA=FAIL_RANGE x=$x y=$y w=$w h=$h full=${FULL_W}x${FULL_H}"
    exit 11
  }

  app_rw
  tmp="$CONF.tmp.$$"
  {
    echo "x=$x"
    echo "y=$y"
    echo "w=$w"
    echo "h=$h"
  } > "$tmp" || {
    rm -f "$tmp" 2>/dev/null || true
    echo "GEN2_SAFEAREA=FAIL_WRITE path=$CONF"
    exit 12
  }
  mv "$tmp" "$CONF" || {
    rm -f "$tmp" 2>/dev/null || true
    echo "GEN2_SAFEAREA=FAIL_RENAME path=$CONF"
    exit 13
  }
  app_ro

  echo "GEN2_SAFEAREA=STORED"
  echo "config=$CONF"
  echo "x=$x"
  echo "y=$y"
  echo "w=$w"
  echo "h=$h"
  echo "apply=next_altScreen_info_handshake"
  echo "first_try=reconnect_carplay"
  echo "unit_reboot=not_required_first"
}

show_status(){
  echo "=== GEN2 SAFEAREA ==="
  echo "full_width=$FULL_W"
  echo "full_height=$FULL_H"
  echo "config=$CONF"
  if [ -r "$CONF" ]; then
    echo "configured=1"
    cat "$CONF"
  else
    echo "configured=0"
    echo "x=0"
    echo "y=0"
    echo "w=$FULL_W"
    echo "h=$FULL_H"
  fi
  echo "apply=next_altScreen_info_handshake"
}

cmd=${1:-status}
case "$cmd" in
  status)
    show_status
    ;;
  full)
    write_rect 0 0 "$FULL_W" "$FULL_H"
    ;;
  set)
    [ $# -eq 5 ] || usage
    write_rect "$2" "$3" "$4" "$5"
    ;;
  bottom)
    [ $# -eq 2 ] || usage
    is_uint "$2" || usage
    [ "$2" -lt "$FULL_H" ] || usage
    write_rect 0 0 "$FULL_W" $((FULL_H-$2))
    ;;
  inset)
    [ $# -eq 5 ] || usage
    l=$2
    t=$3
    r=$4
    b=$5
    is_uint "$l" || usage
    is_uint "$t" || usage
    is_uint "$r" || usage
    is_uint "$b" || usage
    w=$((FULL_W-l-r))
    h=$((FULL_H-t-b))
    write_rect "$l" "$t" "$w" "$h"
    ;;
  clear)
    app_rw
    rm -f "$CONF"
    app_ro
    echo "GEN2_SAFEAREA=CLEARED"
    echo "fallback=full_canvas_${FULL_W}x${FULL_H}"
    echo "apply=next_altScreen_info_handshake"
    ;;
  *)
    usage
    ;;
esac
