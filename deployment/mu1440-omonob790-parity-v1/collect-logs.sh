#!/bin/ksh
set -u

SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2

CARD=/net/mmx/fs/sda0
WORK=$CARD/esd/carplay-test
PKG=$ROOT
LOGROOT=$WORK/logs/omonob790-parity
MOUNTER=$CARD/apps/mounts
CARD_RW=0

card_ro(){
  if [ "$CARD_RW" -eq 1 ] && [ "${MIBR_LOG_ACTIVE:-0}" != 1 ]; then
    sync 2>/dev/null || true
    mount -ur "$CARD" 2>/dev/null || return 1
    CARD_RW=0
  fi
}
fail(){
  echo "OMONOB790_PARITY_LOG_EXPORT=FAIL $*"
  card_ro
  exit 20
}
trap card_ro 0
trap 'card_ro; exit 129' 1
trap 'card_ro; exit 130' 2
trap 'card_ro; exit 143' 15

[ -x "$MOUNTER" ] || fail "missing_mount_helper=$MOUNTER"
[ -r "$PKG/status.sh" ] || fail "missing_status_script=$PKG/status.sh"

. "$MOUNTER" -usb >/dev/null 2>&1 || fail "sd_mount_rw"
CARD_RW=1

TEST=$CARD/.mibr-omonob790-parity-write-test-$$
touch "$TEST" 2>/dev/null || fail "sd_write_test_create"
[ -f "$TEST" ] || fail "sd_write_test_verify"
rm -f "$TEST" 2>/dev/null || fail "sd_write_test_remove"

STAMP=$(/net/rcc/usr/bin/date +%Y%m%d-%H%M%S 2>/dev/null)
[ -n "$STAMP" ] || STAMP=run-$$
OUT=$LOGROOT/$STAMP
mkdir -p "$OUT" || fail "mkdir=$OUT"

ksh "$PKG/status.sh" > "$OUT/status.txt" 2>&1 || true
for F in /tmp/mibr-parity-session.backend /tmp/mibr-parity-session.ticket /tmp/mibr-alt111-native-gate.status /tmp/mibr-alt111-gen2.status /tmp/mibr-parity-rollback.pending; do
  [ ! -r "$F" ] || cp "$F" "$OUT/" || fail "copy_runtime_status=$F"
done

for SPEC in   "/tmp/mibr-parity-ts.status:parity-ts.status"   "/tmp/mibr-parity-session.state:parity-session.state"   "/tmp/mibr-parity-session.pid:parity-session.pid"   "/tmp/mibr-parity-session-bridge.pid:parity-session-bridge.pid"   "/tmp/mibr-alt111-gen2.status:gen2.status"   "/tmp/mibr-alt111-source-timing.status:source-timing.status"   "/tmp/mibr-carplay111.state:stream111.state"   "/tmp/mibr-carplay111.heartbeat:stream111.heartbeat"   "/tmp/altscreen111.log:altscreen111.log"
do
  SRC=${SPEC%%:*}
  NAME=${SPEC#*:}
  [ -r "$SRC" ] && cp "$SRC" "$OUT/$NAME" 2>/dev/null || true
done

card_ro || fail "sd_mount_ro"
trap - 0 1 2 15

echo "OMONOB790_PARITY_LOG_EXPORT=PASS"
echo "path=$OUT"
