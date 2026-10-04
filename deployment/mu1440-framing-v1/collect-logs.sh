#!/bin/ksh
set -u

CARD=/net/mmx/fs/sda0
WORK=$CARD/esd/carplay-test
PKG=$WORK/classic111-framing-v1
LOGROOT=$WORK/logs/classic111
TMPROOT=/tmp/mibr-altscreen-logs
MOUNTER=$CARD/apps/mounts

fail(){
  echo "CLASSIC111_LOG_EXPORT=FAIL $*"
  exit 20
}

[ -x "$MOUNTER" ] || fail "missing_mount_helper=$MOUNTER"
[ -r "$PKG/status.sh" ] || fail "missing_status_script=$PKG/status.sh"

"$MOUNTER" -usb >/dev/null 2>&1 || fail "sd_mount_rw"

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
  "$TMPROOT/U2-LOG.txt:runtime.log"
do
  SRC=${SPEC%%:*}
  NAME=${SPEC#*:}
  [ -r "$SRC" ] && cp "$SRC" "$OUT/$NAME" 2>/dev/null || true
done

if [ -d "$TMPROOT/direct-ts" ]; then
  for F in "$TMPROOT/direct-ts/"*; do
    [ -f "$F" ] || continue
    NAME=${F##*/}
    cp "$F" "$OUT/direct-ts/$NAME" 2>/dev/null || true
  done

  for D in "$TMPROOT/direct-ts/"*; do
    [ -d "$D" ] || continue
    DNAME=${D##*/}
    mkdir -p "$OUT/direct-ts/$DNAME" 2>/dev/null || continue
    for F in "$D/"*; do
      [ -f "$F" ] || continue
      NAME=${F##*/}
      cp "$F" "$OUT/direct-ts/$DNAME/$NAME" 2>/dev/null || true
    done
  done
fi

sync
mount -ur "$CARD" 2>/dev/null || true

echo "CLASSIC111_LOG_EXPORT=PASS"
echo "path=$OUT"
