#!/bin/ksh
set -u

SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2
cd "$ROOT" || exit 2

echo "=== OMONOB790 PARITY VEHICLE INSTALL ==="
echo "phase=preflight"
ksh ./install.sh --check || {
  echo "PARITY_VEHICLE_INSTALL=FAIL_PRECHECK"
  exit 20
}

echo "phase=apply"
ksh ./install.sh --apply
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "PARITY_VEHICLE_INSTALL=FAIL_APPLY rc=$RC"
  echo "phase=automatic_recovery"
  ksh ./uninstall.sh
  URC=$?
  if [ "$URC" -ne 0 ]; then
    echo "PARITY_VEHICLE_INSTALL=FAIL_RECOVERY rc=$URC"
    echo "REBOOT_SKIPPED=YES"
    exit 22
  fi
  echo "PARITY_VEHICLE_INSTALL=RECOVERY_PASS"
  echo "reboot=normal_ioc_after_recovery"
  sync
  sync
  sync
  on -f rcc /usr/apps/mib2_ioc_flash reboot
  exit $?
fi

echo "PARITY_VEHICLE_INSTALL=PASS"
echo "reboot=normal_ioc"
sync
sync
sync
on -f rcc /usr/apps/mib2_ioc_flash reboot
