#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
# Install/enable the guarded parity-drive boot hook. Does not restart stock apps.

set -u
BASE=/mnt/app/root/altscreen-u2
SUP=$BASE/scripts/parity_drive_supervisor.sh
RUNNER=$BASE/bin/parity-session
BRIDGE=$BASE/bin/direct-ts-parity
LSD=/mnt/app/eso/hmi/lsd/lsd.sh
ENABLE=/mnt/app/root/mibr-parity-drive.enabled
AUTODIRECT_ENABLED=/mnt/app/root/mibr-carplay-autodirect.enabled
# Staged beside lsd.sh so the final mv is a same-filesystem rename.
TMP=/mnt/app/eso/hmi/lsd/lsd.sh.mibr-parity-drive.$$
BEGIN="# MIBR PARITY-DRIVE BEGIN"
END="# MIBR PARITY-DRIVE END"
BOOTCMD='/bin/ksh /mnt/app/root/altscreen-u2/scripts/parity_drive_supervisor.sh >/tmp/mibr-parity-drive-boot.log 2>&1 &'
RW=0
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
  echo "PARITY_DRIVE_ENABLE=FAIL $*"
  rm -f "$TMP" 2>/dev/null || true
  if [ "$RW" -eq 1 ]; then sync; mount -ur /mnt/app 2>/dev/null || true; fi
  exit "$RC"
}

[ -x "$SUP" ] || fail 10 "supervisor_missing"
[ -x "$RUNNER" ] || fail 11 "session_missing"
[ -x "$BRIDGE" ] || fail 12 "bridge_missing"
[ -r "$LSD" ] || fail 13 "lsd_missing"

mount -uw /mnt/app 2>/dev/null || fail 20 "app_rw"
RW=1

# The legacy Auto-Direct supervisor and parity-session are mutually exclusive.
# Its lsd.sh hook starts only while the .enabled marker exists, so remove that
# marker (the hook itself stays inert and is left in place).
rm -f "$AUTODIRECT_ENABLED" 2>/dev/null
[ ! -e "$AUTODIRECT_ENABLED" ] || fail 29 "autodirect_marker_remove"

if [ ! -r "$BASE/backup/lsd.sh.pre-parity-drive" ]; then
  mkdir -p "$BASE/backup" || fail 22 "backup_dir"
  cp "$LSD" "$BASE/backup/lsd.sh.pre-parity-drive" || fail 23 "backup_lsd"
fi

if grep -Fq "$BEGIN" "$LSD" 2>/dev/null; then
  awk -v cmd="$BOOTCMD" -v begin="$BEGIN" -v end="$END" '
    BEGIN { skip=0; done=0 }
    $0 == begin { print begin; print cmd; skip=1; done=1; next }
    skip { if ($0 == end) { print end; skip=0 }; next }
    { print }
    END { if (!done || skip) exit 42 }
  ' "$LSD" > "$TMP" || fail 24 "boot_patch_replace"
else
  awk -v cmd="$BOOTCMD" -v begin="$BEGIN" -v end="$END" '
    BEGIN { done=0 }
    !done && /^\$J9/ { print begin; print cmd; print end; done=1 }
    { print }
    END { if (!done) exit 42 }
  ' "$LSD" > "$TMP" || fail 24 "boot_patch_insert"
fi

lsd_check "$TMP" "$BEGIN" "$END" 1 "$(j9_count "$LSD")" || fail 27 "boot_patch_integrity"
chmod 755 "$TMP" 2>/dev/null || true
mv "$TMP" "$LSD" || fail 25 "boot_install"

echo 1 > "$ENABLE" || fail 26 "enable_write"
chmod 644 "$ENABLE" 2>/dev/null || true
sync
mount -ur /mnt/app 2>/dev/null || { RW=0; echo "PARITY_DRIVE_ENABLE=FAIL app_ro"; exit 28; }
RW=0

echo "PARITY_DRIVE_ENABLE=PASS"
echo "boot_hook=present"
echo "parity_drive_enabled=1"
echo "legacy_autodirect_persistent=0"
echo "next_boot_autostart=YES"

if [ "${MIBR_PREPARE_ONLY:-0}" = "1" ]; then
  echo "runtime_start=SKIPPED"
  exit 0
fi

if pidin ar 2>/dev/null | grep -F 'parity_drive_supervisor.sh' | grep -v grep >/dev/null 2>&1; then
  echo "runtime_start=ALREADY_RUNNING"
  exit 0
fi

if on -d -f mmx /bin/ksh "$SUP" >/tmp/mibr-parity-drive-launch.log 2>&1; then
  echo "runtime_start=REQUESTED"
else
  echo "PARITY_DRIVE_ENABLE=WARN_START_FAILED_BOOT_AUTOSTART_STILL_ENABLED"
fi
exit 0
