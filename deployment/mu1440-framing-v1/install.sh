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
LSD=/mnt/app/eso/hmi/lsd/lsd.sh
EXPECTED_AIRPLAY=193a4fd9101ec2aa05e7159cfa307b96500810d379ca74a194f172adc13a46b5

BACK=/mnt/app/root/mibr-framing-v1-backup
ACTIVE=/mnt/app/root/mibr-framing-v1-active
APP_RW=0

STATE_ENABLED=/mnt/app/root/mibr-carplay111-enabled
STATE_AUTODIRECT=/mnt/app/root/mibr-carplay-autodirect
STATE_AUTODIRECT_LEGACY=/mnt/app/root/mibr-carplay-autodirect.enabled
STATE_FPS=/mnt/app/root/mibr-carplay111-fps
STATE_FRAMING=/mnt/app/root/mibr-carplay111-framing
STATE_VIDEO=/mnt/app/root/mibr-carplay111-video.conf
STATE_KEYFRAMES=/mnt/app/root/mibr-carplay111-keyframes.conf
STATE_SOURCEVERSION=/mnt/app/root/mibr-carplay111-sourceversion
STATE_URL=/mnt/app/root/mibr-carplay111-url
STATE_UIURLS=/mnt/app/root/mibr-carplay111-ui-urls.conf
STATE_NAV=/mnt/app/root/mibr-carplay111-nav.conf
STATE_DISPLAY=/mnt/app/root/mibr-carplay111-display.conf
STATE_VIEWAREAS=/mnt/app/root/mibr-carplay111-viewareas.conf

# Legacy state is backed up because the Auto-Direct migration may remove its marker.
LEGACY_VIEWAREAS=/mnt/app/root/mibr-carplay111-viewareas
LEGACY_SAFEAREA=/mnt/app/root/mibr-carplay111-safearea.conf
LEGACY_NAV_QUERY=/mnt/app/root/mibr-carplay111-nav-query

hashf(){
  set -- $("$SHA" "$1" 2>/dev/null)
  [ -n "${1:-}" ] || return 1
  echo "$1"
}

fail(){
  echo "MIBR_CLASSIC111=FAIL $*"
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
    [ -n "${REL:-}" ] || fail "invalid_manifest_line"
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
  grep -Fq "LD_PRELOAD=$HOOK" "$TARGET" 2>/dev/null || fail "base_carplay_preload_not_active"
  for F in     "$DST/bin/libaltscreen111.so"     "$DST/bin/direct-ts-remux"     "$DST/bin/sha256sum"     "$DST/scripts/common.sh"     "$DST/scripts/direct_ts_auto_supervisor.sh"     "$DST/scripts/direct_ts_auto_status.sh"     "$DST/scripts/direct_ts_auto_stop.sh"     "$DST/scripts/writev_gate.sh"     "$HOOK"
  do
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

check_tmp_log_root(){
  T=/tmp/mibr-framing-v1-write-test-$
  touch "$T" 2>/dev/null || fail "tmp_log_root_not_writable"
  [ -f "$T" ] || fail "tmp_log_root_write_test_missing"
  rm -f "$T" 2>/dev/null || true
}

show_plan(){
  echo "=== MU1440 Classic Type-111 runtime-contract candidate ==="
  echo "target=MHI2_ER_SKG13_P4526_MU1440"
  echo "candidate_gen2_sha256=$(candidate_hash gen2)"
  echo "candidate_remux_sha256=$(candidate_hash remux)"
  echo "config_precedence=/tmp_then_/mnt/app/root_then_default"
  echo "fps_default=30"
  echo "framing_default=raw"
  echo "video_default=pace:1,pace_buffer:3"
  echo "source_version_default=1005.8.1"
  echo "url_default=auto"
  echo "viewareas_default=2"
  echo "view0_safe=0,0,1010,376"
  echo "view1_safe=0,58,1010,248"
  echo "d2_default=enabled:1,event_delay:250,min_gap:1000,watchdog:1000"
  echo "source_timing=clock_monotonic"
  echo "m1au_timestamp=8_raw_bytes"
  echo "pts_pcr=UNCHANGED_CFR"
  echo "media=EXCLUDED"
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

same_as_package(){
  LIVE=$1
  PKG=$2
  LH=$(hashf "$LIVE" 2>/dev/null) || return 1
  PH=$(hashf "$PKG" 2>/dev/null) || return 1
  [ "$LH" = "$PH" ]
}

verify_manifest
check_base
check_tmp_log_root
show_plan

case "${1:---check}" in
  --check)
    echo "MIBR_CLASSIC111_CHECK=PASS"
    echo "next=./install.sh --apply"
    exit 0
    ;;
  --apply) ;;
  *) echo "usage: $0 --check|--apply"; exit 64 ;;
esac

if [ -e "$ACTIVE" ]; then
  if same_as_package "$DST/bin/libaltscreen111.so" "$PAYLOAD/libaltscreen111.so" &&
     same_as_package "$DST/bin/direct-ts-remux" "$PAYLOAD/direct-ts-remux" &&
     same_as_package "$HOOK" "$PAYLOAD/libaltscreen111.so" &&
     same_as_package "$DST/scripts/common.sh" "$RUNTIME/auto-direct/common.sh" &&
     same_as_package "$DST/scripts/direct_fps.sh" "$RUNTIME/auto-direct/direct_fps.sh" &&
     same_as_package "$DST/scripts/direct_source_mode.sh" "$RUNTIME/auto-direct/direct_source_mode.sh" &&
     same_as_package "$DST/scripts/direct_autodirect.sh" "$RUNTIME/auto-direct/direct_autodirect.sh" &&
     same_as_package "$DST/scripts/gen2_video.sh" "$RUNTIME/auto-direct/gen2_video.sh" &&
     same_as_package "$DST/scripts/gen2_nav_config.sh" "$RUNTIME/navigation/gen2_nav_config.sh" &&
     same_as_package "$DST/scripts/gen2_url.sh" "$RUNTIME/navigation/gen2_url.sh" &&
     same_as_package "$DST/scripts/gen2_ui_urls.sh" "$RUNTIME/navigation/gen2_ui_urls.sh" &&
     same_as_package "$DST/scripts/gen2_viewareas.sh" "$RUNTIME/navigation/gen2_viewareas.sh" &&
     same_as_package "$DST/scripts/gen2_keyframes.sh" "$RUNTIME/diagnostics/gen2_keyframes.sh" &&
     same_as_package "$DST/scripts/gen2_sourceversion.sh" "$RUNTIME/diagnostics/gen2_sourceversion.sh" &&
     same_as_package "$DST/scripts/gen2_display.sh" "$RUNTIME/diagnostics/gen2_display.sh" &&
     same_as_package "$DST/scripts/gen2_enabled.sh" "$RUNTIME/diagnostics/gen2_enabled.sh"; then
    echo "MIBR_CLASSIC111=ALREADY_INSTALLED"
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

for SPEC in   "$DST/bin/libaltscreen111.so:bin/libaltscreen111.so"   "$DST/bin/direct-ts-remux:bin/direct-ts-remux"   "$HOOK:hook/libmibr_carplay111.so"   "$DST/scripts/common.sh:scripts/common.sh"   "$DST/scripts/direct_fps.sh:scripts/direct_fps.sh"   "$DST/scripts/direct_source_mode.sh:scripts/direct_source_mode.sh"   "$DST/scripts/direct_autodirect.sh:scripts/direct_autodirect.sh"   "$DST/scripts/gen2_video.sh:scripts/gen2_video.sh"   "$DST/scripts/direct_ts_auto_supervisor.sh:scripts/direct_ts_auto_supervisor.sh"   "$DST/scripts/direct_ts_auto_status.sh:scripts/direct_ts_auto_status.sh"   "$DST/scripts/direct_ts_auto_start.sh:scripts/direct_ts_auto_start.sh"   "$DST/scripts/direct_ts_auto_watchdog.sh:scripts/direct_ts_auto_watchdog.sh"   "$DST/scripts/direct_ts_auto_enable.sh:scripts/direct_ts_auto_enable.sh"   "$DST/scripts/direct_ts_auto_disable.sh:scripts/direct_ts_auto_disable.sh"   "$DST/scripts/gen2_nav_config.sh:scripts/gen2_nav_config.sh"   "$DST/scripts/gen2_url.sh:scripts/gen2_url.sh"   "$DST/scripts/gen2_ui_urls.sh:scripts/gen2_ui_urls.sh"   "$DST/scripts/gen2_viewareas.sh:scripts/gen2_viewareas.sh"   "$DST/scripts/gen2_safearea.sh:scripts/gen2_safearea.sh"   "$DST/scripts/gen2_keyframes.sh:scripts/gen2_keyframes.sh"   "$DST/scripts/gen2_sourceversion.sh:scripts/gen2_sourceversion.sh"   "$DST/scripts/gen2_display.sh:scripts/gen2_display.sh"   "$DST/scripts/gen2_enabled.sh:scripts/gen2_enabled.sh"   "$DST/scripts/viewarea_mode.sh:scripts/viewarea_mode.sh"   "$LSD:system/lsd.sh"   "$STATE_ENABLED:state/mibr-carplay111-enabled"   "$STATE_AUTODIRECT:state/mibr-carplay-autodirect"   "$STATE_AUTODIRECT_LEGACY:state/mibr-carplay-autodirect.enabled"   "$STATE_FPS:state/mibr-carplay111-fps"   "$STATE_FRAMING:state/mibr-carplay111-framing"   "$STATE_VIDEO:state/mibr-carplay111-video.conf"   "$STATE_KEYFRAMES:state/mibr-carplay111-keyframes.conf"   "$STATE_SOURCEVERSION:state/mibr-carplay111-sourceversion"   "$STATE_URL:state/mibr-carplay111-url"   "$STATE_UIURLS:state/mibr-carplay111-ui-urls.conf"   "$STATE_NAV:state/mibr-carplay111-nav.conf"   "$STATE_DISPLAY:state/mibr-carplay111-display.conf"   "$STATE_VIEWAREAS:state/mibr-carplay111-viewareas.conf"   "$LEGACY_VIEWAREAS:legacy/mibr-carplay111-viewareas"   "$LEGACY_SAFEAREA:legacy/mibr-carplay111-safearea.conf"   "$LEGACY_NAV_QUERY:legacy/mibr-carplay111-nav-query"
do
  SRC=${SPEC%%:*}
  REL=${SPEC#*:}
  backup_one "$SRC" "$REL"
done
: > "$BACK/BACKUP_COMPLETE" || fail "backup_complete_marker"

install_one "$PAYLOAD/libaltscreen111.so" "$DST/bin/libaltscreen111.so"
install_one "$PAYLOAD/libaltscreen111.so" "$HOOK"
install_one "$PAYLOAD/direct-ts-remux" "$DST/bin/direct-ts-remux"

for F in   common.sh direct_fps.sh direct_source_mode.sh direct_autodirect.sh gen2_video.sh   direct_ts_auto_supervisor.sh direct_ts_auto_status.sh   direct_ts_auto_start.sh direct_ts_auto_watchdog.sh   direct_ts_auto_enable.sh direct_ts_auto_disable.sh
do
  install_one "$RUNTIME/auto-direct/$F" "$DST/scripts/$F"
done

for F in gen2_nav_config.sh gen2_url.sh gen2_ui_urls.sh gen2_viewareas.sh gen2_safearea.sh; do
  install_one "$RUNTIME/navigation/$F" "$DST/scripts/$F"
done

for F in gen2_keyframes.sh gen2_sourceversion.sh gen2_display.sh gen2_enabled.sh; do
  install_one "$RUNTIME/diagnostics/$F" "$DST/scripts/$F"
done

install_one "$RUNTIME/experimental/viewarea_mode.sh" "$DST/scripts/viewarea_mode.sh"

# Old temporary aliases must never shadow the final contract.
rm -f /tmp/mibr-alt111-url-mode /tmp/mibr-alt111-keyframe-policy.enabled 2>/dev/null || true
app_ro

# Normalize the existing lsd.sh Auto-Direct boot block. It writes only the
# persistent Auto-Direct=1 value; all other settings remain absent/default.
MIBR_PREPARE_ONLY=1 "$DST/scripts/direct_ts_auto_enable.sh" || fail "autodirect_contract_migration"

app_rw || fail "mount_app_rw_active_marker"
{
  echo "candidate=classic111-runtime-contract-v1"
  echo "gen2_sha256=$(candidate_hash gen2)"
  echo "remux_sha256=$(candidate_hash remux)"
  echo "installed_from=$ROOT"
} > "$ACTIVE" || fail "active_marker_write"
app_ro

GH=$(hashf "$DST/bin/libaltscreen111.so")
RH=$(hashf "$DST/bin/direct-ts-remux")
HH=$(hashf "$HOOK")
[ "$GH" = "$(candidate_hash gen2)" ] || fail "post_gen2_hash=$GH"
[ "$HH" = "$(candidate_hash gen2)" ] || fail "post_hook_hash=$HH"
[ "$RH" = "$(candidate_hash remux)" ] || fail "post_remux_hash=$RH"

echo "MIBR_CLASSIC111=PASS"
echo "config_precedence=/tmp_then_/mnt/app/root_then_default"
echo "source_fps_default=30"
echo "framing_default=raw"
echo "source_version_default=1005.8.1"
echo "viewareas_default=2"
echo "d2_default=enabled:1,event_delay:250,min_gap:1000,watchdog:1000"
echo "source_timing=clock_monotonic"
echo "pts_pcr=UNCHANGED_CFR"
echo "REBOOT_REQUIRED=YES"
echo "after_reboot=ksh $DST/scripts/direct_ts_auto_status.sh"
