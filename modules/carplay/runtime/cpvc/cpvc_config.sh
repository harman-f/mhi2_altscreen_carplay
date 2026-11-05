#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
# CPVC R5: single human configuration CLI; the internal boot mode reuses it.
set -u
export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/armle/bin:/mnt/app/armle/usr/bin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1

MIBR_ROOT=${MIBR_ROOT:-/mnt/app/root/mibr}
BASE=$MIBR_ROOT
PROFILE=$BASE/config/cockpit/cpvc-r5.profile
HELPER=$BASE/bin/alt111-settings
OWNER=$BASE/bin/parity-session
ENABLED=$MIBR_ROOT/config/features/mibr-cpvc.enabled
PARITY_ENABLED=$MIBR_ROOT/config/features/mibr-parity-drive.enabled
ZOOM=/tmp/mibr-alt111-zoom-v1.enabled
ZOOM_AUTOSTART=$BASE/config/cockpit/cpvc-r5-zoom.autostart
APP_RW=0

usage() {
  echo "Usage: config.sh status | enable | disable | set KEY VALUE | zoom status | zoom arm PARKED | zoom disarm"
  echo "  set: navigation.url (auto or maps:/car/instrumentcluster...), navigation.query,"
  echo "       navigation.surface, navigation.ETA/speedLimit/compass/maneuver,"
  echo "       presentation.suggested_urls, viewarea.selected, viewareas.*,"
  echo "       viewarea.0.*, viewarea.1.*, maxFPS (20|25|30|40|60), sourceVersion,"
  echo "       keyframe.* and display.widthPhysical/heightPhysical."
  echo "  Persistent profile is internal; native registry writes remain TEMP only."
  echo "  Zoom V1 OFF by default; arm is volatile and requires explicit parked confirmation."
}
fail() { echo "CPVC_CONFIG=FAIL $*"; exit 20; }
app_rw() { [ "$APP_RW" -eq 1 ] && return 0; mount -uw /mnt/app 2>/dev/null || return 1; APP_RW=1; }
app_ro() {
  if [ "$APP_RW" -eq 1 ]; then
    sync 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || return 1
    APP_RW=0
  fi
  return 0
}
cleanup() { app_ro || echo "CPVC_CONFIG=WARN_APP_MOUNT_STATE"; }
trap cleanup 0
enabled() { [ -r "$ENABLED" ] && [ "$(cat "$ENABLED" 2>/dev/null)" = "1" ]; }
# r23: a missing, unreadable or invalid profile no longer leaves the unit stock-only. The previous
# verified profile (.lastgood, written by every durable save) is validated through the same native
# transaction, applied to TEMP and restored as the profile; the broken file is kept as .corrupt.
fallback_lastgood() {
  LG=$PROFILE.lastgood
  [ -r "$LG" ] || { echo "CPVC_BOOT_PROFILE_FALLBACK=NO_LASTGOOD"; return 1; }
  "$HELPER" batch --input "$LG" --layer temp || { echo "CPVC_BOOT_PROFILE_FALLBACK=LASTGOOD_INVALID"; return 1; }
  if app_rw; then
    [ ! -e "$PROFILE" ] || mv "$PROFILE" "$PROFILE.corrupt" 2>/dev/null || true
    if cp "$LG" "$PROFILE.new.$$" && chmod 600 "$PROFILE.new.$$" && mv "$PROFILE.new.$$" "$PROFILE"; then
      echo "CPVC_BOOT_PROFILE_FALLBACK=LASTGOOD_RESTORED"
    else
      rm -f "$PROFILE.new.$$" 2>/dev/null || true
      echo "CPVC_BOOT_PROFILE_FALLBACK=LASTGOOD_APPLIED_TEMP_RESTORE_FAILED"
    fi
    app_ro || echo "CPVC_CONFIG=WARN_APP_MOUNT_STATE"
  else
    echo "CPVC_BOOT_PROFILE_FALLBACK=LASTGOOD_APPLIED_TEMP_APP_RW_FAILED"
  fi
  return 0
}
replay() {
  rm -f /tmp/mibr-cpvc-profile-ready 2>/dev/null || true
  enabled || { echo "CPVC_BOOT_PROFILE=DISABLED"; return 21; }
  [ -x "$HELPER" ] || { echo "CPVC_BOOT_PROFILE=FAIL_MISSING_COMPONENT"; return 22; }
  [ ! -e /tmp/mibr-alt111-settings.journal ] && [ ! -e /tmp/mibr-alt111-settings.journal-armed ] || {
    echo "CPVC_BOOT_PROFILE=FAIL_NEEDS_RECONCILE"; return 23;
  }
  if [ -r "$PROFILE" ] && "$HELPER" batch --input "$PROFILE" --layer temp; then
    :
  else
    echo "CPVC_BOOT_PROFILE=PRIMARY_INVALID_TRYING_LASTGOOD"
    fallback_lastgood || { echo "CPVC_BOOT_PROFILE=FAIL_TRANSACTION"; return 24; }
  fi
  if [ -r "$ZOOM_AUTOSTART" ] && [ "$(cat "$ZOOM_AUTOSTART" 2>/dev/null)" = 1 ]; then
    : > "$ZOOM" || { echo "CPVC_BOOT_PROFILE=FAIL_ZOOM_MARKER"; return 26; }
    echo "CPVC_BOOT_ZOOM=ARMED_OPERATOR_PERSISTENT_PREFERENCE motion_check=NOT_IMPLEMENTED"
  fi
  : > /tmp/mibr-cpvc-profile-ready || { echo "CPVC_BOOT_PROFILE=FAIL_READY_MARKER"; return 25; }
  echo "CPVC_BOOT_PROFILE=PASS registry_layer=temp source=internal_profile"
  return 0
}
apply_class() {
  case "$1" in
    maxFPS|sourceVersion|viewareas.*|viewarea.0.*|viewarea.1.*|display.*|presentation.suggested_urls) echo RECONNECT_REQUIRED ;;
    navigation.*) echo PRESENTATION_REFRESH_REQUIRED ;;
    viewarea.selected|keyframe.*) echo LIVE_REQUESTED_NOT_ACKNOWLEDGED ;;
    *) echo SESSION_TRANSITION_REQUIRED ;;
  esac
}
allowed_key() {
  case "$1" in
    maxFPS|sourceVersion|viewarea.selected|viewareas.initial|viewareas.transition_ms|\
    viewarea.0.x|viewarea.0.y|viewarea.0.w|viewarea.0.h|viewarea.0.safe.x|viewarea.0.safe.y|viewarea.0.safe.w|viewarea.0.safe.h|\
    viewarea.1.x|viewarea.1.y|viewarea.1.w|viewarea.1.h|viewarea.1.safe.x|viewarea.1.safe.y|viewarea.1.safe.w|viewarea.1.safe.h|\
    keyframe.mode|keyframe.interval_frames|keyframe.interval_ms|keyframe.showui|keyframe.gap_recovery|keyframe.latency_recovery|\
    navigation.url|navigation.query|navigation.surface|navigation.ETA|navigation.speedLimit|navigation.compass|navigation.maneuver|\
    presentation.suggested_urls|display.widthPhysical|display.heightPhysical) return 0 ;;
    *) return 1 ;;
  esac
}
set_value() {
  KEY=$1
  VALUE=$2
  allowed_key "$KEY" || fail "unsupported_or_fixed_key=$KEY"
  case "$VALUE" in
    ''|*[!A-Za-z0-9_:/?\&=.,'|'+-]*) fail "invalid_value_character_or_empty" ;;
  esac
  [ -r "$PROFILE" ] && [ -x "$HELPER" ] || fail "not_installed"
  [ ! -e /tmp/mibr-parity-session.lock ] || {
    case "$KEY" in
      maxFPS|sourceVersion|viewareas.*|viewarea.0.*|viewarea.1.*|display.*) echo "CPVC_CONFIG=NOTICE active_session_requires_reconnect" ;;
    esac
  }
  app_rw || fail "app_rw"
  NEXT=$PROFILE.new.$$
  awk -F= -v k="$KEY" -v v="$VALUE" '
    $1==k {print k "=" v; n++; next} {print}
    END {if(n!=1) exit 42}
  ' "$PROFILE" > "$NEXT" || { rm -f "$NEXT" 2>/dev/null; fail "profile_key_missing_or_duplicate=$KEY"; }
  # The shared native validator rejects invalid geometry, URL and enum combinations
  # and transactionally applies all groups in a single TEMP revision.
  "$HELPER" batch --input "$NEXT" --layer temp || {
    rm -f "$NEXT" 2>/dev/null || true
    fail "native_profile_rejected;persistent_profile_unchanged"
  }
  chmod 644 "$NEXT" 2>/dev/null || true
  mv "$NEXT" "$PROFILE" || fail "profile_commit_failed_check_live_TEMP_before_reboot"
  app_ro || fail "app_ro"
  echo "CPVC_CONFIG=STORED key=$KEY value=$VALUE"
  echo "apply=$(apply_class "$KEY")"
  echo "active_runtime_ack=NOT_CLAIMED"
}
set_enable() {
  VALUE=$1
  [ -r "$PROFILE" ] && [ -x "$HELPER" ] && [ -x "$OWNER" ] || fail "not_installed"
  if [ "$VALUE" = 0 ]; then
    # Revoke future starts first. Native token-bound stop is the only writer stop.
    app_rw || fail "app_rw"
    echo 0 > "$ENABLED.new.$$" || fail "write_disable"
    mv "$ENABLED.new.$$" "$ENABLED" || fail "commit_disable"
    echo 0 > "$PARITY_ENABLED.new.$$" || fail "write_parity_disable"
    mv "$PARITY_ENABLED.new.$$" "$PARITY_ENABLED" || fail "commit_parity_disable"
    app_ro || fail "app_ro"
    rm -f "$ZOOM" 2>/dev/null || true
    "$OWNER" --stop || fail "stop_unconfirmed;manual_reconciliation_required"
    echo "CPVC_CONFIG=DISABLED writer_stop=CONFIRMED_or_NO_ACTIVE_OWNER"
    echo "active_carplay_preload=UNTIL_REBOOT"
    return 0
  fi
  # Enabling requires a valid existing persistent profile and a stock route.
  [ ! -e /tmp/mibr-parity-session.lock ] || fail "existing_owner"
  [ ! -e /tmp/mibr-isotx2-gate.direct ] || fail "gate_not_stock"
  "$HELPER" batch --input "$PROFILE" --layer temp || fail "profile_validation_failed"
  app_rw || fail "app_rw"
  echo 1 > "$ENABLED.new.$$" || fail "write_enable"
  mv "$ENABLED.new.$$" "$ENABLED" || fail "commit_enable"
  echo 1 > "$PARITY_ENABLED.new.$$" || fail "write_parity_enable"
  mv "$PARITY_ENABLED.new.$$" "$PARITY_ENABLED" || fail "commit_parity_enable"
  app_ro || fail "app_ro"
  echo "CPVC_CONFIG=ENABLED effective=NEXT_BOOT_OR_VERIFIED_SUPERVISOR_START"
  echo "reboot=NOT_AUTOMATIC"
}
zoom() {
  case "${1:-}" in
    status)
      if [ -e "$ZOOM" ]; then echo "zoom_v1=ARMED_VOLATILE"; else echo "zoom_v1=OFF"; fi
      if [ -r "$ZOOM_AUTOSTART" ] && [ "$(cat "$ZOOM_AUTOSTART" 2>/dev/null)" = 1 ]; then echo "zoom_boot_autostart=ON"; else echo "zoom_boot_autostart=OFF"; fi
      echo "parked_motion_sensor=NOT_IMPLEMENTED"
      ;;
    disarm) rm -f "$ZOOM" 2>/dev/null || fail "zoom_disarm"; echo "zoom_v1=OFF" ;;
    arm)
      [ "${2:-}" = PARKED ] || fail "zoom_arm_requires_literal_PARKED"
      enabled || fail "cpvc_disabled"
      [ ! -e "$ZOOM" ] || { echo "zoom_v1=ALREADY_ARMED"; return 0; }
      : > "$ZOOM" || fail "zoom_marker_write"
      echo "zoom_v1=ARMED_VOLATILE parked=OPERATOR_ATTESTED—not_vehicle_verified"
      ;;
    *) usage; return 2 ;;
  esac
}
case "${1:-help}" in
  ''|help|--help|-h) usage ;;
  status)
    echo "=== CPVC R5 internal profile ==="
    if enabled; then echo "cpvc_enabled=1"; else echo "cpvc_enabled=0"; fi
    if [ -r "$PARITY_ENABLED" ]; then echo "parity_enabled=$(cat "$PARITY_ENABLED" 2>/dev/null)"; else echo "parity_enabled=MISSING"; fi
    [ -r "$PROFILE" ] && cat "$PROFILE" || echo "profile=MISSING"
    echo "=== effective native settings (TEMP if loaded) ==="
    if [ -x "$HELPER" ]; then "$HELPER" status || fail "native_status"; else echo "native_helper=MISSING"; fi
    zoom status
    ;;
  _boot-replay) replay ;;
  enable) set_enable 1 ;;
  disable) set_enable 0 ;;
  set) [ "$#" -eq 3 ] || { usage; exit 2; }; set_value "$2" "$3" ;;
  zoom) shift; zoom "$@" ;;
  *) usage; exit 2 ;;
esac
