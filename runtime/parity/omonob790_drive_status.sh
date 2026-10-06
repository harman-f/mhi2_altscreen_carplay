#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

ENABLE=/mnt/app/root/mibr-parity-drive.enabled
echo "=== PARITY DRIVE ==="
if [ -r "$ENABLE" ]; then
  echo "enabled=$(cat "$ENABLE" 2>/dev/null)"
else
  echo "enabled=0"
fi
[ -r /tmp/mibr-parity-drive-supervisor.pid ] && echo "supervisor_pid=$(cat /tmp/mibr-parity-drive-supervisor.pid 2>/dev/null)" || echo "supervisor_pid=none"
[ -r /tmp/mibr-parity-drive.state ] && echo "supervisor_state=$(cat /tmp/mibr-parity-drive.state 2>/dev/null)" || echo "supervisor_state=none"
[ -r /tmp/mibr-parity-drive.heartbeat ] && echo "supervisor_heartbeat=$(cat /tmp/mibr-parity-drive.heartbeat 2>/dev/null)" || echo "supervisor_heartbeat=none"

echo
echo "=== PARITY SESSION ==="
for F in /tmp/mibr-parity-session.state /tmp/mibr-parity-session.pid /tmp/mibr-parity-session-bridge.pid /tmp/mibr-parity-session-watchdog.pid; do
  if [ -r "$F" ]; then echo "$F=$(cat "$F" 2>/dev/null)"; else echo "$F=none"; fi
done
[ -e /tmp/mibr-parity-session.lock ] && echo "session_lock=present" || echo "session_lock=none"

echo
echo "=== PARITY TRANSPORT ==="
if [ -r /tmp/mibr-parity-ts.status ]; then
  grep -E '^(state|input_records|input_idrs|input_non_idr_aus|output_aus_started|output_aus_completed|output_idr_aus_started|output_non_idr_aus_started|sequence_gaps|dropped_wait_idr|safe_recoveries|blocks_written|bytes_written|write_eagain|write_errors|last_write_us|max_write_us|queue_aus|queue_packets)=' /tmp/mibr-parity-ts.status 2>/dev/null || true
else
  echo "parity_transport_status=missing"
fi

echo
echo "=== SOURCE / GEN2 ==="
[ -r /tmp/mibr-carplay111.state ] && echo "stream111_state=$(cat /tmp/mibr-carplay111.state 2>/dev/null)" || echo "stream111_state=missing"
[ -r /tmp/mibr-carplay111.heartbeat ] && echo "stream111_heartbeat=$(cat /tmp/mibr-carplay111.heartbeat 2>/dev/null)" || echo "stream111_heartbeat=missing"
if [ -r /tmp/mibr-alt111-gen2.status ]; then
  grep -E '^(source_aus|source_idrs|delivered_aus|dropped_aus|queue_count|queue_bytes|stream_gen|codec_gen|consumer_gen)=' /tmp/mibr-alt111-gen2.status 2>/dev/null || true
fi
if [ -r /tmp/mibr-alt111-source-timing.status ]; then
  grep -E '^(configured_max_fps|frames_total|source_arrival_fps_x100|source_input_bps|source_arrival_last_us|source_arrival_min_us|source_arrival_max_us)=' /tmp/mibr-alt111-source-timing.status 2>/dev/null || true
fi

echo
echo "=== GATE ==="
[ -r /tmp/mibr-alt111-native-gate.status ] && cat /tmp/mibr-alt111-native-gate.status || echo "gate_status=missing"

echo
echo "=== LOG ROOTS ==="
for R in /net/mmx/fs/sda0/esd/mibr-parity-drive-logs /mnt/app/root/mibr-parity-drive-logs /tmp/mibr-parity-drive-logs; do
  [ -d "$R" ] && echo "$R"
done
