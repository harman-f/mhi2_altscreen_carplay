#!/bin/ksh
set -u

SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2
cd "$ROOT" || exit 2

echo "=== CLASSIC111 VEHICLE ROLLBACK ==="
ksh ./uninstall.sh || {
  echo "VEHICLE_ROLLBACK=FAIL"
  exit 20
}

echo "VEHICLE_ROLLBACK=PASS"
echo "reboot=normal_ioc"
sync
sync
sync
on -f rcc /usr/apps/mib2_ioc_flash reboot
