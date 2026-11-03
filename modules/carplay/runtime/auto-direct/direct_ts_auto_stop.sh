#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init || { echo "AUTO_DIRECT_STOP=FAIL_RUNTIME"; exit 3; }

SUPPID=/tmp/mibr-direct-auto-supervisor.pid
WDPID=/tmp/mibr-direct-auto-watchdog.pid
BRIDGEPID=/tmp/mibr-direct-auto-bridge.pid
GATE=$BASE/scripts/writev_gate.sh

"$GATE" stock >/dev/null 2>&1 || rm -f /tmp/mibr-isotx2-gate.direct 2>/dev/null || true

for PF in "$BRIDGEPID" "$SUPPID" "$WDPID"; do
  if [ -r "$PF" ]; then
    P=$(cat "$PF" 2>/dev/null)
    [ -n "$P" ] && kill "$P" 2>/dev/null || true
  fi
done

sleep 2
"$GATE" stock >/dev/null 2>&1 || rm -f /tmp/mibr-isotx2-gate.direct 2>/dev/null || true
rm -f "$BRIDGEPID" "$SUPPID" "$WDPID" /tmp/mibr-direct-auto.heartbeat 2>/dev/null || true
echo "stopped" > /tmp/mibr-direct-auto.state 2>/dev/null || true

echo "AUTO_DIRECT_STOP=PASS"
echo "GATE=STOCK"
exit 0
