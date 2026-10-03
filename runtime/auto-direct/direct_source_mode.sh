#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init || { echo "DIRECT_SOURCE_MODE=FAIL_RUNTIME"; exit 3; }
load_altscreen_config || { echo "DIRECT_SOURCE_MODE=FAIL_CONFIG"; exit 4; }

NAME=$FRAMING_CONFIG_NAME
TEMP="$MIBR_CFG_TEMP_ROOT/$NAME"
PERSIST="$MIBR_CFG_PERSIST_ROOT/$NAME"
BRIDGEPID=/tmp/mibr-direct-auto-bridge.pid

usage(){
  echo "usage: $0 status|raw|m1au|temp {raw|m1au}|persist {raw|m1au}|clear-temp|clear-persist|default"
  echo "bare raw/m1au writes a temporary override"
  exit 64
}

valid_mode(){
  case "$1" in raw|m1au) return 0 ;; *) return 1 ;; esac
}

effective(){
  V=$(runtime_cfg_get "$NAME" raw)
  case "$V" in m1au|1) echo m1au ;; *) echo raw ;; esac
}

show_status(){
  E=$(effective)
  echo "=== CARPLAY111 FRAMING ==="
  echo "default=raw"
  echo "effective=$E"
  echo "source=$(runtime_cfg_source "$NAME")"
  echo "temporary_path=$TEMP"
  [ -r "$TEMP" ] && echo "temporary_value=$(cat "$TEMP" 2>/dev/null)" || echo "temporary_value=none"
  echo "persistent_path=$PERSIST"
  [ -r "$PERSIST" ] && echo "persistent_value=$(cat "$PERSIST" 2>/dev/null)" || echo "persistent_value=none"
  echo "pts_pcr=CFR_UNCHANGED"
  [ -r /tmp/mibr-direct-remux.status ] &&     grep -E '^(input_mode|m1au_records|m1au_sequence|m1au_sequence_gaps|m1au_flags|m1au_ts_raw|m1au_ts_word1_delta|m1au_ts_word2_delta)='       /tmp/mibr-direct-remux.status 2>/dev/null || true
}

write_temp(){
  V=$1
  T="$TEMP.new.$$"
  echo "$V" > "$T" || { rm -f "$T" 2>/dev/null || true; echo "DIRECT_SOURCE_MODE=FAIL_TEMP_WRITE"; exit 11; }
  mv "$T" "$TEMP" || { rm -f "$T" 2>/dev/null || true; echo "DIRECT_SOURCE_MODE=FAIL_TEMP_RENAME"; exit 12; }
}

write_persist(){
  V=$1
  mount -uw /mnt/app 2>/dev/null || { echo "DIRECT_SOURCE_MODE=FAIL_MOUNT_RW"; exit 10; }
  T="$PERSIST.new.$$"
  echo "$V" > "$T" || {
    rm -f "$T" 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    echo "DIRECT_SOURCE_MODE=FAIL_PERSIST_WRITE"; exit 11
  }
  mv "$T" "$PERSIST" || {
    rm -f "$T" 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    echo "DIRECT_SOURCE_MODE=FAIL_PERSIST_RENAME"; exit 12
  }
  chmod 644 "$PERSIST" 2>/dev/null || true
  sync
  mount -ur /mnt/app 2>/dev/null || true
}

clear_persist(){
  mount -uw /mnt/app 2>/dev/null || { echo "DIRECT_SOURCE_MODE=FAIL_MOUNT_RW"; exit 10; }
  rm -f "$PERSIST" 2>/dev/null || true
  sync
  mount -ur /mnt/app 2>/dev/null || true
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

case "${1:-status}" in
  status)
    show_status
    ;;
  raw|m1au)
    write_temp "$1"
    echo "DIRECT_SOURCE_MODE=SET layer=temp mode=$1"
    restart_bridge
    ;;
  temp)
    [ "$#" -eq 2 ] && valid_mode "$2" || usage
    write_temp "$2"
    echo "DIRECT_SOURCE_MODE=SET layer=temp mode=$2"
    restart_bridge
    ;;
  persist)
    [ "$#" -eq 2 ] && valid_mode "$2" || usage
    write_persist "$2"
    echo "DIRECT_SOURCE_MODE=SET layer=persistent mode=$2"
    restart_bridge
    ;;
  clear-temp|default)
    rm -f "$TEMP" 2>/dev/null || true
    echo "DIRECT_SOURCE_MODE=CLEAR layer=temp"
    restart_bridge
    ;;
  clear-persist)
    clear_persist
    echo "DIRECT_SOURCE_MODE=CLEAR layer=persistent"
    restart_bridge
    ;;
  *)
    usage
    ;;
esac
