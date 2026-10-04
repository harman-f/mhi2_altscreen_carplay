#!/bin/ksh
set -u

SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2
cd "$ROOT" || exit 2

echo "=== CLASSIC111 VEHICLE INSTALL ==="
echo "phase=preflight"
ksh ./install.sh --check || {
  echo "VEHICLE_INSTALL=FAIL_PRECHECK"
  exit 20
}

echo "phase=apply"
ksh ./install.sh --apply || {
  echo "VEHICLE_INSTALL=FAIL_APPLY"
  exit 21
}

echo "VEHICLE_INSTALL=PASS"
echo "reboot=normal_ioc"
sync
sync
sync
on -f rcc /usr/apps/mib2_ioc_flash reboot
