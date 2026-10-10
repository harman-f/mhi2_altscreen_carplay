#!/bin/ksh
# Strict paired offline QNX poll research swap, CI314 (or CI295/CI305) to experimental.
# No boot hooks, no stock process control, no unknown binary pair accepted.
set -u
export PATH=/proc/boot:/bin:/usr/bin:/sbin:/usr/sbin:/mnt/app/armle/bin:/mnt/app/armle/usr/bin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1
MODE=${1:-status}
SD=/net/mmx/fs/sda0/esd/carplay-test/omonob-clock-test/pollwait-v1
DST=/mnt/app/root/altscreen-u2/bin
BACK=/mnt/app/root/mibr-pollwait-v1-backup
SHA=$DST/sha256sum
NEW_B=__NEW_BRIDGE_HASH__
NEW_O=__NEW_OWNER_HASH__
CI314_B=74c39c205bdab2f5e894cf35e644bf7d9fe9c9b46dc71a27e26bb5c2b237f3e2
CI314_O=c513ca1f7fb52df2d6ebb4e65b7bddc7b0aa3c1e455a2d1d614c63972794e370
CI295_B=a6f9e64d807c8ebb827634eb7b1e0421f8b0961329a76bee3a2ad361bf4fad3b
CI295_O=a0422a36f245b3dd5a4dd88a6bc930ba007c8993489a2ee402b6b33e72c820c7
CI305_B=7fa78266b2df3106e1e6372c8873cdfca4d318999262e82b35291bb7ca8a0b8b
CI305_O=441cd1436a94e0a7f4f5f76820646c7f3195984ff1036771b909b6af3f2aaca7
RW=0
ALTERED=0
COMMITTED=0
BASE_B=
BASE_O=
hashfile(){ "$SHA" "$1" 2>/dev/null | awk '{print $1}'; }
fail(){ echo "POLL_SWAP=FAIL reason=$1"; exit 1; }
checkidle(){
  [ ! -e /tmp/mibr-parity-session.lock ] || fail owner_lock
  [ ! -e /tmp/mibr-isotx2-gate.direct ] || fail gate_request
  for PID in /tmp/mibr-parity-session.pid /tmp/mibr-parity-session-bridge.pid /tmp/mibr-parity-session-watchdog.pid /tmp/mibr-parity-drive-supervisor.pid; do
    [ ! -e "$PID" ] || fail runtime_pid
  done
  [ "$(cat /mnt/app/root/mibr-parity-drive.enabled 2>/dev/null)" != 1 ] || fail autostart_enabled
  case "$(cat /tmp/mibr-alt111-native-gate.status 2>/dev/null)" in 'M1GATE1 0 '*) : ;; *) fail gate_not_stock ;; esac
  PROCS=$(pidin ar 2>/dev/null) || fail pidin_unavailable
  if echo "$PROCS" | grep -E '(^|[/[:space:]])(direct-ts-parity|parity-session|parity_drive_supervisor\\.sh)([[:space:]]|$)' >/dev/null 2>&1; then
    fail parity_running
  fi
  echo POLL_SWAP=IDLE_PASS
}
recover(){
  [ -n "$BASE_B" ] && [ -n "$BASE_O" ] || return 0
  cp "$BACK/direct-ts-parity" "$DST/direct-ts-parity" 2>/dev/null || true
  cp "$BACK/parity-session" "$DST/parity-session" 2>/dev/null || true
  chmod 755 "$DST/direct-ts-parity" "$DST/parity-session" 2>/dev/null || true
  if [ "$(hashfile "$DST/direct-ts-parity")" = "$BASE_B" ] &&
     [ "$(hashfile "$DST/parity-session")" = "$BASE_O" ]; then
    echo POLL_SWAP=AUTORESTORE_PASS
  else
    echo POLL_SWAP=AUTORESTORE_FAILED_MANUAL_ACTION_REQUIRED
  fi
}
cleanup(){
  RC=$?
  trap - 0 1 2 15
  if [ "$RW" -eq 1 ]; then
    rm -f "$DST/direct-ts-parity.clockdiag-staged" "$DST/parity-session.clockdiag-staged"
    [ "$ALTERED" -eq 0 ] || [ "$COMMITTED" -eq 1 ] || recover
    sync 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || { echo POLL_SWAP=APP_MOUNT_RO_FAIL; RC=3; }
  fi
  exit "$RC"
}
trap cleanup 0
trap 'exit 130' 1 2 15
[ -x "$SHA" ] || fail sha_helper_missing
case "$MODE" in
  live|fixture|status|stop)
    if [ "$MODE" = fixture ]; then
      exec /bin/ksh "$SD/MU1440_POLL_FIXTURE.sh" start
    fi
    if [ "$MODE" = live ]; then
      exec /bin/ksh "$SD/MU1440_POLL_LIVE.sh" start
    fi
    if [ "$MODE" = status ]; then
      echo ===CLOCKDIAG===
      echo "bridge=$(hashfile "$DST/direct-ts-parity")"
      echo "owner=$(hashfile "$DST/parity-session")"
      [ -r /tmp/mibr-parity-session.state ] && cat /tmp/mibr-parity-session.state
      [ -r /tmp/mibr-alt111-native-gate.status ] && cat /tmp/mibr-alt111-native-gate.status
      [ -r /tmp/mibr-parity-ts.status ] && grep -E '^(state|diag_[^=]*|input_records|output_aus_completed|write_errors|pts_pcr_lead_ms)=' /tmp/mibr-parity-ts.status
      exit 0
    fi
    exec "$DST/parity-session" --stop ;;
  verify)
    [ "$(hashfile "$DST/direct-ts-parity")" = "$NEW_B" ] &&
    [ "$(hashfile "$DST/parity-session")" = "$NEW_O" ] || fail new_pair_mismatch
    echo POLL_SWAP=VERIFY_PASS
    exit 0 ;;
  install|restore) : ;;
  *) echo 'usage: install|verify|live|fixture|status|stop|restore'; exit 2 ;;
esac
CUR_B=$(hashfile "$DST/direct-ts-parity")
CUR_O=$(hashfile "$DST/parity-session")
if [ "$MODE" = install ]; then
  [ "$(hashfile "$SD/direct-ts-parity")" = "$NEW_B" ] &&
  [ "$(hashfile "$SD/parity-session")" = "$NEW_O" ] || fail sd_pair_bad
  if [ "$CUR_B" = "$NEW_B" ] && [ "$CUR_O" = "$NEW_O" ]; then
    echo POLL_SWAP=ALREADY_INSTALLED; exit 0
  fi
  if [ "$CUR_B" = "$CI295_B" ] && [ "$CUR_O" = "$CI295_O" ]; then
    BASE_B=$CI295_B;BASE_O=$CI295_O
  elif [ "$CUR_B" = "$CI305_B" ] && [ "$CUR_O" = "$CI305_O" ]; then
    BASE_B=$CI305_B;BASE_O=$CI305_O
  elif [ "$CUR_B" = "$CI314_B" ] && [ "$CUR_O" = "$CI314_O" ]; then
    BASE_B=$CI314_B;BASE_O=$CI314_O
  else fail current_pair_not_qualified
  fi
  if [ -e "$BACK/original.sha256" ]; then
    [ "$(awk '$2=="direct-ts-parity"{print $1}' "$BACK/original.sha256")" = "$BASE_B" ] &&
    [ "$(awk '$2=="parity-session"{print $1}' "$BACK/original.sha256")" = "$BASE_O" ] || fail existing_backup_conflict
  fi
else
  if [ "$CUR_B" = "$CI295_B" ] && [ "$CUR_O" = "$CI295_O" ]; then
    echo POLL_SWAP=ALREADY_CI295;exit 0
  fi
  if [ "$CUR_B" = "$CI305_B" ] && [ "$CUR_O" = "$CI305_O" ]; then
    echo POLL_SWAP=ALREADY_CI305;exit 0
  fi
  if [ "$CUR_B" = "$CI314_B" ] && [ "$CUR_O" = "$CI314_O" ]; then
    echo POLL_SWAP=ALREADY_CI314;exit 0
  fi
  [ "$CUR_B" = "$NEW_B" ] && [ "$CUR_O" = "$NEW_O" ] || fail not_diag_pair
  [ -r "$BACK/original.sha256" ] || fail backup_missing
  BASE_B=$(awk '$2=="direct-ts-parity"{print $1}' "$BACK/original.sha256")
  BASE_O=$(awk '$2=="parity-session"{print $1}' "$BACK/original.sha256")
  if [ "$BASE_B" = "$CI295_B" ] && [ "$BASE_O" = "$CI295_O" ]; then :
  elif [ "$BASE_B" = "$CI305_B" ] && [ "$BASE_O" = "$CI305_O" ]; then :
  elif [ "$BASE_B" = "$CI314_B" ] && [ "$BASE_O" = "$CI314_O" ]; then :
  else fail backup_pair_unqualified
  fi
  [ "$(hashfile "$BACK/direct-ts-parity")" = "$BASE_B" ] &&
  [ "$(hashfile "$BACK/parity-session")" = "$BASE_O" ] || fail backup_corrupt
fi
checkidle
mount -uw /mnt/app 2>/dev/null || fail app_rw
RW=1
if [ "$MODE" = install ]; then
  mkdir -p "$BACK" || fail backup_dir
  cp "$DST/direct-ts-parity" "$BACK/direct-ts-parity" || fail backup_bridge
  cp "$DST/parity-session" "$BACK/parity-session" || fail backup_owner
  [ "$(hashfile "$BACK/direct-ts-parity")" = "$BASE_B" ] &&
  [ "$(hashfile "$BACK/parity-session")" = "$BASE_O" ] || fail backup_bad
  { echo "$BASE_B direct-ts-parity"; echo "$BASE_O parity-session"; } > "$BACK/original.sha256"
  FROM=$SD
  TARGET_B=$NEW_B;TARGET_O=$NEW_O
else
  FROM=$BACK
  TARGET_B=$BASE_B;TARGET_O=$BASE_O
fi
cp "$FROM/direct-ts-parity" "$DST/direct-ts-parity.clockdiag-staged" || fail stage_bridge
cp "$FROM/parity-session" "$DST/parity-session.clockdiag-staged" || fail stage_owner
chmod 755 "$DST/direct-ts-parity.clockdiag-staged" "$DST/parity-session.clockdiag-staged" || fail chmod
[ "$(hashfile "$DST/direct-ts-parity.clockdiag-staged")" = "$TARGET_B" ] &&
[ "$(hashfile "$DST/parity-session.clockdiag-staged")" = "$TARGET_O" ] || fail stage_hash
ALTERED=1
mv "$DST/direct-ts-parity.clockdiag-staged" "$DST/direct-ts-parity" || fail replace_bridge
mv "$DST/parity-session.clockdiag-staged" "$DST/parity-session" || fail replace_owner
[ "$(hashfile "$DST/direct-ts-parity")" = "$TARGET_B" ] &&
[ "$(hashfile "$DST/parity-session")" = "$TARGET_O" ] || fail installed_hash
sync 2>/dev/null || fail sync
mount -ur /mnt/app 2>/dev/null || fail app_ro
RW=0
COMMITTED=1
echo "POLL_SWAP=PASS action=$MODE"
echo "POLL_SWAP=BACKUP=$BACK"
