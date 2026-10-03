#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init || { echo "DIRECT_SOURCE_MODE=FAIL_RUNTIME"; exit 3; }
load_altscreen_config || { echo "DIRECT_SOURCE_MODE=FAIL_CONFIG"; exit 4; }

FILE=$DIRECT_SOURCE_FRAMING_OVERRIDE_FILE
BRIDGEPID=/tmp/mibr-direct-auto-bridge.pid

show_status(){
  load_altscreen_config >/dev/null 2>&1 || true
  case "$DIRECT_SOURCE_FRAMING" in
    1) MODE=m1au ;;
    *) MODE=raw ;;
  esac
  echo "direct_source_mode=$MODE"
  echo "direct_source_framing=$DIRECT_SOURCE_FRAMING"
  [ -r "$FILE" ] && echo "override=$(cat "$FILE" 2>/dev/null)" || echo "override=none"
  [ -r /tmp/mibr-direct-remux.status ] &&     grep -E '^(input_mode|m1au_records|m1au_sequence|m1au_sequence_gaps|m1au_flags|m1au_ts_raw|m1au_ts_word1_delta|m1au_ts_word2_delta)='       /tmp/mibr-direct-remux.status 2>/dev/null || true
}

restart_bridge(){
  P=
  [ -r "$BRIDGEPID" ] && P=$(cat "$BRIDGEPID" 2>/dev/null)
  if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then
    kill "$P" 2>/dev/null || true
    echo "bridge_restart_requested=1"
  else
    echo "bridge_restart_requested=0"
  fi
}

store(){
  V=$1
  mount -uw /mnt/app 2>/dev/null || { echo "DIRECT_SOURCE_MODE=FAIL_MOUNT_RW"; exit 10; }
  TMP="$FILE.new.$$"
  echo "$V" > "$TMP" || {
    rm -f "$TMP" 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    echo "DIRECT_SOURCE_MODE=FAIL_WRITE"
    exit 11
  }
  mv "$TMP" "$FILE" || {
    rm -f "$TMP" 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    echo "DIRECT_SOURCE_MODE=FAIL_RENAME"
    exit 12
  }
  sync 2>/dev/null || true
  mount -ur /mnt/app 2>/dev/null || true
}

case "${1:-status}" in
  status)
    show_status
    ;;
  raw)
    store 0
    echo "DIRECT_SOURCE_MODE=SET mode=raw-annexb"
    restart_bridge
    ;;
  m1au)
    store 1
    echo "DIRECT_SOURCE_MODE=SET mode=m1au-v1"
    echo "note=PTS/PCR remain CFR in framing-v1; M1AU is metadata-preserving diagnostics"
    restart_bridge
    ;;
  default)
    mount -uw /mnt/app 2>/dev/null || { echo "DIRECT_SOURCE_MODE=FAIL_MOUNT_RW"; exit 10; }
    rm -f "$FILE" 2>/dev/null || true
    sync 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    echo "DIRECT_SOURCE_MODE=DEFAULT"
    restart_bridge
    ;;
  *)
    echo "usage: $0 status|raw|m1au|default"
    exit 64
    ;;
esac
