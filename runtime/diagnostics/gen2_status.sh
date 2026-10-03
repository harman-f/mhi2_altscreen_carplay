#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

HOOK=/mnt/app/eso/lib/libmibr_carplay111.so
BACKDIR=/mnt/app/root/mibr-gen2-backup
BACKUP=$BACKDIR/libmibr_carplay111.pre-gen2.so
BACKUP_SHA=$BACKDIR/libmibr_carplay111.pre-gen2.so.sha256
INSTALLED_SHA=$BACKDIR/installed-gen2.sha256
LEGACY_BACKUP=/mnt/app/eso/lib/libmibr_carplay111.so.pre-gen2

find_sha(){
  for p in /mnt/app/root/altscreen-u2/bin/sha256sum /usr/bin/sha256sum /bin/sha256sum; do
    [ -x "$p" ] && { echo "$p"; return 0; }
  done
  return 1
}
SHA=$(find_sha 2>/dev/null)
hash_file(){ [ -n "$SHA" ] && "$SHA" "$1" 2>/dev/null | awk '{print $1; exit}'; }

echo "=== GEN2 STATUS ==="
[ -r "$HOOK" ] && echo "current_hook_sha256=$(hash_file "$HOOK")"
[ -r "$BACKUP" ] && echo "canonical_pre_gen2_backup_sha256=$(hash_file "$BACKUP")"
[ -r "$BACKUP_SHA" ] && echo "canonical_backup_recorded_sha256=$(awk '{print $1; exit}' "$BACKUP_SHA" 2>/dev/null)"
[ -r "$INSTALLED_SHA" ] && echo "installed_gen2_recorded_sha256=$(awk '{print $1; exit}' "$INSTALLED_SHA" 2>/dev/null)"
[ ! -r "$BACKUP" ] && [ -r "$LEGACY_BACKUP" ] && echo "legacy_pre_gen2_backup_sha256=$(hash_file "$LEGACY_BACKUP")"
echo

echo "--- processes ---"
pidin ar 2>/dev/null | grep -E '[s]martphone_integrator|[d]io_manager|[d]irect-ts-remux|[s]tream-player' || true
echo

echo "--- GEN2 core ---"
cat /tmp/mibr-alt111-gen2.status 2>/dev/null || echo "GEN2_CORE_STATUS=NOT_AVAILABLE"
echo

echo "--- Candidate D resync ---"
[ -r /tmp/mibr-alt111-resync.enabled ] && echo "manual_resync=enabled" || echo "manual_resync=disabled"
echo "auto_resync=OFF"
echo

echo "--- runtime configuration ---"
for helper in gen2_keyframes.sh gen2_sourceversion.sh gen2_nav_config.sh gen2_safearea.sh viewarea_mode.sh; do
  H=/mnt/app/root/altscreen-u2/scripts/$helper
  if [ -x "$H" ]; then
    "$H" status 2>/dev/null || true
    echo
  fi
done

echo "--- Stream111 ---"
[ -r /tmp/mibr-carplay111.state ] && echo "state=$(cat /tmp/mibr-carplay111.state 2>/dev/null)" || echo "state=NONE"
[ -r /tmp/mibr-carplay111.heartbeat ] && echo "heartbeat=$(cat /tmp/mibr-carplay111.heartbeat 2>/dev/null)" || echo "heartbeat=NONE"
echo

echo "--- ports ---"
netstat -an 2>/dev/null | grep -E '(:6031|:19820)' || true
echo

echo "--- recent hook log ---"
tail -120 /tmp/altscreen111.log 2>/dev/null || true
echo

if [ -x /mnt/app/root/altscreen-u2/scripts/direct_ts_auto_status.sh ]; then
  echo "--- Auto-Direct ---"
  /mnt/app/root/altscreen-u2/scripts/direct_ts_auto_status.sh 2>/dev/null || true
fi
