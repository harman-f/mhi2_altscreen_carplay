#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
MIBR_ROOT=${MIBR_ROOT:-/mnt/app/root/mibr}
. $MIBR_ROOT/scripts/common.sh
runtime_init_durable || { echo "FAIL runtime/log bootstrap"; exit 3; }

MARKER=$MIBR_ROOT/config/features/mibr-carplay111-viewareas.enabled

status(){
  if [ -e "$MARKER" ]; then
    echo "VIEWAREA_FALLBACK=ENABLED_NEXT_BOOT"
  else
    echo "VIEWAREA_FALLBACK=DISABLED_NEXT_BOOT"
  fi
  echo "marker=$MARKER"
}

case "${1:-status}" in
  status)
    status
    exit 0
    ;;
  enable)
    mount -uw /mnt/app 2>/dev/null || { echo "FAIL cannot mount /mnt/app rw"; exit 20; }
    : > "$MARKER" || {
      mount -ur /mnt/app 2>/dev/null || true
      echo "FAIL cannot create $MARKER"
      exit 21
    }
    sync
    mount -ur /mnt/app 2>/dev/null || true
    [ -e "$MARKER" ] || { echo "FAIL marker verification"; exit 22; }
    status
    echo "REBOOT_REQUIRED=YES"
    echo "Next CarPlay child boot will advertise full-screen viewAreas + safeArea + initialViewArea=0."
    ;;
  disable)
    mount -uw /mnt/app 2>/dev/null || { echo "FAIL cannot mount /mnt/app rw"; exit 23; }
    rm -f "$MARKER" || {
      mount -ur /mnt/app 2>/dev/null || true
      echo "FAIL cannot remove $MARKER"
      exit 24
    }
    sync
    mount -ur /mnt/app 2>/dev/null || true
    [ ! -e "$MARKER" ] || { echo "FAIL marker still present"; exit 25; }
    status
    echo "REBOOT_REQUIRED=YES"
    echo "Next CarPlay child boot returns to the minimal display descriptor without viewAreas."
    ;;
  *)
    echo "Usage: $0 {status|enable|disable}"
    exit 2
    ;;
esac
exit 0
