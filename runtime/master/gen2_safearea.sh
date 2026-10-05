#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
case "$0" in */*) MASTER_SCRIPT_ROOT=${0%/*} ;; *) MASTER_SCRIPT_ROOT=. ;; esac
. "$MASTER_SCRIPT_ROOT/master_settings.sh" || exit 10
C=${1:-status}
case "$C" in
  status) exec "$HELPER" status ;;
  persist|clear-persist) blocked ;;
  clear-temp) clear_key viewareas.enabled; exit $? ;;
  temp) shift; C=${1:-};;
esac
uint(){ case "$1" in ''|*[!0-9]*) usage ;; esac; [ "${#1}" -le 4 ] || usage; }
case "$C" in
  full) [ "$#" -eq 1 ] || usage; X=0; Y=0; W=1010; H=376 ;;
  set) [ "$#" -eq 5 ] || usage; X=$2; Y=$3; W=$4; H=$5 ;;
  bottom) [ "$#" -eq 2 ] || usage; uint "$2"; X=0; Y=0; W=1010; H=$((376-$2)) ;;
  inset)
    [ "$#" -eq 5 ] || usage
    for V in "$2" "$3" "$4" "$5"; do uint "$V"; done
    X=$2; Y=$3; W=$((1010-$2-$4)); H=$((376-$3-$5)) ;;
  *) usage ;;
esac
for V in "$X" "$Y" "$W" "$H"; do uint "$V"; done
batch <<EOF
viewarea.0.safe.x=$X
viewarea.0.safe.y=$Y
viewarea.0.safe.w=$W
viewarea.0.safe.h=$H
EOF
