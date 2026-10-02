#!/bin/ksh
set -u

SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2

PAYLOAD=$ROOT/payload
RUNTIME=$ROOT/runtime
SHA=$PAYLOAD/sha256sum
MANIFEST=$ROOT/PAYLOAD.sha256

DST=/mnt/app/root/altscreen-u2
HOOK=/mnt/app/eso/lib/libmibr_carplay111.so
TARGET=/mnt/system/etc/eso/production/smartphone_integrator.json
AIRPLAY=/mnt/app/eso/lib/libairplay.so
EXPECTED_AIRPLAY=193a4fd9101ec2aa05e7159cfa307b96500810d379ca74a194f172adc13a46b5

BACK=/mnt/app/root/mibr-framing-v1-backup
ACTIVE=/mnt/app/root/mibr-framing-v1-active
APP_RW=0

hashf(){
  set -- $("$SHA" "$1" 2>/dev/null)
  [ -n "${1:-}" ] || return 1
  echo "$1"
}

fail(){
  echo "MIBR_FRAMING_V1=FAIL $*"
  if [ "$APP_RW" -eq 1 ]; then
    sync 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    APP_RW=0
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
    mount -ur /mnt/app 2>/dev/null || true
    APP_RW=0
  fi
}
trap app_ro 0 1 2 15

verify_manifest(){
  [ -x "$SHA" ] || fail "missing_sha256_helper=$SHA"
  [ -r "$MANIFEST" ] || fail "missing_manifest=$MANIFEST"
  while read EXPECT REL; do
    [ -n "${EXPECT:-}" ] || continue
    case "$REL" in
      ** ) REL=${REL#*} ;;
    esac
    F=$ROOT/$REL
    [ -r "$F" ] || fail "missing_payload=$REL"
    GOT=$(hashf "$F") || fail "hash_failed=$REL"
    [ "$GOT" = "$EXPECT" ] || fail "hash_mismatch=$REL expected=$EXPECT actual=$GOT"
  done < "$MANIFEST"
}

check_base(){
  [ -d "$DST" ] || fail "base_runtime_missing=$DST"
  [ -r "$TARGET" ] || fail "smartphone_integrator_missing"
  [ -r "$AIRPLAY" ] || fail "libairplay_missing"
  AH=$(hashf "$AIRPLAY") || fail "libairplay_hash_failed"
  [ "$AH" = "$EXPECTED_AIRPLAY" ] || fail "wrong_target_libairplay=$AH"
  grep -Fq "LD_PRELOAD=$HOOK" "$TARGET" 2>/dev/null ||
    fail "base_carplay_preload_not_active"
  for F in     "$DST/bin/libaltscreen111.so"     "$DST/bin/direct-ts-remux"     "$DST/scripts/common.sh"     "$DST/scripts/direct_ts_auto_supervisor.sh"     "$DST/scripts/direct_ts_auto_status.sh"     "$DST/scripts/direct_fps.sh"     "$HOOK"; do
      [ -r "$F" ] || fail "base_file_missing=$F"
  done
}

candidate_hash(){
  case "$1" in
    gen2) hashf "$PAYLOAD/libaltscreen111.so" ;;
    remux) hashf "$PAYLOAD/direct-ts-remux" ;;
    *) return 1 ;;
  esac
}

show_plan(){
  echo "=== MU1440 framing-v1 candidate overlay ==="
  echo "target=MHI2_ER_SKG13_P4526_MU1440"
  echo "base_runtime=$DST"
  echo "candidate_gen2_sha256=$(candidate_hash gen2)"
  echo "candidate_remux_sha256=$(candidate_hash remux)"
  echo "default_source_fps=30"
  echo "default_transport=raw-annexb"
  echo "optional_transport=m1au-v1"
  echo "safearea_helper=included"
  echo "pts_pcr=UNCHANGED_CFR"
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
    chmod 755 "$DSTB" 2>/dev/null || true
  else
    : > "$DSTB.ABSENT" || fail "backup_absent_marker=$REL"
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

verify_manifest
check_base
show_plan

case "${1:---check}" in
  --check)
    echo "MIBR_FRAMING_V1_CHECK=PASS"
    echo "next=./install.sh --apply"
    exit 0
    ;;
  --apply) ;;
  *)
    echo "usage: $0 --check|--apply"
    exit 64
    ;;
esac

if [ -e "$ACTIVE" ]; then
  G=$(hashf "$DST/bin/libaltscreen111.so" 2>/dev/null)
  R=$(hashf "$DST/bin/direct-ts-remux" 2>/dev/null)
  CG=$(candidate_hash gen2)
  CR=$(candidate_hash remux)
  if [ "$G" = "$CG" ] && [ "$R" = "$CR" ]; then
    echo "MIBR_FRAMING_V1=ALREADY_INSTALLED"
    exit 0
  fi
  fail "active_marker_with_different_runtime"
fi

if [ -d "$BACK" ] && [ ! -e "$ACTIVE" ]; then
  fail "orphan_backup_exists=$BACK run_uninstall_for_recovery_or_review_backup"
fi

if [ -x "$DST/scripts/direct_ts_auto_stop.sh" ]; then
  "$DST/scripts/direct_ts_auto_stop.sh" >/dev/null 2>&1 || true
fi

app_rw || fail "mount_app_rw"
mkdir -p "$BACK" || fail "backup_dir"

backup_one "$DST/bin/libaltscreen111.so" bin/libaltscreen111.so
backup_one "$DST/bin/direct-ts-remux" bin/direct-ts-remux
backup_one "$HOOK" hook/libmibr_carplay111.so
backup_one "$DST/scripts/common.sh" scripts/common.sh
backup_one "$DST/scripts/direct_fps.sh" scripts/direct_fps.sh
backup_one "$DST/scripts/direct_ts_auto_supervisor.sh" scripts/direct_ts_auto_supervisor.sh
backup_one "$DST/scripts/direct_ts_auto_status.sh" scripts/direct_ts_auto_status.sh
backup_one "$DST/scripts/direct_source_mode.sh" scripts/direct_source_mode.sh
backup_one "$DST/scripts/gen2_safearea.sh" scripts/gen2_safearea.sh
: > "$BACK/BACKUP_COMPLETE" || fail "backup_complete_marker"

install_one "$PAYLOAD/libaltscreen111.so" "$DST/bin/libaltscreen111.so"
install_one "$PAYLOAD/libaltscreen111.so" "$HOOK"
install_one "$PAYLOAD/direct-ts-remux" "$DST/bin/direct-ts-remux"
install_one "$RUNTIME/auto-direct/common.sh" "$DST/scripts/common.sh"
install_one "$RUNTIME/auto-direct/direct_fps.sh" "$DST/scripts/direct_fps.sh"
install_one "$RUNTIME/auto-direct/direct_ts_auto_supervisor.sh" "$DST/scripts/direct_ts_auto_supervisor.sh"
install_one "$RUNTIME/auto-direct/direct_ts_auto_status.sh" "$DST/scripts/direct_ts_auto_status.sh"
install_one "$RUNTIME/auto-direct/direct_source_mode.sh" "$DST/scripts/direct_source_mode.sh"
install_one "$RUNTIME/navigation/gen2_safearea.sh" "$DST/scripts/gen2_safearea.sh"

{
  echo "candidate=framing-v1"
  echo "gen2_sha256=$(candidate_hash gen2)"
  echo "remux_sha256=$(candidate_hash remux)"
  echo "installed_from=$ROOT"
} > "$ACTIVE" || fail "active_marker_write"

# Default remains raw Annex-B even if a stale candidate override survived a prior experiment.
rm -f /mnt/app/root/mibr-direct-source-framing 2>/dev/null || true

app_ro

GH=$(hashf "$DST/bin/libaltscreen111.so")
RH=$(hashf "$DST/bin/direct-ts-remux")
HH=$(hashf "$HOOK")
[ "$GH" = "$(candidate_hash gen2)" ] || fail "post_gen2_hash=$GH"
[ "$HH" = "$(candidate_hash gen2)" ] || fail "post_hook_hash=$HH"
[ "$RH" = "$(candidate_hash remux)" ] || fail "post_remux_hash=$RH"

echo "MIBR_FRAMING_V1=PASS"
echo "transport_default=raw-annexb"
echo "source_fps_default=30"
echo "REBOOT_REQUIRED=YES"
echo "after_reboot=$DST/scripts/direct_source_mode.sh status"
