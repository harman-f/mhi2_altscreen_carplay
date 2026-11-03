#!/bin/ksh
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init_durable || { echo "ERROR runtime/bootstrap failed"; exit 15; }
runtime_require_cmds mount cp mv chmod awk grep sync mkdir rm || { log "ERROR required QNX command missing"; exit 16; }

HOOK_SRC=$BASE/bin/libaltscreen111.so
HOOK=$CARPLAY_HOOK
PATCHED=/tmp/smartphone_integrator.json.mibr-carplay111.$$
HOOK_TMP=$HOOK.new.$$

cleanup_patch(){
  rm -f "$PATCHED" "$HOOK_TMP" 2>/dev/null || true
}
trap cleanup_patch 0 1 2 15

[ -x "$HOOK_SRC" ] || { log "ERROR missing $HOOK_SRC"; exit 1; }
[ -r "$TARGET" ] || { log "ERROR missing $TARGET"; exit 1; }
load_altscreen_config || exit 1
prepare_log_storage || {
  echo "ERROR refusing patch: SD/log storage is not writable"
  echo "$(timestamp_now) ERROR SD/log storage is not writable" >> /tmp/altscreen-u2-control.log 2>/dev/null || true
  exit 14
}

H=$(hash256 /mnt/app/eso/lib/libairplay.so)
[ "$H" = "$EXPECTED_AIRPLAY" ] || { log "ERROR libairplay hash mismatch: $H"; exit 2; }

CURRENT=$(hash256 "$TARGET")
HOOK_SHA=$(hash256 "$HOOK_SRC") || { log "ERROR cannot hash source hook"; exit 17; }

# Keep the canonical stock backup on internal storage so recovery does not
# depend on the SD card remaining present.
mount -uw /mnt/app 2>/dev/null || { log "ERROR cannot mount /mnt/app rw"; exit 18; }
mkdir -p "$CARPLAY_BACKDIR" || {
  mount -ur /mnt/app 2>/dev/null || true
  log "ERROR cannot create $CARPLAY_BACKDIR"
  exit 19
}

if [ ! -r "$BACKUP" ]; then
  [ "$CURRENT" = "$EXPECTED_SMARTPHONE" ] || {
    mount -ur /mnt/app 2>/dev/null || true
    log "ERROR refusing first patch: smartphone_integrator hash $CURRENT is not canonical stock"
    exit 3
  }
  cp "$TARGET" "$BACKUP" || {
    mount -ur /mnt/app 2>/dev/null || true
    exit 4
  }
  chmod 644 "$BACKUP" 2>/dev/null || true
  echo "$EXPECTED_SMARTPHONE  $BACKUP" > "$BACKUP_SHA" 2>/dev/null || true
fi

B=$(hash256 "$BACKUP")
[ "$B" = "$EXPECTED_SMARTPHONE" ] || {
  mount -ur /mnt/app 2>/dev/null || true
  log "ERROR stock backup hash mismatch: $B"
  exit 5
}
if grep -Fq 'libaltscreen111.so' "$BACKUP" 2>/dev/null ||
   grep -Fq 'libmibr_carplay111.so' "$BACKUP" 2>/dev/null; then
  mount -ur /mnt/app 2>/dev/null || true
  log "ERROR stock backup is already patched"
  exit 6
fi
mount -ur /mnt/app 2>/dev/null || true

# smartphone_integrator has a tight environment-array budget. Keep this at
# exactly ten entries. The persistent LD_PRELOAD target is internal /mnt/app,
# not the SD card; therefore CarPlay child startup is independent of SD timing.
awk \
  -v hook="$HOOK" \
  -v altport="$ALTSCREEN111_PORT" \
  -v teeport="$ALTSCREEN111_TEE_PORT" \
  -v width="$ALTSCREEN111_WIDTH" \
  -v height="$ALTSCREEN111_HEIGHT" \
  -v fps="$ALTSCREEN111_FPS" \
  -v autoshow="$ALTSCREEN111_AUTO_SHOW" \
  -v url="$ALTSCREEN111_URL" '
BEGIN{in_children=0;in_carplay=0;patched=0}
{
 if($0 ~ /"children"[ \t]*:/) in_children=1
 if(in_children && !in_carplay && $0 ~ /^[ \t]*"carplay"[ \t]*:/) in_carplay=1
 if(in_carplay && !patched && $0 ~ /^[ \t]*"envs"[ \t]*:\[/){
   indent=$0; sub(/"envs".*/,"",indent)
   print indent "\"envs\":[\"LD_PRELOAD=" hook "\", \"ALTSCREEN111_PORT=" altport "\", \"ALTSCREEN111_TEE_PORT=" teeport "\", \"ALTSCREEN111_WIDTH=" width "\", \"ALTSCREEN111_HEIGHT=" height "\", \"ALTSCREEN111_FPS=" fps "\", \"ALTSCREEN111_AUTO_SHOW=" autoshow "\", \"ALTSCREEN111_URL=" url "\", \"LD_LIBRARY_PATH=/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib\", \"IPL_CONFIG_DIR_DIO_MANAGER=/etc/eso/production\"],"
   patched=1; next
 }
 print
}
END{if(!patched) exit 3}
' "$BACKUP" > "$PATCHED" || { log "ERROR could not patch carplay env array"; exit 7; }

grep -q "LD_PRELOAD=$HOOK" "$PATCHED" || exit 8
grep -q "ALTSCREEN111_WIDTH=$ALTSCREEN111_WIDTH" "$PATCHED" || exit 8
grep -q "ALTSCREEN111_HEIGHT=$ALTSCREEN111_HEIGHT" "$PATCHED" || exit 8
grep -q "ALTSCREEN111_URL=$ALTSCREEN111_URL" "$PATCHED" || exit 8
grep -q '"gal"' "$PATCHED" || exit 8
grep -q '"carlife"' "$PATCHED" || exit 8

P=$(hash256 "$PATCHED")
if [ "$CURRENT" != "$EXPECTED_SMARTPHONE" ] && [ "$CURRENT" != "$P" ]; then
  log "ERROR refusing overwrite: current config is neither stock nor exact generated U2 patch ($CURRENT)"
  exit 9
fi

# Stage the hook internally first. If this fails, the persistent config remains
# untouched and the next boot stays stock.
DEST_SHA=""
[ -r "$HOOK" ] && DEST_SHA=$(hash256 "$HOOK" 2>/dev/null)
if [ "$DEST_SHA" != "$HOOK_SHA" ]; then
  mount -uw /mnt/app 2>/dev/null || { log "ERROR cannot mount /mnt/app rw for hook install"; exit 10; }
  cp "$HOOK_SRC" "$HOOK_TMP" &&
  chmod 755 "$HOOK_TMP" 2>/dev/null &&
  mv "$HOOK_TMP" "$HOOK"
  RC=$?
  sync
  mount -ur /mnt/app 2>/dev/null || true
  [ $RC -eq 0 ] || { log "ERROR cannot install persistent CarPlay111 hook"; exit 11; }
fi

DEST_SHA=$(hash256 "$HOOK")
[ "$DEST_SHA" = "$HOOK_SHA" ] || {
  log "ERROR persistent hook hash mismatch source=$HOOK_SHA installed=$DEST_SHA"
  exit 12
}

if [ "$CURRENT" != "$P" ]; then
  mount -uw /mnt/system 2>/dev/null || { log "ERROR cannot mount /mnt/system rw"; exit 20; }
  cp "$PATCHED" "$TARGET.u2-new" &&
  chmod 644 "$TARGET.u2-new" 2>/dev/null &&
  mv "$TARGET.u2-new" "$TARGET"
  RC=$?
  sync
  mount -ur /mnt/system 2>/dev/null || true
  [ $RC -eq 0 ] || exit $RC
fi

FINAL=$(hash256 "$TARGET")
[ "$FINAL" = "$P" ] || {
  log "ERROR post-install smartphone_integrator hash mismatch expected=$P actual=$FINAL"
  exit 21
}

log "installed persistent stream111 preload; hook=$HOOK sha256=$HOOK_SHA"
log "source=${ALTSCREEN111_WIDTH}x${ALTSCREEN111_HEIGHT}@${ALTSCREEN111_FPS}; tee=$ALTSCREEN111_TEE_PORT"
log "REBOOT_REQUIRED=YES; do not hot-restart smartphone_integrator/dio_manager"
exit 0
