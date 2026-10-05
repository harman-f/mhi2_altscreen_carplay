#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

echo "=== OMONOB790 PARITY SESSION ==="
for F in   /tmp/mibr-parity-session.state   /tmp/mibr-parity-session.pid   /tmp/mibr-parity-session-bridge.pid /tmp/mibr-parity-session-watchdog.pid /tmp/mibr-parity-session.lock
do
  if [ -r "$F" ]; then
    echo "$F=$(cat "$F" 2>/dev/null)"
  else
    echo "$F=none"
  fi
done

if [ -r /tmp/mibr-parity-ts.status ]; then
  echo
  echo "=== PARITY TRANSPORT ==="
  cat /tmp/mibr-parity-ts.status
else
  echo "PARITY_TRANSPORT_STATUS=NOT_AVAILABLE"
fi

echo
echo "=== SOURCE ==="
[ -r /tmp/mibr-carplay111.state ] && echo "stream111_state=$(cat /tmp/mibr-carplay111.state 2>/dev/null)" || echo "stream111_state=missing"
[ -r /tmp/mibr-carplay111.heartbeat ] && echo "stream111_heartbeat=$(cat /tmp/mibr-carplay111.heartbeat 2>/dev/null)" || echo "stream111_heartbeat=missing"

echo
echo "=== LEGACY AUTO DIRECT ==="
if [ -r /tmp/mibr-carplay-autodirect ]; then
  echo "autodirect_source=temp"
  echo "autodirect=$(cat /tmp/mibr-carplay-autodirect 2>/dev/null)"
elif [ -r /mnt/app/root/mibr-carplay-autodirect ]; then
  echo "autodirect_source=persistent"
  echo "autodirect=$(cat /mnt/app/root/mibr-carplay-autodirect 2>/dev/null)"
else
  echo "autodirect_source=default"
  echo "autodirect=1"
fi

echo
echo "=== M1AU MARKER ==="
[ -e /tmp/mibr-alt111-au-framing.enabled ] && echo "m1au_marker=present" || echo "m1au_marker=absent"
