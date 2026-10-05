#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init || { echo "DIRECT_FPS=FAIL_RUNTIME"; exit 3; }
load_altscreen_config || { echo "DIRECT_FPS=FAIL_CONFIG"; exit 4; }

NAME=$FPS_CONFIG_NAME
TEMP="$MIBR_CFG_TEMP_ROOT/$NAME"
PERSIST="$MIBR_CFG_PERSIST_ROOT/$NAME"
BRIDGEPID=/tmp/mibr-direct-auto-bridge.pid

usage(){
  echo "usage: $0 status|20|25|30|40|temp {20|25|30|40}|persist {20|25|30|40}|clear-temp|clear-persist|default"
  echo "bare FPS writes a temporary override; persistent changes require the 'persist' verb"
  exit 64
}

valid_fps(){
  case "$1" in 20|25|30|40) return 0 ;; *) return 1 ;; esac
}

effective(){
  runtime_cfg_get "$NAME" "$ALTSCREEN111_FPS"
}

show_status(){
  E=$(effective)
  echo "=== CARPLAY111 FPS ==="
  echo "default=$ALTSCREEN111_FPS"
  echo "effective=$E"
  echo "source=$(runtime_cfg_source "$NAME")"
  echo "temporary_path=$TEMP"
  [ -r "$TEMP" ] && echo "temporary_value=$(cat "$TEMP" 2>/dev/null)" || echo "temporary_value=none"
  echo "persistent_path=$PERSIST"
  [ -r "$PERSIST" ] && echo "persistent_value=$(cat "$PERSIST" 2>/dev/null)" || echo "persistent_value=none"
  echo "scope=source_maxFPS+direct_output_pacer"
  if [ -r /tmp/mibr-alt111-source-timing.status ]; then
    cat /tmp/mibr-alt111-source-timing.status 2>/dev/null || true
  fi
  if [ -r /tmp/mibr-direct-remux.status ]; then
    grep -E '^(input_bps|most_bps|pace_|last_input_interval_us|min_input_interval_us|max_input_interval_us|last_emit_interval_us|max_emit_jitter_us|write_eagain|last_block_wait_us|max_block_wait_us)=' /tmp/mibr-direct-remux.status 2>/dev/null || true
  fi
}

write_temp(){
  V=$1
  T="$TEMP.new.$$"
  echo "$V" > "$T" || { rm -f "$T" 2>/dev/null || true; echo "DIRECT_FPS=FAIL_TEMP_WRITE"; exit 11; }
  mv "$T" "$TEMP" || { rm -f "$T" 2>/dev/null || true; echo "DIRECT_FPS=FAIL_TEMP_RENAME"; exit 12; }
}

write_persist(){
  V=$1
  mount -uw /mnt/app 2>/dev/null || { echo "DIRECT_FPS=FAIL_MOUNT_RW"; exit 10; }
  T="$PERSIST.new.$$"
  echo "$V" > "$T" || {
    rm -f "$T" 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    echo "DIRECT_FPS=FAIL_PERSIST_WRITE"; exit 11
  }
  mv "$T" "$PERSIST" || {
    rm -f "$T" 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    echo "DIRECT_FPS=FAIL_PERSIST_RENAME"; exit 12
  }
  chmod 644 "$PERSIST" 2>/dev/null || true
  sync
  mount -ur /mnt/app 2>/dev/null || true
}

clear_persist(){
  mount -uw /mnt/app 2>/dev/null || { echo "DIRECT_FPS=FAIL_MOUNT_RW"; exit 10; }
  rm -f "$PERSIST" 2>/dev/null || true
  sync
  mount -ur /mnt/app 2>/dev/null || true
}

report_change(){
  OLD=$1
  NEW=$(effective)
  echo "DIRECT_FPS_EFFECTIVE=$NEW"
  echo "config_source=$(runtime_cfg_source "$NAME")"
  if [ "$OLD" != "$NEW" ]; then
    echo "CARPLAY_RECONNECT_REQUIRED=YES old_source_fps=$OLD new_source_fps=$NEW"
    echo "bridge_restart_requested=deferred_until_source_renegotiation"
  else
    echo "CARPLAY_RECONNECT_REQUIRED=NO"
  fi
}

OLD=$(effective)
case "${1:-status}" in
  status)
    show_status
    ;;
  20|25|30|40)
    write_temp "$1"
    echo "DIRECT_FPS=SET layer=temp fps=$1"
    report_change "$OLD"
    ;;
  temp)
    [ "$#" -eq 2 ] && valid_fps "$2" || usage
    write_temp "$2"
    echo "DIRECT_FPS=SET layer=temp fps=$2"
    report_change "$OLD"
    ;;
  persist)
    [ "$#" -eq 2 ] && valid_fps "$2" || usage
    write_persist "$2"
    echo "DIRECT_FPS=SET layer=persistent fps=$2"
    report_change "$OLD"
    ;;
  clear-temp|default)
    rm -f "$TEMP" 2>/dev/null || true
    echo "DIRECT_FPS=CLEAR layer=temp"
    report_change "$OLD"
    ;;
  clear-persist)
    clear_persist
    echo "DIRECT_FPS=CLEAR layer=persistent"
    report_change "$OLD"
    ;;
  *)
    usage
    ;;
esac
