#!/bin/ksh
set -u

SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2

CARD=/net/mmx/fs/sda0
WORK=$CARD/esd/carplay-test
PKG=$ROOT
LOGROOT=$WORK/logs/classic111
MOUNTER=$CARD/apps/mounts
CARD_RW=0

card_ro(){
  if [ "$CARD_RW" -eq 1 ]; then
    sync 2>/dev/null || true
    mount -ur "$CARD" 2>/dev/null || true
    CARD_RW=0
  fi
}

fail(){
  echo "CLASSIC111_LOG_EXPORT=FAIL $*"
  card_ro
  exit 20
}

trap card_ro 0 1 2 15

[ -x "$MOUNTER" ] || fail "missing_mount_helper=$MOUNTER"
[ -r "$PKG/status.sh" ] || fail "missing_status_script=$PKG/status.sh"

. "$MOUNTER" -usb >/dev/null 2>&1 || fail "sd_mount_rw"
CARD_RW=1

TEST=$CARD/.mibr-classic111-write-test-$$
touch "$TEST" 2>/dev/null || fail "sd_write_test_create"
[ -f "$TEST" ] || fail "sd_write_test_verify"
rm -f "$TEST" 2>/dev/null || true

STAMP=$(/net/rcc/usr/bin/date +%Y%m%d-%H%M%S 2>/dev/null)
[ -n "$STAMP" ] || STAMP=run-$$
OUT=$LOGROOT/$STAMP

mkdir -p "$OUT" "$OUT/direct-ts" || fail "mkdir=$OUT"

ksh "$PKG/status.sh" > "$OUT/status.txt" 2>&1 || true

for SPEC in \
  "/tmp/mibr-alt111-gen2.status:gen2.status" \
  "/tmp/mibr-alt111-source-timing.status:source-timing.status" \
  "/tmp/mibr-direct-remux.status:direct-remux.status" \
  "/tmp/altscreen111.log:altscreen111.log" \
  "/tmp/mibr-alt111-runtime.log:runtime.log" \
  "/tmp/mibr-alt111-direct-ts.log:direct-ts.log" \
  "/tmp/mibr-alt111-dmdt.log:dmdt.log"
do
  SRC=${SPEC%%:*}
  NAME=${SPEC#*:}
  [ -r "$SRC" ] && cp "$SRC" "$OUT/$NAME" 2>/dev/null || true
done

for F in /tmp/mibr-alt111-run-*; do
  [ -f "$F" ] || continue
  NAME=${F##*/}
  cp "$F" "$OUT/direct-ts/$NAME" 2>/dev/null || true
done

card_ro
trap - 0 1 2 15

echo "CLASSIC111_LOG_EXPORT=PASS"
echo "path=$OUT"
