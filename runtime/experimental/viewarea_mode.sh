#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
# Compatibility wrapper. Canonical backend: gen2_viewareas.sh / mibr-carplay111-viewareas.conf.
set -u
H=/mnt/app/root/altscreen-u2/scripts/gen2_viewareas.sh
[ -x "$H" ] || { echo "VIEWAREA_MODE=FAIL_HELPER"; exit 3; }

case "${1:-status}" in
  status) exec "$H" status ;;
  on) exec "$H" temp-set enabled 1 ;;
  off) exec "$H" temp-set enabled 0 ;;
  temp)
    [ "$#" -eq 2 ] || exit 2
    case "$2" in on|1) exec "$H" temp-set enabled 1 ;; off|0) exec "$H" temp-set enabled 0 ;; *) exit 2 ;; esac
    ;;
  persist)
    [ "$#" -eq 2 ] || exit 2
    case "$2" in on|1) exec "$H" persist-set enabled 1 ;; off|0) exec "$H" persist-set enabled 0 ;; *) exit 2 ;; esac
    ;;
  clear-temp) exec "$H" clear-temp ;;
  clear-persist) exec "$H" clear-persist ;;
  *) echo "usage: $0 status|on|off|temp {on|off}|persist {on|off}|clear-temp|clear-persist"; exit 2 ;;
esac
