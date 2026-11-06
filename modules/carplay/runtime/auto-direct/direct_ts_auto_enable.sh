#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
MIBR_ROOT=${MIBR_ROOT:-/mnt/app/root/mibr}
. $MIBR_ROOT/scripts/common.sh
runtime_init_durable || { echo "AUTO_DIRECT_ENABLE=FAIL_RUNTIME"; exit 3; }

DSTBASE=$MIBR_ROOT
ENABLED=$MIBR_ROOT/config/features/mibr-carplay-autodirect.enabled
PARITY_ENABLED=$MIBR_ROOT/config/features/mibr-parity-drive.enabled
PARITY_LOCK=/tmp/mibr-parity-session.lock
PARITY_SUP_PID=/tmp/mibr-parity-drive-supervisor.pid
PARITY_RUNNER=$MIBR_ROOT/bin/parity-session
LSD=/mnt/app/eso/hmi/lsd/lsd.sh
# Stage in the lsd.sh directory itself, not in /tmp (RAM): the final mv is
# then a same-filesystem rename whatever the mount layout under /mnt/app is.
TMP=/mnt/app/eso/hmi/lsd/lsd.sh.mibr-autodirect.$$
MARKER_BEGIN="# MIBR AUTO-DIRECT BEGIN"
MARKER_END="# MIBR AUTO-DIRECT END"
BOOTCMD='/bin/ksh /mnt/app/root/mibr/scripts/direct_ts_auto_start.sh >/tmp/mibr-direct-auto-boot.log 2>&1 || true'
APP_RW=0
# Integrity gate for a rewritten lsd.sh before it replaces the original:
# the J9 start-line count must be unchanged and BEGIN/END marker lines must
# form exactly WANT ordered pairs (WANT=- skips the pair check).
lsd_check(){
  awk -v b="$2" -v e="$3" -v want="$4" -v orig="$5" '
    b != "" && $0 == b { nb++; if (open) bad=1; open=1 }
    e != "" && $0 == e { ne++; if (!open) bad=1; open=0 }
    /^\$J9/ { nj++ }
    END {
      if (nj != orig || nj < 1) exit 1
      if (want != "-" && (bad || open || nb != want || ne != want)) exit 1
    }
  ' "$1"
}
j9_count(){
  awk '/^\$J9/ { n++ } END { print n+0 }' "$1"
}

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

# Last explicitly enabled mode wins. An installer upgrade that deliberately
# preserves Auto-Direct=off must NOT disturb a selected Parity mode.
# A running Parity owner is not stopped by removing its persistent marker
# alone: request its token-bound native stop, then wait for lock + supervisor
# teardown. Do not start a competing Auto-Direct owner without that evidence.
if [ "${MIBR_KEEP_MARKER_STATE:-0}" != "1" ] || [ -e "$ENABLED" ]; then
  if [ -e "$PARITY_ENABLED" ] || [ -e "$PARITY_LOCK" ] || [ -e "$PARITY_SUP_PID" ]; then
    # In an already inconsistent dual-enabled state, fail closed from now on.
    rm -f "$ENABLED" 2>/dev/null || fail 35 "autodirect_marker_clear"
    [ ! -e "$ENABLED" ] || fail 35 "autodirect_marker_still_present"
    rm -f "$PARITY_ENABLED" 2>/dev/null || fail 36 "parity_marker_clear"
    [ ! -e "$PARITY_ENABLED" ] || fail 36 "parity_marker_still_present"
    if [ -e "$PARITY_LOCK" ]; then
      [ -x "$PARITY_RUNNER" ] || fail 37 "parity_owner_missing"
      "$PARITY_RUNNER" --stop || fail 38 "parity_owner_stop_unconfirmed"
    fi
    N=0
    while [ -e "$PARITY_LOCK" ] || [ -e "$PARITY_SUP_PID" ]; do
      [ "$N" -lt 20 ] || fail 39 "parity_owner_teardown_unconfirmed"
      sleep 1
      N=$((N+1))
    done
    echo "PARITY_OWNER=QUIESCED"
  fi
fi

mkdir -p "$DSTBASE/bin" "$DSTBASE/scripts" "$DSTBASE/config/carplay" "$DSTBASE/logs" "$DSTBASE/backup" || fail 24 "dst_create"

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
      !seen && $0 ~ /^\. .*\/scripts\/common\.sh$/ {
        seen = 1
        print ". " common
        next
      }
      { print }
    ' "$SRC" > "$DST.new" || fail 27 "transform_$N"
    chmod 755 "$DST.new" 2>/dev/null || true
    mv "$DST.new" "$DST" || fail 28 "install_$N"
  done

  [ -r "$BASE/config/carplay/altscreen111.conf" ] && cp "$BASE/config/carplay/altscreen111.conf" "$DSTBASE/config/carplay/altscreen111.conf"
fi

chmod 755 "$DSTBASE/bin/direct-ts-remux" "$DSTBASE/scripts/"*.sh 2>/dev/null || true
chmod 644 "$DSTBASE/config/carplay/"* 2>/dev/null || true

if [ ! -r "$DSTBASE/backup/lsd.sh.pre-autodirect" ]; then
  cp "$LSD" "$DSTBASE/backup/lsd.sh.pre-autodirect" || fail 29 "backup_lsd"
fi

if ! grep -Fq "$MARKER_BEGIN" "$LSD" 2>/dev/null; then
  awk -v cmd="$BOOTCMD" -v begin="$MARKER_BEGIN" -v end="$MARKER_END" '
    BEGIN { done=0 }
    !done && /^\$J9/ {
      print begin
      print "if [ -e /mnt/app/root/mibr/config/features/mibr-carplay-autodirect.enabled ]; then"
      print "  " cmd
      print "fi"
      print end
      done=1
    }
    { print }
    END { if (!done) exit 42 }
  ' "$LSD" > "$TMP" || fail 30 "boot_patch"
  lsd_check "$TMP" "$MARKER_BEGIN" "$MARKER_END" 1 "$(j9_count "$LSD")" || fail 34 "boot_patch_integrity"
  chmod 755 "$TMP" 2>/dev/null || true
  mv "$TMP" "$LSD" || fail 31 "boot_install"
fi

# MIBR_KEEP_MARKER_STATE=1 (installer upgrade): refresh scripts and hook but
# keep a user's earlier "off" (marker absent).
if [ "${MIBR_KEEP_MARKER_STATE:-0}" = "1" ] && [ ! -e "$ENABLED" ]; then
  MARKER_STATE=absent_preserved
else
  touch "$ENABLED" || fail 32 "enable_marker"
  MARKER_STATE=present
fi
sync
mount -ur /mnt/app 2>/dev/null || { APP_RW=0; echo "AUTO_DIRECT_ENABLE=FAIL app_ro"; exit 33; }
APP_RW=0

if [ "${MIBR_PREPARE_ONLY:-0}" = "1" ]; then
  echo "AUTO_DIRECT_ENABLE=PREPARED"
  echo "runtime_start=SKIPPED_UNTIL_REBOOT"
  echo "boot_hook=present"
  echo "enabled_marker=$ENABLED state=$MARKER_STATE"
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
