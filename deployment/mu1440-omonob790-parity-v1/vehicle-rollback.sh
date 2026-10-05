#!/bin/ksh
set -u

SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2
cd "$ROOT" || exit 2

echo "=== OMONOB790 PARITY VEHICLE ROLLBACK ==="
ksh ./uninstall.sh
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
on -f rcc /usr/apps/mib2_ioc_flash reboot
