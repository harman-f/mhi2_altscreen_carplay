#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

# BEGIN_TARGET_ENV -- proven installed MU1440 runtime paths
export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/media/gracenote/bin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin:/mnt/app/armle/usr/sbin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1
# END_TARGET_ENV

echo "=== CLASSIC_SINGLE_VIEW PARITY SESSION ==="
for F in /tmp/mibr-parity-session.backend /tmp/mibr-parity-session.ticket /tmp/mibr-alt111-native-gate.status /tmp/mibr-alt111-gen2.status; do
  [ ! -r "$F" ] || { echo "$F"; cat "$F"; }
done
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
