#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

BASE=/mnt/app/root/altscreen-u2
RUNNER=$BASE/bin/parity-session
BRIDGE=$BASE/bin/direct-ts-parity
INPUT=tcp://127.0.0.1:19820
OUTPUT=/dev/mlb/isoTX2

cfg_path(){
  NAME=$1
  [ -r "/tmp/$NAME" ] && { echo "/tmp/$NAME"; return; }
  [ -r "/mnt/app/root/$NAME" ] && { echo "/mnt/app/root/$NAME"; return; }
  echo ""
}

cfg_scalar(){
  NAME=$1
  P=$(cfg_path "$NAME")
  [ -n "$P" ] && cat "$P" || echo ""
}

need_scalar(){
  NAME=$1
  WANT=$2
  GOT=$(cfg_scalar "$NAME")
  [ "$GOT" = "$WANT" ] || {
    echo "PARITY_SESSION=FAIL profile_scalar name=$NAME expected=$WANT actual=${GOT:-MISSING}"
    exit 20
  }
}

need_line(){
  NAME=$1
  WANT=$2
  P=$(cfg_path "$NAME")
  [ -n "$P" ] && grep -Fxq "$WANT" "$P" 2>/dev/null || {
    echo "PARITY_SESSION=FAIL profile_line file=$NAME expected=$WANT"
    exit 21
  }
}

case "${1:-}" in
  '' ) SECONDS=120 ;;
  *[!0-9]* ) echo "usage: $0 [SECONDS 5..600]"; exit 2 ;;
  * ) SECONDS=$1 ;;
esac
[ "$SECONDS" -ge 5 ] && [ "$SECONDS" -le 600 ] || { echo "usage: $0 [SECONDS 5..600]"; exit 2; }

[ -x "$RUNNER" ] || { echo "PARITY_SESSION=FAIL missing_runner=$RUNNER"; exit 10; }
[ -x "$BRIDGE" ] || { echo "PARITY_SESSION=FAIL missing_bridge=$BRIDGE"; exit 11; }
[ -x /eso/bin/apps/dmdt ] || { echo "PARITY_SESSION=FAIL missing_dmdt"; exit 12; }

need_scalar mibr-carplay111-compat-profile omonob790
need_scalar mibr-carplay111-fps 40
need_scalar mibr-carplay111-sourceversion 950.7.1
need_scalar mibr-carplay111-url maps:/car/instrumentcluster/map
need_scalar mibr-carplay-autodirect 0

need_line mibr-carplay111-display.conf widthPixels=1010
need_line mibr-carplay111-display.conf heightPixels=376
need_line mibr-carplay111-display.conf widthPhysical=202
need_line mibr-carplay111-display.conf heightPhysical=75
need_line mibr-carplay111-display.conf uuid=b7e6c5a0-2222-4000-8000-000000000002

need_line mibr-carplay111-viewareas.conf enabled=1
need_line mibr-carplay111-viewareas.conf count=1
need_line mibr-carplay111-viewareas.conf initial=0
need_line mibr-carplay111-viewareas.conf view0.x=0
need_line mibr-carplay111-viewareas.conf view0.y=0
need_line mibr-carplay111-viewareas.conf view0.w=1010
need_line mibr-carplay111-viewareas.conf view0.h=376
need_line mibr-carplay111-viewareas.conf view0.safe.x=202
need_line mibr-carplay111-viewareas.conf view0.safe.y=16
need_line mibr-carplay111-viewareas.conf view0.safe.w=606
need_line mibr-carplay111-viewareas.conf view0.safe.h=344

need_line mibr-carplay111-keyframes.conf enabled=0
need_line mibr-carplay111-keyframes.conf watchdog_ms=0

[ -r /tmp/mibr-carplay111.state ] && [ "$(cat /tmp/mibr-carplay111.state 2>/dev/null)" = streaming ] || {
  echo "PARITY_SESSION=FAIL stream111_not_streaming"
  exit 22
}
[ -r /tmp/mibr-carplay111.heartbeat ] || {
  echo "PARITY_SESSION=FAIL stream111_heartbeat_missing"
  exit 23
}

echo "PARITY_SESSION=PREFLIGHT_PASS seconds=$SECONDS"
echo "ownership=dmdt_omonob790"
echo "transport=source_clock_32.32_to_90khz_no_frame_pacer"
exec "$RUNNER" "$BRIDGE" "$INPUT" "$OUTPUT" "$SECONDS"
