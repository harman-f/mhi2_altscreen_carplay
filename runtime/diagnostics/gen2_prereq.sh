#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

MIBR_ROOT=${MIBR_ROOT:-/mnt/app/root/mibr}
STAGE=${MIBR_GEN2_STAGE:-/mnt/app/root/mibr-gen2-stage}
BIN=${MIBR_GEN2_BINARY:-$STAGE/libaltscreen111.so}
SHAFILE=${MIBR_GEN2_SHA256:-$BIN.sha256}
AIRPLAY=/mnt/app/eso/lib/libairplay.so
EXPECTED_AIRPLAY=193a4fd9101ec2aa05e7159cfa307b96500810d379ca74a194f172adc13a46b5
CFG=/mnt/system/etc/eso/production/smartphone_integrator.json
HOOK=/mnt/app/eso/lib/libmibr_carplay111.so
BACKDIR=/mnt/app/root/mibr-gen2-backup
BACKUP=$BACKDIR/libmibr_carplay111.pre-gen2.so
BACKUP_SHA=$BACKDIR/libmibr_carplay111.pre-gen2.so.sha256

find_sha(){
  for p in $MIBR_ROOT/bin/sha256sum /usr/bin/sha256sum /bin/sha256sum; do
    [ -x "$p" ] && { echo "$p"; return 0; }
  done
  command -v sha256sum 2>/dev/null && return 0
  return 1
}
SHA=$(find_sha) || { echo "GEN2_PREREQ=FAIL_NO_SHA256"; exit 2; }
hash_file(){ "$SHA" "$1" 2>/dev/null | awk '{print $1; exit}'; }

echo "=== GEN2 PREREQ ==="
echo "stage=$STAGE"
echo "binary=$BIN"

[ -r "$BIN" ] || { echo "GEN2_PREREQ=FAIL_NO_BINARY"; exit 11; }
[ -r "$SHAFILE" ] || { echo "GEN2_PREREQ=FAIL_NO_BINARY_SHA"; exit 12; }
[ -r "$AIRPLAY" ] || { echo "GEN2_PREREQ=FAIL_NO_LIBAIRPLAY"; exit 13; }
[ -r "$CFG" ] || { echo "GEN2_PREREQ=FAIL_NO_SMARTPHONE_CONFIG"; exit 14; }
[ -r "$HOOK" ] || { echo "GEN2_PREREQ=FAIL_NO_CURRENT_HOOK"; exit 15; }

EXPECTED_BIN=$(awk '{print $1; exit}' "$SHAFILE")
ACTUAL_BIN=$(hash_file "$BIN")
echo "gen2_expected_sha256=$EXPECTED_BIN"
echo "gen2_actual_sha256=$ACTUAL_BIN"
[ -n "$EXPECTED_BIN" ] && [ "$EXPECTED_BIN" = "$ACTUAL_BIN" ] || {
  echo "GEN2_PREREQ=FAIL_BINARY_HASH"
  exit 16
}

AIR_SHA=$(hash_file "$AIRPLAY")
echo "libairplay_sha256=$AIR_SHA"
[ "$AIR_SHA" = "$EXPECTED_AIRPLAY" ] || {
  echo "GEN2_PREREQ=FAIL_AIRPLAY_HASH"
  exit 17
}

grep -q "LD_PRELOAD=$HOOK" "$CFG" 2>/dev/null || {
  echo "GEN2_PREREQ=FAIL_PRELOAD_NOT_CONFIGURED"
  exit 18
}

if [ -r "$BACKUP" ]; then
  B=$(hash_file "$BACKUP")
  R=$(awk '{print $1; exit}' "$BACKUP_SHA" 2>/dev/null)
  echo "canonical_pre_gen2_backup_sha256=$B"
  [ -n "$R" ] && [ "$R" = "$B" ] || {
    echo "GEN2_PREREQ=FAIL_BACKUP_METADATA expected=$R actual=$B"
    exit 19
  }
else
  echo "pre_gen2_backup=NOT_YET_CREATED"
fi

echo "GEN2_PREREQ=PASS"
