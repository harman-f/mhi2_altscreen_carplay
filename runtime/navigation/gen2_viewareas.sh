#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
. "${0%/*}/master_settings.sh" || exit 10
case "${1:-status}" in
  status) exec "$HELPER" status ;;
  persist-default|persist-set|clear-persist) blocked ;;
  temp-default)
    echo "result=INVALID_VALUE use_complete_dual_preset_before_reconnect"; exit 2 ;;
  clear-temp) clear_key viewareas.enabled ;;
  select) [ "$#" -eq 2 ] || usage; set_key viewarea.selected "$2" ;;
  temp-set)
    [ "$#" -eq 3 ] || usage
    case "$2" in
      enabled|count|initial|transition_ms) KEY=viewareas.$2 ;;
      view0.*) KEY=viewarea.0.${2#view0.} ;;
      view1.*) KEY=viewarea.1.${2#view1.} ;;
      *) usage ;;
    esac
    set_key "$KEY" "$3" ;;
  *) usage ;;
esac
