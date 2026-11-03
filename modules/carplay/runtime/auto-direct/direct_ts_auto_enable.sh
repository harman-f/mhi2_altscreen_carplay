#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init_durable || { echo "AUTO_DIRECT_ENABLE=FAIL_RUNTIME"; exit 3; }

DSTBASE=/mnt/app/root/altscreen-u2
ENABLED=/mnt/app/root/mibr-carplay-autodirect.enabled
LSD=/mnt/app/eso/hmi/lsd/lsd.sh
TMP=/tmp/lsd.sh.mibr-autodirect.$$
MARKER_BEGIN="# MIBR AUTO-DIRECT BEGIN"
MARKER_END="# MIBR AUTO-DIRECT END"
BOOTCMD='/bin/ksh /mnt/app/root/altscreen-u2/scripts/direct_ts_auto_start.sh >/tmp/mibr-direct-auto-boot.log 2>&1 || true'
APP_RW=0

fail(){
  RC=$1
  shift
  echo "AUTO_DIRECT_ENABLE=FAIL $*"
  rm -f "$TMP" 2>/dev/null || true
  if [ "$APP_RW" -eq 1 ]; then
    sync
    mount -ur /mnt/app 2>/dev/null || true
  fi
  exit "$RC"
}

[ -r "$LSD" ] || fail 20 "lsd_missing"
[ -x "$BASE/bin/direct-ts-remux" ] || fail 21 "source_bridge_missing"
[ -r "$DSTBASE/scripts/common.sh" ] || fail 22 "internal_u2_common_missing"

mount -uw /mnt/app 2>/dev/null || fail 23 "app_rw"
APP_RW=1
mkdir -p "$DSTBASE/bin" "$DSTBASE/scripts" "$DSTBASE/config" "$DSTBASE/logs" "$DSTBASE/backup" || fail 24 "dst_create"

if [ "$BASE" != "$DSTBASE" ]; then
  cp "$BASE/bin/direct-ts-remux" "$DSTBASE/bin/direct-ts-remux" || fail 25 "copy_bridge"

  # The SD-only build rewrites each script's own common.sh import to the SD
  # path. When staging those scripts internally we must reverse only that first
  # import without embedding a literal internal import string that the package
  # rewriter could itself rewrite.
  for N in writev_gate.sh direct_ts_auto_supervisor.sh direct_ts_auto_watchdog.sh direct_ts_auto_start.sh direct_ts_auto_stop.sh direct_ts_auto_status.sh direct_ts_auto_enable.sh direct_ts_auto_disable.sh; do
    SRC="$BASE/scripts/$N"
    DST="$DSTBASE/scripts/$N"
    [ -r "$SRC" ] || fail 26 "missing_source_$N"
    awk -v common="$DSTBASE/scripts/common.sh" '
      NR == 2 && $0 ~ /^\. .*\/scripts\/common\.sh$/ {
        print ". " common
        next
      }
      { print }
    ' "$SRC" > "$DST.new" || fail 27 "transform_$N"
    chmod 755 "$DST.new" 2>/dev/null || true
    mv "$DST.new" "$DST" || fail 28 "install_$N"
  done

  [ -r "$BASE/config/altscreen111.conf" ] && cp "$BASE/config/altscreen111.conf" "$DSTBASE/config/altscreen111.conf"
fi

chmod 755 "$DSTBASE/bin/direct-ts-remux" "$DSTBASE/scripts/"*.sh 2>/dev/null || true
chmod 644 "$DSTBASE/config/"* 2>/dev/null || true

if [ ! -r "$DSTBASE/backup/lsd.sh.pre-autodirect" ]; then
  cp "$LSD" "$DSTBASE/backup/lsd.sh.pre-autodirect" || fail 29 "backup_lsd"
fi

if ! grep -Fq "$MARKER_BEGIN" "$LSD" 2>/dev/null; then
  awk -v cmd="$BOOTCMD" -v begin="$MARKER_BEGIN" -v end="$MARKER_END" '
    BEGIN { done=0 }
    !done && /^\$J9/ {
      print begin
      print "if [ -e /mnt/app/root/mibr-carplay-autodirect.enabled ]; then"
      print "  " cmd
      print "fi"
      print end
      done=1
    }
    { print }
    END { if (!done) exit 42 }
  ' "$LSD" > "$TMP" || fail 30 "boot_patch"
  chmod 755 "$TMP" 2>/dev/null || true
  mv "$TMP" "$LSD" || fail 31 "boot_install"
fi

touch "$ENABLED" || fail 32 "enable_marker"
sync
mount -ur /mnt/app 2>/dev/null || true
APP_RW=0

if [ "${MIBR_PREPARE_ONLY:-0}" = "1" ]; then
  echo "AUTO_DIRECT_ENABLE=PREPARED"
  echo "runtime_start=SKIPPED_UNTIL_REBOOT"
  echo "boot_hook=present"
  echo "enabled_marker=$ENABLED"
  exit 0
fi

"$DSTBASE/scripts/direct_ts_auto_start.sh"
RC=$?
if [ "$RC" -eq 0 ]; then
  echo "AUTO_DIRECT_ENABLE=PASS"
else
  echo "AUTO_DIRECT_ENABLE=PREPARED_START_RC_$RC"
fi
echo "boot_hook=present"
echo "enabled_marker=$ENABLED"
exit 0
