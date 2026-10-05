#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
. "${0%/*}/master_settings.sh" || exit 10
cmd=${1:-status}
case "$cmd" in
  status) exec "$HELPER" status ;;
  persist|persist-profile|use-persist|clear-persist) blocked ;;
  clear-temp) clear_key navigation.query; exit $? ;;
  apply) apply_presentation; exit $? ;;
  temp)
    [ "$#" -eq 3 ] || usage
    case "$2" in
      query|surface) KEY=navigation.$2 ;;
      eta) KEY=navigation.ETA ;;
      speed) KEY=navigation.speedLimit ;;
      compass) KEY=navigation.compass ;;
      maneuver) KEY=navigation.maneuver ;;
      *) usage ;;
    esac
    set_key "$KEY" "$3"; exit $? ;;
  temp-profile|use-temp) [ "$#" -eq 2 ] || usage ;;
  *) usage ;;
esac
Q=1; S=base; E=yes; P=user; C=user; M=none
case "$2" in
  stock) Q=0 ;;
  base-rich) ;;
  base-right) M=right ;;
  base-left) M=left ;;
  base-top) M=top ;;
  map-rich) S=map ;;
  map-clean) S=map; E=no; P=no; C=no ;;
  maneuver-only) S=instructioncard ;;
  *) usage ;;
esac
batch <<EOF
navigation.query=$Q
navigation.surface=$S
navigation.ETA=$E
navigation.speedLimit=$P
navigation.compass=$C
navigation.maneuver=$M
EOF
RC=$?; [ "$RC" -eq 0 ] || exit "$RC"
[ "$cmd" = use-temp ] && { apply_presentation; exit $?; }
exit 0
