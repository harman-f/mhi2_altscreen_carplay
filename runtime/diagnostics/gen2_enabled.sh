#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
. "${0%/*}/master_settings.sh" || exit 10
case "${1:-status}" in
  status) exec "$HELPER" get --key carplay.enabled ;;
  persist|clear-persist) blocked ;;
  clear-temp) clear_key carplay.enabled; exit $? ;;
  temp) [ "$#" -eq 2 ] || usage; shift ;;
  on|off|0|1) [ "$#" -eq 1 ] || usage ;;
  *) usage ;;
esac
case "$1" in on|1) set_key carplay.enabled 1 ;; off|0) set_key carplay.enabled 0 ;; *) usage ;; esac
