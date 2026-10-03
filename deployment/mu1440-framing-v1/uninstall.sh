#!/bin/ksh
set -u

DST=/mnt/app/root/altscreen-u2
HOOK=/mnt/app/eso/lib/libmibr_carplay111.so
LSD=/mnt/app/eso/hmi/lsd/lsd.sh
BACK=/mnt/app/root/mibr-framing-v1-backup
ACTIVE=/mnt/app/root/mibr-framing-v1-active
APP_RW=0

STATE_ENABLED=/mnt/app/root/mibr-carplay111-enabled
STATE_AUTODIRECT=/mnt/app/root/mibr-carplay-autodirect
STATE_AUTODIRECT_LEGACY=/mnt/app/root/mibr-carplay-autodirect.enabled
STATE_FPS=/mnt/app/root/mibr-carplay111-fps
STATE_FRAMING=/mnt/app/root/mibr-carplay111-framing
STATE_VIDEO=/mnt/app/root/mibr-carplay111-video.conf
STATE_KEYFRAMES=/mnt/app/root/mibr-carplay111-keyframes.conf
STATE_SOURCEVERSION=/mnt/app/root/mibr-carplay111-sourceversion
STATE_URL=/mnt/app/root/mibr-carplay111-url
STATE_UIURLS=/mnt/app/root/mibr-carplay111-ui-urls.conf
STATE_NAV=/mnt/app/root/mibr-carplay111-nav.conf
STATE_DISPLAY=/mnt/app/root/mibr-carplay111-display.conf
STATE_VIEWAREAS=/mnt/app/root/mibr-carplay111-viewareas.conf
LEGACY_VIEWAREAS=/mnt/app/root/mibr-carplay111-viewareas
LEGACY_SAFEAREA=/mnt/app/root/mibr-carplay111-safearea.conf
LEGACY_NAV_QUERY=/mnt/app/root/mibr-carplay111-nav-query

fail(){
  echo "MIBR_CLASSIC111_UNINSTALL=FAIL $*"
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
  echo "MIBR_CLASSIC111_UNINSTALL=NOT_ACTIVE"
  exit 0
fi
[ -d "$BACK" ] || fail "backup_dir_missing"
[ -e "$BACK/BACKUP_COMPLETE" ] || fail "backup_incomplete_refusing_automatic_restore"
[ -e "$ACTIVE" ] || echo "MIBR_CLASSIC111_UNINSTALL=RECOVERY_FROM_INTERRUPTED_INSTALL"

if [ -x "$DST/scripts/direct_ts_auto_stop.sh" ]; then
  "$DST/scripts/direct_ts_auto_stop.sh" >/dev/null 2>&1 || true
fi

app_rw || fail "mount_app_rw"

for SPEC in   "bin/libaltscreen111.so:$DST/bin/libaltscreen111.so:755"   "bin/direct-ts-remux:$DST/bin/direct-ts-remux:755"   "hook/libmibr_carplay111.so:$HOOK:755"   "scripts/common.sh:$DST/scripts/common.sh:755"   "scripts/direct_fps.sh:$DST/scripts/direct_fps.sh:755"   "scripts/direct_source_mode.sh:$DST/scripts/direct_source_mode.sh:755"   "scripts/gen2_video.sh:$DST/scripts/gen2_video.sh:755"   "scripts/direct_ts_auto_supervisor.sh:$DST/scripts/direct_ts_auto_supervisor.sh:755"   "scripts/direct_ts_auto_status.sh:$DST/scripts/direct_ts_auto_status.sh:755"   "scripts/direct_ts_auto_start.sh:$DST/scripts/direct_ts_auto_start.sh:755"   "scripts/direct_ts_auto_watchdog.sh:$DST/scripts/direct_ts_auto_watchdog.sh:755"   "scripts/direct_ts_auto_enable.sh:$DST/scripts/direct_ts_auto_enable.sh:755"   "scripts/direct_ts_auto_disable.sh:$DST/scripts/direct_ts_auto_disable.sh:755"   "scripts/gen2_nav_config.sh:$DST/scripts/gen2_nav_config.sh:755"   "scripts/gen2_url.sh:$DST/scripts/gen2_url.sh:755"   "scripts/gen2_ui_urls.sh:$DST/scripts/gen2_ui_urls.sh:755"   "scripts/gen2_viewareas.sh:$DST/scripts/gen2_viewareas.sh:755"   "scripts/gen2_safearea.sh:$DST/scripts/gen2_safearea.sh:755"   "scripts/gen2_keyframes.sh:$DST/scripts/gen2_keyframes.sh:755"   "scripts/gen2_sourceversion.sh:$DST/scripts/gen2_sourceversion.sh:755"   "scripts/gen2_display.sh:$DST/scripts/gen2_display.sh:755"   "scripts/gen2_enabled.sh:$DST/scripts/gen2_enabled.sh:755"   "scripts/viewarea_mode.sh:$DST/scripts/viewarea_mode.sh:755"   "system/lsd.sh:$LSD:755"   "state/mibr-carplay111-enabled:$STATE_ENABLED:644"   "state/mibr-carplay-autodirect:$STATE_AUTODIRECT:644"   "state/mibr-carplay-autodirect.enabled:$STATE_AUTODIRECT_LEGACY:644"   "state/mibr-carplay111-fps:$STATE_FPS:644"   "state/mibr-carplay111-framing:$STATE_FRAMING:644"   "state/mibr-carplay111-video.conf:$STATE_VIDEO:644"   "state/mibr-carplay111-keyframes.conf:$STATE_KEYFRAMES:644"   "state/mibr-carplay111-sourceversion:$STATE_SOURCEVERSION:644"   "state/mibr-carplay111-url:$STATE_URL:644"   "state/mibr-carplay111-ui-urls.conf:$STATE_UIURLS:644"   "state/mibr-carplay111-nav.conf:$STATE_NAV:644"   "state/mibr-carplay111-display.conf:$STATE_DISPLAY:644"   "state/mibr-carplay111-viewareas.conf:$STATE_VIEWAREAS:644"   "legacy/mibr-carplay111-viewareas:$LEGACY_VIEWAREAS:644"   "legacy/mibr-carplay111-safearea.conf:$LEGACY_SAFEAREA:644"   "legacy/mibr-carplay111-nav-query:$LEGACY_NAV_QUERY:644"
do
  REL=${SPEC%%:*}
  REST=${SPEC#*:}
  DSTF=${REST%%:*}
  MODE=${REST#*:}
  restore_one "$REL" "$DSTF" "$MODE"
done

# Candidate-only volatile controls must not leak into the restored runtime.
rm -f   /tmp/mibr-carplay111-enabled   /tmp/mibr-carplay111-fps   /tmp/mibr-carplay111-framing   /tmp/mibr-carplay111-video.conf   /tmp/mibr-carplay111-keyframes.conf   /tmp/mibr-carplay111-sourceversion   /tmp/mibr-carplay111-url   /tmp/mibr-carplay111-ui-urls.conf   /tmp/mibr-carplay111-nav.conf   /tmp/mibr-carplay111-display.conf   /tmp/mibr-carplay111-viewareas.conf   /tmp/mibr-alt111-viewarea-request   2>/dev/null || true

rm -f "$ACTIVE" 2>/dev/null || true
rm -rf "$BACK" 2>/dev/null || true
app_ro

echo "MIBR_CLASSIC111_UNINSTALL=PASS"
echo "REBOOT_REQUIRED=YES"
