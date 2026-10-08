#!/bin/ksh
# Exact-build CI295 <-> fixture CI300. No stock process signals or reboot.
# QNX MU1440 only; run with car parked. No automatic start.
set -u
export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1
SRC=/net/mmx/fs/sda0/esd/carplay-test/omonob-clock-test/fixture-replay-v1
DST=/mnt/app/root/altscreen-u2/bin
SHA=$DST/sha256sum
BACK=/mnt/app/root/mibr-fixture-replay-backup-ci295
OLD_B=a6f9e64d807c8ebb827634eb7b1e0421f8b0961329a76bee3a2ad361bf4fad3b
OLD_O=a0422a36f245b3dd5a4dd88a6bc930ba007c8993489a2ee402b6b33e72c820c7
NEW_B=7fa78266b2df3106e1e6372c8873cdfca4d318999262e82b35291bb7ca8a0b8b
NEW_O=441cd1436a94e0a7f4f5f76820646c7f3195984ff1036771b909b6af3f2aaca7
STAGE_B=$DST/direct-ts-parity.fixture-staged
STAGE_O=$DST/parity-session.fixture-staged
MODE=${1:-status}
RW=0
ALTERED=0
COMMITTED=0
PREV_SRC=
PREV_B=
PREV_O=
hashfile(){ "$SHA" "$1" 2>/dev/null | awk '{print $1}'; }
fail(){ echo "REPLAY_SWAP=FAIL reason=$1"; exit 1; }
idle(){
  [ ! -e /tmp/mibr-parity-session.lock ] || fail owner_lock_present
  [ ! -e /tmp/mibr-isotx2-gate.direct ] || fail stock_gate_request_present
  for P in /tmp/mibr-parity-session.pid /tmp/mibr-parity-session-bridge.pid /tmp/mibr-parity-session-watchdog.pid /tmp/mibr-parity-drive-supervisor.pid; do
    [ ! -e "$P" ] || fail parity_runtime_active
  done
  if [ -r /mnt/app/root/mibr-parity-drive.enabled ]; then
    [ "$(cat /mnt/app/root/mibr-parity-drive.enabled 2>/dev/null)" != 1 ] || fail drive_enabled
  fi
  [ -r /tmp/mibr-alt111-native-gate.status ] || fail native_gate_status_missing
  GATE=$(cat /tmp/mibr-alt111-native-gate.status 2>/dev/null)
  case "$GATE" in 'M1GATE1 0 '*) : ;; *) fail native_gate_not_stock ;; esac
  PS=$(pidin ar 2>/dev/null) || fail pidin_failed
  if echo "$PS" | grep -E '(^|[/[:space:]])(direct-ts-parity|parity-session|parity_drive_supervisor\.sh)([[:space:]]|$)' >/dev/null 2>&1; then
    fail parity_process_present
  fi
  if [ -r /tmp/mibr-parity-session.state ]; then
    STATE=$(cat /tmp/mibr-parity-session.state 2>/dev/null)
    case "$STATE" in complete_stock|failed_stock) : ;; *) fail invalid_session_state ;; esac
  fi
  echo 'REPLAY_SWAP=IDLE_PASS native_gate_stock=1 no_owner=1'
}
recover(){
  if [ -n "$PREV_SRC" ]; then
    echo 'REPLAY_SWAP=AUTORESTORE_START'
    cp "$PREV_SRC/direct-ts-parity" "$DST/direct-ts-parity" 2>/dev/null || true
    cp "$PREV_SRC/parity-session" "$DST/parity-session" 2>/dev/null || true
    chmod 755 "$DST/direct-ts-parity" "$DST/parity-session" 2>/dev/null || true
    if [ "$(hashfile "$DST/direct-ts-parity")" = "$PREV_B" ] &&
       [ "$(hashfile "$DST/parity-session")" = "$PREV_O" ]; then
      echo 'REPLAY_SWAP=AUTORESTORE_PASS'
    else
      echo 'REPLAY_SWAP=AUTORESTORE_FAILED_MANUAL_ACTION_REQUIRED'
    fi
  fi
}
cleanup(){
  RC=$?
  trap - 0 1 2 15
  if [ "$RW" -eq 1 ]; then
    rm -f "$STAGE_B" "$STAGE_O" 2>/dev/null || true
    if [ "$ALTERED" -eq 1 ] && [ "$COMMITTED" -eq 0 ]; then recover; fi
    sync 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || { echo 'REPLAY_SWAP=APP_READ_ONLY_RESTORE_FAILED'; RC=3; }
  fi
  exit "$RC"
}
trap cleanup 0
trap 'exit 130' 1 2 15
case "$MODE" in
  status|start|stop|preflight)
    [ -r "$SRC/MU1440_REPLAY_RUN.sh" ] || fail runner_script_missing
    exec /bin/ksh "$SRC/MU1440_REPLAY_RUN.sh" "$MODE" ;;
  verify)
    [ -x "$SHA" ] || fail sha_helper_missing
    echo "BRIDGE_SHA256=$(hashfile "$DST/direct-ts-parity")"
    echo "OWNER_SHA256=$(hashfile "$DST/parity-session")"
    [ "$(hashfile "$DST/direct-ts-parity")" = "$NEW_B" ] &&
    [ "$(hashfile "$DST/parity-session")" = "$NEW_O" ] || fail installed_pair_unexpected
    echo 'REPLAY_SWAP=VERIFY_PASS'; exit 0 ;;
  install|restore) : ;;
  *) echo 'usage: MU1440_REPLAY_SWAP.sh install|verify|preflight|start|status|stop|restore'; exit 2 ;;
esac
[ -x "$SHA" ] || fail sha_helper_missing
[ -f "$DST/direct-ts-parity" ] && [ -f "$DST/parity-session" ] || fail installed_binary_missing
CUR_B=$(hashfile "$DST/direct-ts-parity")
CUR_O=$(hashfile "$DST/parity-session")
if [ "$MODE" = install ]; then
  [ -r "$SRC/direct-ts-parity" ] && [ -r "$SRC/parity-session" ] || fail SD_new_pair_missing
  [ "$(hashfile "$SRC/direct-ts-parity")" = "$NEW_B" ] &&
  [ "$(hashfile "$SRC/parity-session")" = "$NEW_O" ] || fail SD_new_pair_mismatch
  if [ "$CUR_B" = "$NEW_B" ] && [ "$CUR_O" = "$NEW_O" ]; then
    echo 'REPLAY_SWAP=ALREADY_INSTALLED'; exit 0
  fi
  [ "$CUR_B" = "$OLD_B" ] && [ "$CUR_O" = "$OLD_O" ] || fail baseline_is_not_CI295
  idle
  PREV_SRC=$BACK
  PREV_B=$OLD_B
  PREV_O=$OLD_O
else
  if [ "$CUR_B" = "$OLD_B" ] && [ "$CUR_O" = "$OLD_O" ]; then
    echo 'REPLAY_SWAP=ALREADY_RESTORED_CI295'; exit 0
  fi
  [ "$CUR_B" = "$NEW_B" ] && [ "$CUR_O" = "$NEW_O" ] || fail installed_not_fixture_pair
  [ -d "$BACK" ] || fail backup_missing
  [ "$(hashfile "$BACK/direct-ts-parity")" = "$OLD_B" ] &&
  [ "$(hashfile "$BACK/parity-session")" = "$OLD_O" ] || fail backup_hash_mismatch
  idle
  PREV_SRC=$SRC
  PREV_B=$NEW_B
  PREV_O=$NEW_O
fi
echo "REPLAY_SWAP=PRECHECK_PASS action=$MODE"
mount -uw /mnt/app 2>/dev/null || fail app_mount_rw
RW=1
if [ "$MODE" = install ]; then
  if [ -d "$BACK" ]; then
    [ "$(hashfile "$BACK/direct-ts-parity")" = "$OLD_B" ] &&
    [ "$(hashfile "$BACK/parity-session")" = "$OLD_O" ] || fail backup_conflict
  else
    mkdir -p "$BACK" || fail backup_directory_create
    cp "$DST/direct-ts-parity" "$BACK/direct-ts-parity" || fail backup_bridge_copy
    cp "$DST/parity-session" "$BACK/parity-session" || fail backup_owner_copy
  fi
  [ "$(hashfile "$BACK/direct-ts-parity")" = "$OLD_B" ] &&
  [ "$(hashfile "$BACK/parity-session")" = "$OLD_O" ] || fail backup_verify
  echo 'REPLAY_SWAP=BACKUP_PASS version=CI295'
  FROM_B=$SRC/direct-ts-parity
  FROM_O=$SRC/parity-session
  NEED_B=$NEW_B
  NEED_O=$NEW_O
else
  FROM_B=$BACK/direct-ts-parity
  FROM_O=$BACK/parity-session
  NEED_B=$OLD_B
  NEED_O=$OLD_O
fi
cp "$FROM_B" "$STAGE_B" || fail stage_bridge
cp "$FROM_O" "$STAGE_O" || fail stage_owner
chmod 755 "$STAGE_B" "$STAGE_O" || fail chmod_stage
[ "$(hashfile "$STAGE_B")" = "$NEED_B" ] &&
[ "$(hashfile "$STAGE_O")" = "$NEED_O" ] || fail stage_hash
ALTERED=1
mv "$STAGE_B" "$DST/direct-ts-parity" || fail replace_bridge
mv "$STAGE_O" "$DST/parity-session" || fail replace_owner
[ "$(hashfile "$DST/direct-ts-parity")" = "$NEED_B" ] &&
[ "$(hashfile "$DST/parity-session")" = "$NEED_O" ] || fail installed_hash
sync 2>/dev/null || fail sync
mount -ur /mnt/app 2>/dev/null || fail app_mount_ro
RW=0
COMMITTED=1
echo "REPLAY_SWAP=PASS action=$MODE"
echo "ROLLBACK_BACKUP=$BACK"
echo 'APP_MOUNT=READ_ONLY'
