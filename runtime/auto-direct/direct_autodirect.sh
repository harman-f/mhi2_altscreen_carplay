#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init || { echo "AUTO_DIRECT_CONTROL=FAIL_RUNTIME"; exit 3; }

NAME=$AUTODIRECT_CONFIG_NAME
TEMP=$MIBR_CFG_TEMP_ROOT/$NAME
PERSIST=$MIBR_CFG_PERSIST_ROOT/$NAME
START=/mnt/app/root/altscreen-u2/scripts/direct_ts_auto_start.sh
STOP=/mnt/app/root/altscreen-u2/scripts/direct_ts_auto_stop.sh
ENABLE=/mnt/app/root/altscreen-u2/scripts/direct_ts_auto_enable.sh
DISABLE=/mnt/app/root/altscreen-u2/scripts/direct_ts_auto_disable.sh

usage(){
  echo "usage: $0 status|on|off|temp {on|off}|persist {on|off}|clear-temp|clear-persist|apply"
  echo "bare on/off writes a temporary override"
  exit 2
}
val(){ case "$1" in on|1) echo 1 ;; off|0) echo 0 ;; *) usage ;; esac; }
effective(){ runtime_cfg_bool "$NAME" 1; }
status(){
  echo "=== AUTO-DIRECT CONTROL ==="
  echo "default=1"
  echo "effective=$(effective)"
  echo "source=$(runtime_cfg_source "$NAME")"
  echo "temporary_path=$TEMP"
  echo "persistent_path=$PERSIST"
  echo "apply_class=runtime"
}
apply(){
  E=$(effective)
  if [ "$E" = 1 ]; then
    [ -x "$START" ] && "$START" || { echo "AUTO_DIRECT_CONTROL=FAIL_START_HELPER"; exit 20; }
  else
    [ -x "$STOP" ] && "$STOP" || { echo "AUTO_DIRECT_CONTROL=FAIL_STOP_HELPER"; exit 21; }
  fi
}
write_temp(){
  echo "$1" > "$TEMP.new.$$" || exit 10
  mv "$TEMP.new.$$" "$TEMP" || exit 11
}
clear_persist(){
  mount -uw /mnt/app 2>/dev/null || exit 12
  rm -f "$PERSIST" 2>/dev/null || true
  sync
  mount -ur /mnt/app 2>/dev/null || true
}
case "${1:-status}" in
  status) status ;;
  on|off)
    write_temp "$(val "$1")"
    status
    apply
    ;;
  temp)
    [ "$#" -eq 2 ] || usage
    write_temp "$(val "$2")"
    status
    apply
    ;;
  persist)
    [ "$#" -eq 2 ] || usage
    case "$2" in
      on|1) [ -x "$ENABLE" ] || exit 22; "$ENABLE" ;;
      off|0) [ -x "$DISABLE" ] || exit 23; "$DISABLE" ;;
      *) usage ;;
    esac
    status
    ;;
  clear-temp)
    rm -f "$TEMP" 2>/dev/null || true
    status
    apply
    ;;
  clear-persist)
    clear_persist
    status
    apply
    ;;
  apply) apply ;;
  *) usage ;;
esac
