#!/bin/ksh
set -u

SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2
cd "$ROOT" || exit 2
. "$ROOT/runtime/package-logging.sh" || exit 20
package_log_init master-rollback || { echo "PACKAGE_LOG_BOOTSTRAP=FAIL"; exit 20; }

echo "=== OMONOB790 PARITY VEHICLE ROLLBACK ==="
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
