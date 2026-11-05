#!/bin/ksh
# NOTE: frozen legacy release line, installs the pre-MIBR altscreen-u2 layout; superseded by the MIB Runtime installer.
# Its hash-pinned payload binaries are vehicle-tested with compiled altscreen-u2 paths; do not switch these paths here.
set -u

SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2

DST=/mnt/app/root/altscreen-u2
LSD=/mnt/app/eso/hmi/lsd/lsd.sh
PAYLOAD=$ROOT/payload
SHA=${MIBR_SHA256:-$PAYLOAD/sha256sum}
TEE=${MIBR_TEE:-$PAYLOAD/tee}
SESSION_HELPER=$ROOT/runtime/deployment/session.sh

[ -r "$SESSION_HELPER" ] || { echo "MIBR_UNINSTALL=FAIL missing_session_helper=$SESSION_HELPER"; exit 20; }
. "$SESSION_HELPER" || { echo "MIBR_UNINSTALL=FAIL cannot_source_session_helper"; exit 20; }

if [ "${MIBR_LOG_ACTIVE:-0}" != "1" ]; then
  [ -x "$SHA" ] || { echo "MIBR_UNINSTALL=FAIL missing_sha256_helper=$SHA"; exit 20; }
  [ -x "$TEE" ] || { echo "MIBR_UNINSTALL=FAIL missing_tee_helper=$TEE"; exit 20; }
  mibr_prepare_session uninstall "$ROOT" "$TEE" "$SHA" || {
    echo "MIBR_UNINSTALL=FAIL cannot_create_sd_issue_log rc=$?"
    exit 20
  }
  echo "Logging complete uninstall session to $MIBR_LOG_FILE"
  mibr_run_logged "$0" "$@"
  exit $?
fi

mibr_vehicle_summary || echo "WARN vehicle_summary_failed"

OWNED=/mnt/app/root/mibr-deploy-navignore-owned
MOSTOWNED=/mnt/app/root/mibr-deploy-most20-owned
# Stage in the lsd.sh directory itself, not in /tmp (RAM): the final mv is
# then a same-filesystem rename whatever the mount layout under /mnt/app is.
TMP=/mnt/app/eso/hmi/lsd/lsd.sh.mibr-deploy-java-remove.$$
# Integrity gate for a rewritten lsd.sh before it replaces the original:
# the J9 start-line count must be unchanged and BEGIN/END marker lines must
# form exactly WANT ordered pairs (WANT=- skips the pair check).
lsd_check(){
  awk -v b="$2" -v e="$3" -v want="$4" -v orig="$5" '
    b != "" && $0 == b { nb++; if (open) bad=1; open=1 }
    e != "" && $0 == e { ne++; if (!open) bad=1; open=0 }
    /^\$J9/ { nj++ }
    END {
      if (nj != orig || nj < 1) exit 1
      if (want != "-" && (bad || open || nb != want || ne != want)) exit 1
    }
  ' "$1"
}
j9_count(){
  awk '/^\$J9/ { n++ } END { print n+0 }' "$1"
}

FAIL=0

echo "=== MHI2 AltScreen MU1440 developer uninstall ==="
[ -x "$SHA" ] || { echo "MIBR_UNINSTALL=FAIL missing_sha256_helper=$SHA"; exit 20; }

if [ -x "$DST/scripts/direct_ts_auto_disable.sh" ]; then
  "$DST/scripts/direct_ts_auto_disable.sh" || FAIL=1
fi
if [ -x "$DST/scripts/direct_ts_auto_stop.sh" ]; then
  "$DST/scripts/direct_ts_auto_stop.sh" || FAIL=1
else
  rm -f /tmp/mibr-isotx2-gate.direct 2>/dev/null || true
fi

if [ -e "$OWNED" ]; then
  echo "Removing deployment-owned NavIgnore"
  if mount -uw /mnt/app 2>/dev/null; then
    awk '
      $0 == "# MIBR NAVIGNORE" { next }
      index($0, "-Xbootclasspath/p:$BASE_DIR/lsd/jars/MIBR-NavIgnore.jar") { next }
      { print }
    ' "$LSD" > "$TMP" &&
    lsd_check "$TMP" "" "" - "$(j9_count "$LSD")" &&
    chmod 755 "$TMP" 2>/dev/null &&
    mv "$TMP" "$LSD"
    RC=$?
    if [ "$RC" -eq 0 ]; then
      rm -f /mnt/app/eso/hmi/lsd/jars/MIBR-NavIgnore.jar "$OWNED" 2>/dev/null || true
    else
      rm -f "$TMP" 2>/dev/null || true
      FAIL=1
    fi
    sync
    mount -ur /mnt/app 2>/dev/null || {
      echo "ERROR /mnt/app did not return to read-only"
      FAIL=1
    }
  else
    FAIL=1
  fi
else
  echo "NavIgnore not owned by deployment; leaving it untouched."
fi

if [ -e "$MOSTOWNED" ]; then
  echo "Removing deployment-owned Most20FPS"
  if mount -uw /mnt/app 2>/dev/null; then
    awk '
      $0 == "# MIBR MOST20FPS" { next }
      index($0, "-Xbootclasspath/p:$BASE_DIR/lsd/jars/MIBR-Most20FPS.jar") { next }
      { print }
    ' "$LSD" > "$TMP" &&
    lsd_check "$TMP" "" "" - "$(j9_count "$LSD")" &&
    chmod 755 "$TMP" 2>/dev/null &&
    mv "$TMP" "$LSD"
    RC=$?
    if [ "$RC" -eq 0 ]; then
      rm -f /mnt/app/eso/hmi/lsd/jars/MIBR-Most20FPS.jar "$MOSTOWNED" 2>/dev/null || true
    else
      rm -f "$TMP" 2>/dev/null || true
      FAIL=1
    fi
    sync
    mount -ur /mnt/app 2>/dev/null || {
      echo "ERROR /mnt/app did not return to read-only"
      FAIL=1
    }
  else
    FAIL=1
  fi
else
  echo "Most20FPS not owned by deployment; leaving it untouched."
fi

# Parity-drive keeps its boot hook on disable by design; uninstall removes
# it, because the supervisor it starts stays under $DST after uninstall.
PARITY_BEGIN="# MIBR PARITY-DRIVE BEGIN"
PARITY_END="# MIBR PARITY-DRIVE END"
if grep -F "$PARITY_BEGIN" "$LSD" >/dev/null 2>&1; then
  echo "Removing parity-drive boot hook"
  if [ -x "$DST/scripts/parity_drive_disable.sh" ]; then
    "$DST/scripts/parity_drive_disable.sh" || FAIL=1
  fi
  if mount -uw /mnt/app 2>/dev/null; then
    awk -v b="$PARITY_BEGIN" -v e="$PARITY_END" '
      $0 == b { skip=1; next }
      skip && $0 == e { skip=0; next }
      !skip { print }
      END { if (skip) exit 42 }
    ' "$LSD" > "$TMP"
    ARC=$?
    if [ "$ARC" -eq 0 ] && lsd_check "$TMP" "$PARITY_BEGIN" "$PARITY_END" 0 "$(j9_count "$LSD")"; then
      chmod 755 "$TMP" 2>/dev/null || true
      if mv "$TMP" "$LSD"; then
        echo 0 > /mnt/app/root/mibr-parity-drive.enabled 2>/dev/null || true
        echo "Parity-drive boot hook removed"
      else
        rm -f "$TMP" 2>/dev/null || true
        echo "ERROR parity-drive boot hook replacement failed"
        FAIL=1
      fi
    else
      rm -f "$TMP" 2>/dev/null || true
      echo "ERROR malformed parity-drive boot hook; lsd.sh left unchanged"
      FAIL=1
    fi
    sync
    mount -ur /mnt/app 2>/dev/null || {
      echo "ERROR /mnt/app did not return to read-only"
      FAIL=1
    }
  else
    echo "ERROR cannot mount /mnt/app rw to remove the parity-drive boot hook"
    FAIL=1
  fi
fi

echo "Restoring DisplayManager startup"
MIBR_SHA256="$SHA" "$ROOT/runtime/isotx2-gate/restore_preload.sh" || FAIL=1

echo "Restoring stock smartphone_integrator configuration"
if [ -x "$DST/scripts/restore_stock.sh" ]; then
  "$DST/scripts/restore_stock.sh"
  RC=$?
  case "$RC" in 0|21) ;; *) FAIL=1 ;; esac
else
  echo "WARN internal restore_stock.sh missing"
  FAIL=1
fi

rm -f /tmp/mibr-alt111-keyframe-policy.enabled /tmp/mibr-alt111-resync.enabled /tmp/mibr-alt111-resync-arm 2>/dev/null || true

# The persistent D2 marker lives on /mnt/app, which every step above has
# already returned to read-only. Remove it inside its own RW window and
# report a marker that survives, instead of hiding the failure. Only a
# marker the installer created (ownership file) is removed; one the user or
# another tool created stays. The install-defaults receipt goes as well, so
# a later install applies the defaults again.
D2_MARKER=/mnt/app/root/mibr-alt111-keyframe-policy.enabled
D2_OWNED=$DST/version/ownership/d2-marker.owned
RECEIPT=$DST/version/install-defaults.receipt
if [ -e "$D2_MARKER" ] && [ ! -e "$D2_OWNED" ]; then
  echo "Persistent D2 marker not created by the installer; left in place"
elif [ -e "$D2_MARKER" ]; then
  if mount -uw /mnt/app 2>/dev/null; then
    rm -f "$D2_MARKER" 2>/dev/null || true
    sync
    mount -ur /mnt/app 2>/dev/null || {
      echo "ERROR /mnt/app did not return to read-only"
      FAIL=1
    }
  fi
  if [ -e "$D2_MARKER" ]; then
    echo "ERROR persistent D2 marker survived uninstall: $D2_MARKER"
    FAIL=1
  else
    echo "Persistent D2 marker removed"
  fi
fi
if [ -e "$D2_OWNED" ] || [ -e "$RECEIPT" ]; then
  if mount -uw /mnt/app 2>/dev/null; then
    [ -e "$D2_MARKER" ] || rm -f "$D2_OWNED" 2>/dev/null || true
    rm -f "$RECEIPT" 2>/dev/null || true
    sync
    mount -ur /mnt/app 2>/dev/null || {
      echo "ERROR /mnt/app did not return to read-only"
      FAIL=1
    }
  fi
  if [ -e "$RECEIPT" ]; then
    echo "ERROR install-defaults receipt survived uninstall: $RECEIPT"
    FAIL=1
  fi
fi

if [ "$FAIL" -ne 0 ]; then
  echo "MIBR_UNINSTALL=COMPLETED_WITH_ERRORS"
  exit 20
fi

echo "MIBR_UNINSTALL=PASS"
echo "REBOOT_REQUIRED=YES"
echo "Runtime/evidence files under $DST are intentionally retained."
exit 0
