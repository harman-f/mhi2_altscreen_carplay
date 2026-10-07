#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
# Disable parity-drive and request a token-bound session stop if active.

set -u
BASE=/mnt/app/root/altscreen-u2
RUNNER=$BASE/bin/parity-session
ENABLE=/mnt/app/root/mibr-parity-drive.enabled
PROFILE_MARKER=/tmp/mibr-parity-drive-profile-applied

mount -uw /mnt/app 2>/dev/null || { echo "PARITY_DRIVE_DISABLE=FAIL_APP_RW"; exit 20; }
echo 0 > "$ENABLE" || { mount -ur /mnt/app 2>/dev/null || true; echo "PARITY_DRIVE_DISABLE=FAIL_WRITE"; exit 21; }
chmod 644 "$ENABLE" 2>/dev/null || true
sync
mount -ur /mnt/app 2>/dev/null || true

if [ -e /tmp/mibr-parity-session.lock ]; then
  "$RUNNER" --stop
  RC=$?
  [ "$RC" -eq 0 ] || { echo "PARITY_DRIVE_DISABLE=STOP_UNCONFIRMED rc=$RC"; exit "$RC"; }
fi

N=0
while [ "$N" -lt 20 ] && [ -r /tmp/mibr-parity-drive-supervisor.pid ]; do
  sleep 1
  N=$((N+1))
done

rm -f "$PROFILE_MARKER" 2>/dev/null || true
sync 2>/dev/null || true
mount -ur /net/mmx/fs/sda0 2>/dev/null || true

echo "PARITY_DRIVE_DISABLE=PASS"
echo "parity_drive_enabled=0"
echo "active_session=$( [ -e /tmp/mibr-parity-session.lock ] && echo 1 || echo 0 )"
exit 0
