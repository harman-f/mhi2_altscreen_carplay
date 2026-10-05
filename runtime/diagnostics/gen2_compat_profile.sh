#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
HELPER=/mnt/app/root/altscreen-u2/bin/alt111-settings
[ -x "$HELPER" ] || { echo "result=APPLY_FAILED missing_settings_helper"; exit 10; }
case "${1:-status}" in
  status) exec "$HELPER" get --key preset.id ;;
  omonob790|mibr_dual_view|mibr_legacy) PRESET=$1 ;;
  mibr) PRESET=mibr_legacy ;;
  temp)
    [ "$#" -eq 2 ] || exit 2
    case "$2" in mibr) PRESET=mibr_legacy ;; omonob790|mibr_dual_view|mibr_legacy) PRESET=$2 ;; *) exit 2 ;; esac ;;
  clear-temp|default) exec "$HELPER" clear-temp ;;
  persist|clear-persist) echo "result=POLICY_BLOCKED persistent_backup_powerloss_gate"; exit 24 ;;
  *) echo "usage: $0 status|omonob790|mibr_dual_view|mibr_legacy|temp PRESET|clear-temp"; exit 2 ;;
esac
exec "$HELPER" preset --preset "$PRESET"
