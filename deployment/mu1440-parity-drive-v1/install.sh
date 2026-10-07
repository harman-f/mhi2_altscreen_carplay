#!/bin/ksh
set -u

# BEGIN_TARGET_ENV -- proven installed MU1440 runtime paths
export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/media/gracenote/bin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin:/mnt/app/armle/usr/sbin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1
# END_TARGET_ENV

SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2

PAYLOAD=$ROOT/payload
RUNTIME=$ROOT/runtime
SHA=$PAYLOAD/sha256sum
MANIFEST=$ROOT/PAYLOAD.sha256
. "$ROOT/runtime/settings-basenames.sh" || exit 20
. "$ROOT/runtime/master-script-basenames.sh" || exit 20

DST=/mnt/app/root/altscreen-u2
HOOK=/mnt/app/eso/lib/libmibr_carplay111.so
AIRPLAY=/mnt/app/eso/lib/libairplay.so
TARGET=/mnt/system/etc/eso/production/smartphone_integrator.json
STARTUP=/mnt/system/etc/boot/startup.sh
GUARD=/mnt/app/eso/lib/libmibr_isotx2_guard.so
OLD_GATE_LINE='        LD_PRELOAD=/mnt/app/eso/lib/libmibr_isotx2_gate.so MALLOC_ARENA_CACHE_MAXSZ=400000 on -p 15 /eso/bin/apps/displaymanager ${DM_EXTRA_OPTS} ${LVDS2} &'
NEW_GATE_LINE='        LD_PRELOAD=/mnt/app/eso/lib/libmibr_isotx2_guard.so:/mnt/app/eso/lib/libmibr_isotx2_gate.so MALLOC_ARENA_CACHE_MAXSZ=400000 on -p 15 /eso/bin/apps/displaymanager ${DM_EXTRA_OPTS} ${LVDS2} &'
PATCHED_STARTUP=/tmp/mibr-parity-startup.$$

EXPECTED_AIRPLAY=193a4fd9101ec2aa05e7159cfa307b96500810d379ca74a194f172adc13a46b5
EXPECTED_BASE_GEN2=8cccf1cb1764952acd973cbb4f881cfd70f3312e7f6a29cdef7fec930c83d25c
EXPECTED_BASE_REMUX=3f0e730523bd290608dc13e186baa962eeb9c46f117d4d4976be523c0cd94c09
EXPECTED_GATE=05673010a88c25022145ffb4e75d3715eaf686f4127ac188e91a52f512b9d957
BASE_ACTIVE=/mnt/app/root/mibr-framing-v1-active

BACK=/mnt/app/root/mibr-parity-drive-v1-backup
ACTIVE=/mnt/app/root/mibr-parity-drive-v1-active
STATE_AUTODIRECT=/mnt/app/root/mibr-carplay-autodirect
APP_RW=0
SYSTEM_RW=0
MUTATING=0

hashf(){
  set -- $("$SHA" "$1" 2>/dev/null)
  [ -n "${1:-}" ] || return 1
  echo "$1"
}

fail(){
  echo "MIBR_PARITY_DRIVE=FAIL $*"
  system_ro || echo "SYSTEM_MOUNT_STATE=UNCONFIRMED"
  app_ro || echo "APP_MOUNT_STATE=UNCONFIRMED"
  if [ "$MUTATING" -eq 1 ]; then
    echo "MIBR_PARITY_DRIVE=ROLLBACK_AFTER_FAILED_APPLY"
    ksh "$ROOT/uninstall.sh" || echo "MIBR_PARITY_DRIVE=ROLLBACK_FAILED backups_retained=$BACK"
  fi
  exit 20
}

app_rw(){
  [ "$APP_RW" -eq 1 ] && return 0
  mount -uw /mnt/app 2>/dev/null || return 1
  APP_RW=1
}

app_ro(){
  if [ "$APP_RW" -eq 1 ]; then
    sync 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || return 1
    APP_RW=0
  fi
}
system_ro(){
  if [ "$SYSTEM_RW" -eq 1 ]; then
    sync 2>/dev/null || true
    mount -ur /mnt/system 2>/dev/null || return 1
    SYSTEM_RW=0
  fi
}
cleanup(){ system_ro; app_ro; rm -f "$PATCHED_STARTUP" 2>/dev/null || true; }
trap cleanup 0
trap 'cleanup; exit 129' 1
trap 'cleanup; exit 130' 2
trap 'cleanup; exit 143' 15

prepare_startup(){
  [ -r "$STARTUP" ] || fail "startup_missing"
  [ ! -e /mnt/app/root/mibr-isotx2-gate-disable ] || fail "native_gate_disabled"
  awk -v old="$OLD_GATE_LINE" -v replacement="$NEW_GATE_LINE" '
    $0==old {print replacement; hits++; next}
    {print}
    END {if(hits!=1)exit 42}
  ' "$STARTUP" > "$PATCHED_STARTUP" || fail "startup_not_exact_single_known_gate_command"
  ksh -n "$PATCHED_STARTUP" || fail "startup_generated_syntax"
}

verify_manifest(){
  [ -x "$SHA" ] || fail "missing_sha256_helper=$SHA"
  [ -r "$MANIFEST" ] || fail "missing_manifest=$MANIFEST"
  while read EXPECT REL; do
    [ -n "${EXPECT:-}" ] || continue
    [ -n "${REL:-}" ] || fail "invalid_manifest_line"
    F=$ROOT/$REL
    [ -r "$F" ] || fail "missing_payload=$REL"
    GOT=$(hashf "$F") || fail "hash_failed=$REL"
    [ "$GOT" = "$EXPECT" ] || fail "hash_mismatch=$REL expected=$EXPECT actual=$GOT"
  done < "$MANIFEST"
}

candidate_hash(){
  case "$1" in
    gen2) hashf "$PAYLOAD/libaltscreen111.so" ;;
    bridge) hashf "$PAYLOAD/direct-ts-parity" ;;
    session) hashf "$PAYLOAD/parity-session" ;;
    *) return 1 ;;
  esac
}

check_base(){
  [ -e "$BASE_ACTIVE" ] || fail "envfix2_active_marker_missing=$BASE_ACTIVE"
  [ -d "$DST" ] || fail "base_runtime_missing=$DST"
  [ -r "$TARGET" ] || fail "smartphone_integrator_missing"
  [ -r "$AIRPLAY" ] || fail "libairplay_missing"
  AH=$(hashf "$AIRPLAY") || fail "libairplay_hash_failed"
  [ "$AH" = "$EXPECTED_AIRPLAY" ] || fail "wrong_target_libairplay=$AH"
  grep -Fq "LD_PRELOAD=$HOOK" "$TARGET" 2>/dev/null || fail "base_carplay_preload_not_active"

  [ -r "$DST/bin/libaltscreen111.so" ] || fail "base_gen2_missing"
  [ -r "$DST/bin/direct-ts-remux" ] || fail "base_remux_missing"
  [ -r "$HOOK" ] || fail "base_hook_missing"

  GH=$(hashf "$DST/bin/libaltscreen111.so") || fail "base_gen2_hash_failed"
  HH=$(hashf "$HOOK") || fail "base_hook_hash_failed"
  RH=$(hashf "$DST/bin/direct-ts-remux") || fail "base_remux_hash_failed"
  [ "$GH" = "$EXPECTED_BASE_GEN2" ] || fail "wrong_base_gen2=$GH"
  [ "$HH" = "$EXPECTED_BASE_GEN2" ] || fail "wrong_base_hook=$HH"
  [ "$RH" = "$EXPECTED_BASE_REMUX" ] || fail "wrong_base_remux=$RH"

  for LEGACY_STATE in /tmp/mibr-direct-auto-supervisor.pid /tmp/mibr-direct-auto-watchdog.pid /tmp/mibr-direct-auto-bridge.pid; do
    [ ! -e "$LEGACY_STATE" ] || fail "legacy_owner_hint_requires_review=$LEGACY_STATE"
  done
}

check_tmp_root(){
  T=/tmp/mibr-parity-drive-v1-write-test
  rm -f "$T" 2>/dev/null || true
  touch "$T" 2>/dev/null || fail "tmp_root_not_writable"
  [ -f "$T" ] || fail "tmp_root_write_test_missing"
  rm -f "$T" 2>/dev/null || true
}

show_plan(){
  echo "=== MU1440 MU1440 parity-drive candidate ==="
  echo "target=MHI2_ER_SKG13_P4526_MU1440"
  echo "base_gen2_sha256=$EXPECTED_BASE_GEN2"
  echo "base_remux_sha256=$EXPECTED_BASE_REMUX"
  echo "candidate_gen2_sha256=$(candidate_hash gen2)"
  echo "candidate_bridge_sha256=$(candidate_hash bridge)"
  echo "candidate_session_sha256=$(candidate_hash session)"
  echo "transport=complete_m1au_to_source_clocked_mpegts"
  echo "ownership=writev_gate_initial_dmdt_reference_probe_only"
  echo "legacy_autodirect=persistently_disabled_during_candidate"
  echo "profile_apply=temporary_after_reboot_before_carplay_connect"
  echo "backup=$BACK"
  [ -e "$ACTIVE" ] && echo "candidate_active=1" || echo "candidate_active=0"
}

backup_one(){
  SRC=$1
  REL=$2
  DSTB=$BACK/$REL
  DIR=${DSTB%/*}
  mkdir -p "$DIR" || fail "backup_mkdir=$DIR"
  if [ -e "$SRC" ]; then
    cp "$SRC" "$DSTB" || fail "backup_copy=$SRC"
    EXPECT=$(hashf "$SRC") || fail "backup_source_hash=$SRC"
    GOT=$(hashf "$DSTB") || fail "backup_target_hash=$DSTB"
    [ "$EXPECT" = "$GOT" ] || fail "backup_hash_mismatch=$SRC"
    echo "$EXPECT $REL" >> "$BACK/BACKUP.sha256" || fail "backup_manifest=$REL"
  else
    : > "$DSTB.ABSENT" || fail "backup_absent_marker=$REL"
    echo "ABSENT $REL" >> "$BACK/BACKUP.sha256" || fail "backup_manifest=$REL"
  fi
}

install_one(){
  SRC=$1
  DSTF=$2
  MODE=${3:-755}
  TMP=$DSTF.new.$$
  cp "$SRC" "$TMP" || fail "copy=$SRC"
  chmod "$MODE" "$TMP" 2>/dev/null || true
  mv "$TMP" "$DSTF" || fail "replace=$DSTF"
}

same_as_package(){
  LIVE=$1
  PKG=$2
  LH=$(hashf "$LIVE" 2>/dev/null) || return 1
  PH=$(hashf "$PKG" 2>/dev/null) || return 1
  [ "$LH" = "$PH" ]
}

check_environment(){
  AH=$(hashf "$AIRPLAY") || fail "libairplay_hash_failed"
  [ "$AH" = "$EXPECTED_AIRPLAY" ] || fail "wrong_target_libairplay=$AH"
  RH=$(hashf "$DST/bin/direct-ts-remux") || fail "base_remux_hash_failed"
  [ "$RH" = "$EXPECTED_BASE_REMUX" ] || fail "wrong_base_remux=$RH"
  GH=$(hashf /mnt/app/eso/lib/libmibr_isotx2_gate.so) || fail "gate_hash_failed"
  [ "$GH" = "$EXPECTED_GATE" ] || fail "unidentified_gate=$GH"
}

verify_manifest
check_environment
check_tmp_root
show_plan

case "${1:---check}" in
  --check|--apply) ;;
  *) echo "usage: $0 --check|--apply"; exit 64 ;;
esac

if [ -e "$ACTIVE" ]; then
  if same_as_package "$DST/bin/libaltscreen111.so" "$PAYLOAD/libaltscreen111.so" &&
     same_as_package "$HOOK" "$PAYLOAD/libaltscreen111.so" &&
     same_as_package "$DST/bin/direct-ts-parity" "$PAYLOAD/direct-ts-parity" &&
     same_as_package "$DST/bin/parity-session" "$PAYLOAD/parity-session" &&
     same_as_package "$DST/bin/alt111-settings" "$PAYLOAD/alt111-settings" &&
     same_as_package "$GUARD" "$PAYLOAD/libmibr_isotx2_guard.so" &&
     same_as_package "$DST/scripts/parity_profile.sh" "$RUNTIME/parity_profile.sh" &&
     same_as_package "$DST/scripts/parity_session.sh" "$RUNTIME/parity_session.sh" &&
     same_as_package "$DST/scripts/parity_status.sh" "$RUNTIME/parity_status.sh" &&
     same_as_package "$DST/scripts/gen2_compat_profile.sh" "$RUNTIME/gen2_compat_profile.sh"; then
    [ "$(awk -v line="$NEW_GATE_LINE" '$0==line {n++} END {print n+0}' "$STARTUP")" = 1 ] || fail "active_startup_guard_missing"
    for SCRIPT in $ALT111_MASTER_SCRIPTS; do
      same_as_package "$DST/scripts/$SCRIPT" "$RUNTIME/$SCRIPT" || fail "active_script_mismatch=$SCRIPT"
    done
    echo "MIBR_PARITY_DRIVE=ALREADY_INSTALLED"
    exit 0
  fi
  fail "active_marker_with_different_runtime"
fi

check_base
prepare_startup
[ ! -e /tmp/mibr-alt111-settings.journal ] || fail "settings_transaction_reconcile_required"
[ ! -e /tmp/mibr-alt111-settings.journal-armed ] || fail "settings_transaction_reconcile_required"
[ ! -e /tmp/mibr-parity-rollback.pending ] || fail "rollback_requires_canonical_reboot"
[ ! -e /tmp/mibr-parity-session.lock ] || fail "parity_owner_requires_confirmed_stop"

if [ -d "$BACK" ] && [ ! -e "$ACTIVE" ]; then
  fail "orphan_backup_exists=$BACK run_uninstall_for_recovery_or_review_backup"
fi

if [ "${1:---check}" = --check ]; then
  echo "MIBR_PARITY_DRIVE_CHECK=PASS"
  echo "next=./install.sh --apply"
  exit 0
fi

ksh "$ROOT/collect-logs.sh" || fail "sd_log_preflight"

# Preflight rejects legacy ownership hints. The installer never signals a
# numeric PID or releases a gate through the old unbound stop script.

app_rw || fail "mount_app_rw"
mkdir -p "$BACK" || fail "backup_dir"

for SPEC in   "$DST/bin/libaltscreen111.so:bin/libaltscreen111.so"   "$HOOK:hook/libmibr_carplay111.so"   "$DST/bin/direct-ts-parity:bin/direct-ts-parity"   "$DST/bin/parity-session:bin/parity-session"   "$DST/bin/alt111-settings:bin/alt111-settings"   "$GUARD:guard/libmibr_isotx2_guard.so"   "$STARTUP:boot/startup.sh"   "$DST/scripts/parity_profile.sh:scripts/parity_profile.sh"   "$DST/scripts/parity_session.sh:scripts/parity_session.sh"   "$DST/scripts/parity_status.sh:scripts/parity_status.sh"   "$DST/scripts/parity_drive_supervisor.sh:scripts/parity_drive_supervisor.sh"   "$DST/scripts/parity_drive_enable.sh:scripts/parity_drive_enable.sh"   "$DST/scripts/parity_drive_disable.sh:scripts/parity_drive_disable.sh"   "$DST/scripts/parity_drive_status.sh:scripts/parity_drive_status.sh"   "$DST/scripts/gen2_compat_profile.sh:scripts/gen2_compat_profile.sh"   "$STATE_AUTODIRECT:state/mibr-carplay-autodirect"
do
  SRC=${SPEC%%:*}
  REL=${SPEC#*:}
  backup_one "$SRC" "$REL"
done
for SCRIPT in $ALT111_MASTER_SCRIPTS; do
  backup_one "$DST/scripts/$SCRIPT" "scripts/$SCRIPT"
done
for NAME in $ALT111_CONFIG_BASENAMES; do
  backup_one "/tmp/$NAME" "temp/$NAME"
done
: > "$BACK/BACKUP_COMPLETE" || fail "backup_complete_marker"
MUTATING=1

install_one "$PAYLOAD/libaltscreen111.so" "$DST/bin/libaltscreen111.so"
install_one "$PAYLOAD/libaltscreen111.so" "$HOOK"
install_one "$PAYLOAD/direct-ts-parity" "$DST/bin/direct-ts-parity"
install_one "$PAYLOAD/parity-session" "$DST/bin/parity-session"
install_one "$PAYLOAD/alt111-settings" "$DST/bin/alt111-settings"
install_one "$PAYLOAD/libmibr_isotx2_guard.so" "$GUARD"
install_one "$RUNTIME/parity_profile.sh" "$DST/scripts/parity_profile.sh"
install_one "$RUNTIME/parity_session.sh" "$DST/scripts/parity_session.sh"
install_one "$RUNTIME/parity_status.sh" "$DST/scripts/parity_status.sh"
install_one "$RUNTIME/parity_drive_supervisor.sh" "$DST/scripts/parity_drive_supervisor.sh"
install_one "$RUNTIME/parity_drive_enable.sh" "$DST/scripts/parity_drive_enable.sh"
install_one "$RUNTIME/parity_drive_disable.sh" "$DST/scripts/parity_drive_disable.sh"
install_one "$RUNTIME/parity_drive_status.sh" "$DST/scripts/parity_drive_status.sh"
install_one "$RUNTIME/gen2_compat_profile.sh" "$DST/scripts/gen2_compat_profile.sh"

for SCRIPT in $ALT111_MASTER_SCRIPTS; do
  install_one "$RUNTIME/$SCRIPT" "$DST/scripts/$SCRIPT"
done

# Configuration and the exact DisplayManager boot command are both backed up.
echo 0 > "$STATE_AUTODIRECT.new.$$" || fail "autodirect_disable_write"
mv "$STATE_AUTODIRECT.new.$$" "$STATE_AUTODIRECT" || fail "autodirect_disable_replace"
chmod 644 "$STATE_AUTODIRECT" 2>/dev/null || true
mount -uw /mnt/system 2>/dev/null || fail "mount_system_rw"
SYSTEM_RW=1
install_one "$PATCHED_STARTUP" "$STARTUP" 755
system_ro || fail "mount_system_ro"

{
  echo "candidate=mu1440-parity-drive-v1"
  echo "gen2_sha256=$(candidate_hash gen2)"
  echo "bridge_sha256=$(candidate_hash bridge)"
  echo "session_sha256=$(candidate_hash session)"
  echo "base_remux_sha256=$EXPECTED_BASE_REMUX"
  echo "base_gate_sha256=$EXPECTED_GATE"
  echo "installed_from=$ROOT"
} > "$ACTIVE" || fail "active_marker_write"

app_ro || fail "mount_app_ro"

GH=$(hashf "$DST/bin/libaltscreen111.so") || fail "post_gen2_hash_failed"
HH=$(hashf "$HOOK") || fail "post_hook_hash_failed"
BH=$(hashf "$DST/bin/direct-ts-parity") || fail "post_bridge_hash_failed"
SH=$(hashf "$DST/bin/parity-session") || fail "post_session_hash_failed"
RH=$(hashf "$DST/bin/direct-ts-remux") || fail "post_base_remux_hash_failed"

[ "$GH" = "$(candidate_hash gen2)" ] || fail "post_gen2_hash=$GH"
[ "$HH" = "$(candidate_hash gen2)" ] || fail "post_hook_hash=$HH"
[ "$BH" = "$(candidate_hash bridge)" ] || fail "post_bridge_hash=$BH"
[ "$SH" = "$(candidate_hash session)" ] || fail "post_session_hash=$SH"
same_as_package "$DST/bin/alt111-settings" "$PAYLOAD/alt111-settings" || fail "post_settings_hash"
same_as_package "$GUARD" "$PAYLOAD/libmibr_isotx2_guard.so" || fail "post_guard_hash"
[ "$RH" = "$EXPECTED_BASE_REMUX" ] || fail "base_remux_changed=$RH"
[ -r "$STATE_AUTODIRECT" ] && [ "$(cat "$STATE_AUTODIRECT" 2>/dev/null)" = 0 ] || fail "autodirect_not_disabled"

echo "MIBR_PARITY_DRIVE=PASS"
ksh "$ROOT/collect-logs.sh" || fail "sd_log_post_install"
echo "legacy_autodirect=0"
echo "base_direct_ts_remux=UNCHANGED"
echo "REBOOT_REQUIRED=YES"
echo "after_reboot=ksh $DST/scripts/parity_status.sh"
echo "then_apply_temp_profile_before_carplay_connect=ksh $DST/scripts/parity_profile.sh temp"
