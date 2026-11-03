#!/bin/ksh
. /mnt/app/root/altscreen-u2/scripts/common.sh
FAIL=0
REBOOT_REQUIRED=0
CURRENT_BEFORE=$(hash256 "$TARGET" 2>/dev/null)
if [ -n "$CURRENT_BEFORE" ] && [ "$CURRENT_BEFORE" != "$EXPECTED_SMARTPHONE" ]; then
  REBOOT_REQUIRED=1
fi
if ! runtime_init; then
  echo "ERROR restore runtime bootstrap failed; refusing unverified persistent file replacement"
  FAIL=1
fi

# Auto-Direct is U2-owned runtime state. Full restore must make STOCK the
# fail-safe state before touching the persistent CarPlay preload.
AUTO_ENABLED=/mnt/app/root/mibr-carplay-autodirect.enabled
AUTO_BEGIN="# MIBR AUTO-DIRECT BEGIN"
AUTO_END="# MIBR AUTO-DIRECT END"
AUTO_TMP=/tmp/lsd.sh.mibr-autodirect-remove.$$

if [ -x "$BASE/scripts/direct_ts_auto_stop.sh" ]; then
  "$BASE/scripts/direct_ts_auto_stop.sh" >/dev/null 2>&1 || {
    rm -f /tmp/mibr-isotx2-gate.direct 2>/dev/null || true
    log "WARN Auto-Direct stop helper returned nonzero; forced gate marker removal"
  }
else
  rm -f /tmp/mibr-isotx2-gate.direct 2>/dev/null || true
fi

if [ -e "$AUTO_ENABLED" ] || grep -Fq "$AUTO_BEGIN" /mnt/app/eso/hmi/lsd/lsd.sh 2>/dev/null; then
  if mount -uw /mnt/app 2>/dev/null; then
    rm -f "$AUTO_ENABLED" 2>/dev/null || true
    if grep -Fq "$AUTO_BEGIN" /mnt/app/eso/hmi/lsd/lsd.sh 2>/dev/null; then
      awk -v b="$AUTO_BEGIN" -v e="$AUTO_END" '
        $0 == b { skip=1; next }
        skip && $0 == e { skip=0; next }
        !skip { print }
        END { if (skip) exit 42 }
      ' /mnt/app/eso/hmi/lsd/lsd.sh > "$AUTO_TMP"
      ARC=$?
      if [ "$ARC" -eq 0 ]; then
        chmod 755 "$AUTO_TMP" 2>/dev/null || true
        if mv "$AUTO_TMP" /mnt/app/eso/hmi/lsd/lsd.sh; then
          log "Auto-Direct boot hook removed"
        else
          rm -f "$AUTO_TMP" 2>/dev/null || true
          log "ERROR Auto-Direct boot hook replacement failed"
          FAIL=1
        fi
      else
        rm -f "$AUTO_TMP" 2>/dev/null || true
        log "ERROR malformed Auto-Direct boot hook; refusing partial removal"
        FAIL=1
      fi
    fi
    sync
    mount -ur /mnt/app 2>/dev/null || true
  else
    log "ERROR cannot mount /mnt/app rw to clear Auto-Direct persistence"
    FAIL=1
  fi
fi

slay -9 stream-player 2>/dev/null || true
slay -9 altscreen-capture 2>/dev/null || true
slay -9 direct-ts-remux 2>/dev/null || true
slay -9 most-ts-writer 2>/dev/null || true

if ! stock_route >/dev/null 2>&1; then
  log "ERROR initial stock VC route request failed"
  FAIL=1
fi

if [ -r "$BACKUP" ]; then
  B=$(hash256 "$BACKUP")
  if [ "$B" = "$EXPECTED_SMARTPHONE" ]; then
    if mount -uw /mnt/system 2>/dev/null; then
      if cp "$BACKUP" "$TARGET.restore" &&
         chmod 644 "$TARGET.restore" 2>/dev/null &&
         mv "$TARGET.restore" "$TARGET"; then
        sync
        log "stock smartphone_integrator.json restored"
      else
        log "ERROR restoring smartphone_integrator.json"
        rm -f "$TARGET.restore" 2>/dev/null || true
        FAIL=1
      fi
      mount -ur /mnt/system 2>/dev/null || true
    else
      log "ERROR cannot mount /mnt/system rw for restore"
      FAIL=1
    fi
  else
    log "ERROR refusing restore: backup SHA mismatch $B"
    FAIL=1
  fi
else
  C=$(hash256 "$TARGET")
  if [ "$C" = "$EXPECTED_SMARTPHONE" ]; then
    log "no stock backup found; target already canonical stock"
  else
    log "ERROR no stock backup and current smartphone_integrator is not canonical stock ($C)"
    FAIL=1
  fi
fi

# Verify the persistent file after any attempted restore. Do not report a
# successful FULL RESTORE unless the exact canonical stock bytes are present.
C=$(hash256 "$TARGET")
if [ "$C" != "$EXPECTED_SMARTPHONE" ]; then
  log "ERROR restore verification failed: smartphone_integrator SHA=$C"
  FAIL=1
fi

# Once the persistent stock config no longer references the hook, remove the
# internal preload file as well. A currently running CarPlay process may still
# have it mapped, so REBOOT_REQUIRED remains the authoritative unload boundary.
# A full CarPlay111 rollback also clears optional protocol-experiment markers.
if [ "$C" = "$EXPECTED_SMARTPHONE" ] && [ -e /mnt/app/root/mibr-carplay111-viewareas.enabled ]; then
  if mount -uw /mnt/app 2>/dev/null; then
    rm -f /mnt/app/root/mibr-carplay111-viewareas.enabled 2>/dev/null || true
    sync
    mount -ur /mnt/app 2>/dev/null || true
    [ ! -e /mnt/app/root/mibr-carplay111-viewareas.enabled ] || {
      log "ERROR ViewArea fallback marker could not be removed"
      FAIL=1
    }
  else
    log "ERROR cannot mount /mnt/app rw to clear ViewArea fallback marker"
    FAIL=1
  fi
fi

if [ "$C" = "$EXPECTED_SMARTPHONE" ] && [ -e "$CARPLAY_HOOK" ]; then
  if mount -uw /mnt/app 2>/dev/null; then
    rm -f "$CARPLAY_HOOK" "$CARPLAY_HOOK".new.* 2>/dev/null || true
    sync
    mount -ur /mnt/app 2>/dev/null || true
    if [ -e "$CARPLAY_HOOK" ]; then
      log "ERROR persistent CarPlay111 hook could not be removed"
      FAIL=1
    else
      log "persistent CarPlay111 hook removed"
      REBOOT_REQUIRED=1
    fi
  else
    log "ERROR cannot mount /mnt/app rw to remove persistent CarPlay111 hook"
    FAIL=1
  fi
fi

# Do not restart smartphone_integrator/dio_manager here. Vehicle run 1 proved
# repeated hard restarts can exhaust/break the service stack. Persistent stock
# bytes are restored first; reboot is the recovery boundary if the hook was
# loaded or the CarPlay process stack is unhealthy.
if ! carplay_stack_health; then
  log "WARN stock file restored but CarPlay process stack is incomplete"
  REBOOT_REQUIRED=1
fi

if ! stock_route >/dev/null 2>&1; then
  log "ERROR final stock VC route request failed"
  FAIL=1
fi

if [ "$FAIL" -ne 0 ]; then
  log "U2 restore completed with errors; inspect control/dmdt logs before reboot"
  exit 20
fi

if [ "$REBOOT_REQUIRED" -ne 0 ]; then
  log "STOCK FILE VERIFIED; REBOOT_REQUIRED for clean CarPlay process/hook recovery"
  exit 21
fi

log "U2 stopped; exact stock config verified; CarPlay process stack present; stock VC route requested"
exit 0
