#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

# BEGIN_TARGET_ENV -- proven installed MU1440 runtime paths
export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/media/gracenote/bin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin:/mnt/app/armle/usr/sbin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1
# END_TARGET_ENV
HELPER=/mnt/app/root/altscreen-u2/bin/alt111-settings
[ -x "$HELPER" ] || { echo "result=APPLY_FAILED missing_settings_helper"; exit 10; }
case "${1:-status}" in
  status) exec "$HELPER" status ;;
  temp) exec "$HELPER" preset --preset classic_single_view ;;
  dual-temp) exec "$HELPER" preset --preset mibr_dual_view ;;
  clear-temp) exec "$HELPER" clear-temp ;;
  persist|clear-persist) echo "result=POLICY_BLOCKED persistent_backup_powerloss_gate"; exit 24 ;;
  *) echo "usage: $0 status|temp|dual-temp|clear-temp"; exit 2 ;;
esac
