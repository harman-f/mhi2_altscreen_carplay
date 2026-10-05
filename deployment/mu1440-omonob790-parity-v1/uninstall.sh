#!/bin/ksh
set -u

DST=/mnt/app/root/altscreen-u2
HOOK=/mnt/app/eso/lib/libmibr_carplay111.so
STARTUP=/mnt/system/etc/boot/startup.sh
GUARD=/mnt/app/eso/lib/libmibr_isotx2_guard.so
BACK=/mnt/app/root/mibr-omonob790-parity-v1-backup
ACTIVE=/mnt/app/root/mibr-omonob790-parity-v1-active
STATE_AUTODIRECT=/mnt/app/root/mibr-carplay-autodirect
APP_RW=0
SYSTEM_RW=0
SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2
SHA=$ROOT/payload/sha256sum
hashf(){ set -- $("$SHA" "$1" 2>/dev/null); [ -n "${1:-}" ] || return 1; echo "$1"; }

fail(){
  echo "MIBR_OMONOB790_PARITY_UNINSTALL=FAIL $*"
  system_ro || echo "SYSTEM_MOUNT_STATE=UNCONFIRMED"
  app_ro || echo "APP_MOUNT_STATE=UNCONFIRMED"
  exit 20
}
app_rw(){ [ "$APP_RW" -eq 1 ] && return 0; mount -uw /mnt/app 2>/dev/null || return 1; APP_RW=1; }
app_ro(){ if [ "$APP_RW" -eq 1 ]; then sync; mount -ur /mnt/app 2>/dev/null || return 1; APP_RW=0; fi; }
system_ro(){ if [ "$SYSTEM_RW" -eq 1 ]; then sync; mount -ur /mnt/system 2>/dev/null || return 1; SYSTEM_RW=0; fi; }
cleanup(){ system_ro; app_ro; }
trap cleanup 0
trap 'cleanup; exit 129' 1
trap 'cleanup; exit 130' 2
trap 'cleanup; exit 143' 15

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
  echo "MIBR_OMONOB790_PARITY_UNINSTALL=NOT_ACTIVE"
  exit 0
fi
[ -d "$BACK" ] || fail "backup_dir_missing"
[ -e "$BACK/BACKUP_COMPLETE" ] || fail "backup_incomplete_refusing_automatic_restore"
[ -e "$ACTIVE" ] || echo "MIBR_OMONOB790_PARITY_UNINSTALL=RECOVERY_FROM_INTERRUPTED_INSTALL"
[ -x "$SHA" ] && [ -r "$BACK/BACKUP.sha256" ] || fail "backup_verification_missing"
while read EXPECT REL; do
  if [ "$EXPECT" = ABSENT ]; then
    [ -e "$BACK/$REL.ABSENT" ] && [ ! -e "$BACK/$REL" ] || fail "backup_absence_corrupt=$REL"
  else
    [ ! -e "$BACK/$REL.ABSENT" ] || fail "backup_conflicting_absence=$REL"
    GOT=$(hashf "$BACK/$REL") || fail "backup_hash_failed=$REL"
    [ "$GOT" = "$EXPECT" ] || fail "backup_corrupt=$REL"
  fi
done < "$BACK/BACKUP.sha256"

# A PID file is a hint, never signal authority. Stop uses an owner-generation
# ticket, then confirms writer death and backend-specific handback.
if [ -r /tmp/mibr-parity-session.pid ]; then
  [ -x "$DST/bin/parity-session" ] || fail "owner_helper_missing"
  "$DST/bin/parity-session" --stop || fail "owner_stop_unconfirmed"
fi

# A bounded explicit restore closes the ownership state even after an
# interrupted session. If the binary was not yet installed during a failed
# apply, no parity session could have taken DMDT ownership.
if [ -x "$DST/bin/parity-session" ]; then
  "$DST/bin/parity-session" --restore-stock || fail "backend_stock_restore"
fi

ksh "$ROOT/collect-logs.sh" || fail "sd_log_pre_restore"
# New GEN2 must not consume a partially restored legacy settings set, even if
# the shell dies mid-restore. This volatile barrier is cleared by normal boot.
echo "canonical_reboot_required" > /tmp/mibr-parity-rollback.pending || fail "rollback_reader_barrier"
app_rw || fail "mount_app_rw"

for SPEC in   "bin/libaltscreen111.so:$DST/bin/libaltscreen111.so:755"   "hook/libmibr_carplay111.so:$HOOK:755"   "bin/direct-ts-parity:$DST/bin/direct-ts-parity:755"   "bin/parity-session:$DST/bin/parity-session:755"   "scripts/omonob790_profile.sh:$DST/scripts/omonob790_profile.sh:755"   "scripts/omonob790_session.sh:$DST/scripts/omonob790_session.sh:755"   "scripts/omonob790_status.sh:$DST/scripts/omonob790_status.sh:755"   "scripts/gen2_compat_profile.sh:$DST/scripts/gen2_compat_profile.sh:755"   "state/mibr-carplay-autodirect:$STATE_AUTODIRECT:644"
do
  REL=${SPEC%%:*}
  REST=${SPEC#*:}
  DSTF=${REST%%:*}
  MODE=${REST#*:}
  restore_one "$REL" "$DSTF" "$MODE"
done
restore_one "guard/libmibr_isotx2_guard.so" "$GUARD" 755
restore_one "bin/alt111-settings" "$DST/bin/alt111-settings" 755
mount -uw /mnt/system 2>/dev/null || fail "mount_system_rw"
SYSTEM_RW=1
restore_one "boot/startup.sh" "$STARTUP" 755
system_ro || fail "mount_system_ro"
while read EXPECT REL; do
  case "$REL" in
    temp/*) restore_one "$REL" "/tmp/${REL#temp/}" 644 ;;
    scripts/*) restore_one "$REL" "$DST/$REL" 755 ;;
  esac
done < "$BACK/BACKUP.sha256"

while read EXPECT REL; do
  case "$REL" in
    hook/*) LIVE=$HOOK ;;
    state/*) LIVE=$STATE_AUTODIRECT ;;
    guard/*) LIVE=$GUARD ;;
    boot/*) LIVE=$STARTUP ;;
    temp/*) LIVE=/tmp/${REL#temp/} ;;
    *) LIVE=$DST/$REL ;;
  esac
  if [ "$EXPECT" = ABSENT ]; then
    [ ! -e "$LIVE" ] || fail "restored_absence_failed=$REL"
  else
    GOT=$(hashf "$LIVE") || fail "restored_hash_failed=$REL"
    [ "$GOT" = "$EXPECT" ] || fail "restored_hash_mismatch=$REL"
  fi
done < "$BACK/BACKUP.sha256"
rm -f "$ACTIVE" 2>/dev/null || fail "active_marker_remove"
# Retain verified backups and restoration evidence. A later install refuses
# this directory until a separately reviewed retirement/archival action.
echo "RESTORE_VERIFIED=YES" > "$BACK/RESTORE_VERIFIED" || fail "restore_verification_marker"
app_ro || fail "mount_app_ro"

# Keep the legacy Auto-Direct path suppressed only until the required reboot.
# /tmp is volatile; after reboot the byte-for-byte restored persistent setting
# regains control.
echo 0 > /tmp/mibr-carplay-autodirect 2>/dev/null || true

rm -f /tmp/mibr-alt111-au-framing.enabled /tmp/mibr-parity-session.pid /tmp/mibr-parity-session-bridge.pid 2>/dev/null || true

echo "MIBR_OMONOB790_PARITY_UNINSTALL=PASS"
echo "REBOOT_REQUIRED=YES"
