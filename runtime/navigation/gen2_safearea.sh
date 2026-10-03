#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
# Compatibility wrapper for the former single SafeArea helper.
# It modifies ViewArea 0 only; use gen2_viewareas.sh for both areas.
set -u
H=/mnt/app/root/altscreen-u2/scripts/gen2_viewareas.sh
[ -x "$H" ] || { echo "GEN2_SAFEAREA=FAIL_HELPER"; exit 3; }
FULL_W=1010
FULL_H=376

usage(){
  echo "usage: $0 status|full|set X Y W H|bottom PIXELS|inset L T R B"
  echo "       $0 temp {full|set X Y W H|bottom PIXELS|inset L T R B}"
  echo "       $0 persist {full|set X Y W H|bottom PIXELS|inset L T R B}"
  echo "       $0 clear-temp|clear-persist"
  echo "compatibility_scope=view0.safe; canonical_helper=gen2_viewareas.sh"
  exit 2
}
is_uint(){ case "$1" in ''|*[!0-9]*) return 1 ;; *) return 0 ;; esac; }

set_rect(){
  L=$1; X=$2; Y=$3; W=$4; H=$5
  for V in "$X" "$Y" "$W" "$H"; do is_uint "$V" || usage; done
  [ "$W" -gt 0 ] && [ "$H" -gt 0 ] || usage
  [ $((X+W)) -le "$FULL_W" ] && [ $((Y+H)) -le "$FULL_H" ] || usage
  [ "$L" = temp ] && C=temp-set || C=persist-set
  "$H" "$C" view0.safe.x "$X" >/dev/null || exit $?
  "$H" "$C" view0.safe.y "$Y" >/dev/null || exit $?
  "$H" "$C" view0.safe.w "$W" >/dev/null || exit $?
  "$H" "$C" view0.safe.h "$H" >/dev/null || exit $?
  "$H" status
}

run(){
  L=$1; shift
  C=$1; shift
  case "$C" in
    full) [ "$#" -eq 0 ] || usage; set_rect "$L" 0 0 "$FULL_W" "$FULL_H" ;;
    set) [ "$#" -eq 4 ] || usage; set_rect "$L" "$1" "$2" "$3" "$4" ;;
    bottom)
      [ "$#" -eq 1 ] || usage; is_uint "$1" || usage
      [ "$1" -lt "$FULL_H" ] || usage
      set_rect "$L" 0 0 "$FULL_W" $((FULL_H-$1))
      ;;
    inset)
      [ "$#" -eq 4 ] || usage
      for V in "$1" "$2" "$3" "$4"; do is_uint "$V" || usage; done
      set_rect "$L" "$1" "$2" $((FULL_W-$1-$3)) $((FULL_H-$2-$4))
      ;;
    *) usage ;;
  esac
}

case "${1:-status}" in
  status) exec "$H" status ;;
  temp|persist)
    L=$1; shift; [ "$#" -ge 1 ] || usage; run "$L" "$@" ;;
  full|set|bottom|inset)
    run temp "$@" ;;
  clear-temp) exec "$H" clear-temp ;;
  clear-persist) exec "$H" clear-persist ;;
  *) usage ;;
esac
