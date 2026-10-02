#!/bin/ksh
set -u

DST=/mnt/app/root/altscreen-u2
HOOK=/mnt/app/eso/lib/libmibr_carplay111.so
BACK=/mnt/app/root/mibr-framing-v1-backup
ACTIVE=/mnt/app/root/mibr-framing-v1-active
STATE_SOURCE=/mnt/app/root/mibr-direct-source-framing
STATE_DIRECT_FPS=/mnt/app/root/mibr-direct-output-fps
STATE_SOURCE_FPS=/mnt/app/root/mibr-carplay111-fps
STATE_SAFEAREA=/mnt/app/root/mibr-carplay111-safearea.conf
APP_RW=0

fail(){
  echo "MIBR_FRAMING_V1_UNINSTALL=FAIL $*"
  if [ "$APP_RW" -eq 1 ]; then
    sync 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    APP_RW=0
  fi
  exit 20
}
app_rw(){ [ "$APP_RW" -eq 1 ] && return 0; mount -uw /mnt/app 2>/dev/null || return 1; APP_RW=1; }
app_ro(){ if [ "$APP_RW" -eq 1 ]; then sync 2>/dev/null || true; mount -ur /mnt/app 2>/dev/null || true; APP_RW=0; fi; }
trap app_ro 0 1 2 15

restore_one(){
  REL=$1
  DSTF=$2
  MODE=${3:-755}
  SRC=$BACK/$REL
  if [ -e "$SRC.ABSENT" ]; then
    rm -f "$DSTF" 2>/dev/null || fail "remove_added=$DSTF"
    return 0
  fi
  [ -r "$SRC" ] || fail "backup_missing=$SRC"
  cp "$SRC" "$DSTF.new.$$" || fail "restore_copy=$REL"
  chmod "$MODE" "$DSTF.new.$$" 2>/dev/null || true
  mv "$DSTF.new.$$" "$DSTF" || fail "restore_replace=$DSTF"
}

if [ ! -e "$ACTIVE" ] && [ ! -e "$BACK/BACKUP_COMPLETE" ]; then
  echo "MIBR_FRAMING_V1_UNINSTALL=NOT_ACTIVE"
  exit 0
fi
[ -d "$BACK" ] || fail "backup_dir_missing"
[ -e "$BACK/BACKUP_COMPLETE" ] || fail "backup_incomplete_refusing_automatic_restore"
[ -e "$ACTIVE" ] || echo "MIBR_FRAMING_V1_UNINSTALL=RECOVERY_FROM_INTERRUPTED_INSTALL"

if [ -x "$DST/scripts/direct_ts_auto_stop.sh" ]; then
  "$DST/scripts/direct_ts_auto_stop.sh" >/dev/null 2>&1 || true
fi

app_rw || fail "mount_app_rw"
restore_one bin/libaltscreen111.so "$DST/bin/libaltscreen111.so"
restore_one bin/direct-ts-remux "$DST/bin/direct-ts-remux"
restore_one hook/libmibr_carplay111.so "$HOOK"
restore_one scripts/common.sh "$DST/scripts/common.sh"
restore_one scripts/direct_fps.sh "$DST/scripts/direct_fps.sh"
restore_one scripts/direct_ts_auto_supervisor.sh "$DST/scripts/direct_ts_auto_supervisor.sh"
restore_one scripts/direct_ts_auto_status.sh "$DST/scripts/direct_ts_auto_status.sh"
restore_one scripts/direct_source_mode.sh "$DST/scripts/direct_source_mode.sh"
restore_one scripts/gen2_safearea.sh "$DST/scripts/gen2_safearea.sh"
restore_one state/mibr-direct-source-framing "$STATE_SOURCE" 644
restore_one state/mibr-direct-output-fps "$STATE_DIRECT_FPS" 644
restore_one state/mibr-carplay111-fps "$STATE_SOURCE_FPS" 644
restore_one state/mibr-carplay111-safearea.conf "$STATE_SAFEAREA" 644
rm -f "$ACTIVE" 2>/dev/null || true
app_ro

echo "MIBR_FRAMING_V1_UNINSTALL=PASS"
echo "backup_retained=$BACK"
echo "REBOOT_REQUIRED=YES"
