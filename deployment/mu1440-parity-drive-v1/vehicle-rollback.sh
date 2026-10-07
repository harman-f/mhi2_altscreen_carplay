#!/bin/ksh
set -u

# BEGIN_TARGET_ENV -- proven installed MU1440 runtime paths
export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/media/gracenote/bin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin:/mnt/app/armle/usr/sbin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1
# END_TARGET_ENV

SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2
cd "$ROOT" || exit 2
. "$ROOT/runtime/package-logging.sh" || exit 20
package_log_init master-rollback || { echo "PACKAGE_LOG_BOOTSTRAP=FAIL"; exit 20; }

echo "=== PARITY DRIVE VEHICLE ROLLBACK ==="
mibr_run_logged "$ROOT/uninstall.sh"
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "PARITY_VEHICLE_ROLLBACK=FAIL rc=$RC"
  echo "REBOOT_SKIPPED=YES"
  exit 20
fi

echo "PARITY_VEHICLE_ROLLBACK=PASS"
echo "reboot=normal_ioc"
sync
sync
sync
package_card_ro || { echo "SD_MOUNT_STATE=UNCONFIRMED REBOOT_SKIPPED=YES"; exit 23; }
on -f rcc /usr/apps/mib2_ioc_flash reboot
