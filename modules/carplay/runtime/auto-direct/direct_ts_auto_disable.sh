#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init || { echo "AUTO_DIRECT_DISABLE=FAIL_RUNTIME"; exit 3; }

ENABLED=/mnt/app/root/mibr-carplay-autodirect.enabled
mount -uw /mnt/app 2>/dev/null || { echo "AUTO_DIRECT_DISABLE=FAIL_APP_RW"; exit 20; }
rm -f "$ENABLED" 2>/dev/null || true
sync
mount -ur /mnt/app 2>/dev/null || true

"$BASE/scripts/direct_ts_auto_stop.sh" >/dev/null 2>&1 || {
  rm -f /tmp/mibr-isotx2-gate.direct 2>/dev/null || true
}

echo "AUTO_DIRECT_DISABLE=PASS"
echo "GATE=STOCK"
echo "Boot hook remains inert; re-enable does not require another lsd.sh edit."
exit 0
