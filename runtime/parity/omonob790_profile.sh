#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
HELPER=/mnt/app/root/altscreen-u2/bin/alt111-settings
[ -x "$HELPER" ] || { echo "result=APPLY_FAILED missing_settings_helper"; exit 10; }
case "${1:-status}" in
  status) exec "$HELPER" status ;;
  temp) exec "$HELPER" preset --preset omonob790 ;;
  dual-temp) exec "$HELPER" preset --preset mibr_dual_view ;;
  clear-temp) exec "$HELPER" clear-temp ;;
  persist|clear-persist) echo "result=POLICY_BLOCKED persistent_backup_powerloss_gate"; exit 24 ;;
  *) echo "usage: $0 status|temp|dual-temp|clear-temp"; exit 2 ;;
esac
