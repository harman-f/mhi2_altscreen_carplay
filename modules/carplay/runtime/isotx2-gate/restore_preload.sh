#!/bin/ksh
set -u

SELF=$0
case "$SELF" in */*) BASE=${SELF%/*} ;; *) BASE=. ;; esac
BASE=$(cd "$BASE" 2>/dev/null && pwd) || exit 2
HASH="${MIBR_SHA256:-$BASE/../../payload/sha256sum}"
TARGET=/mnt/system/etc/boot/startup.sh
DST_LIB=/mnt/app/eso/lib/libmibr_isotx2_gate.so
BACKUP=/mnt/app/root/mibr-isotx2-gate-backup/startup.sh.stock
DISABLE_MARKER=/mnt/app/root/mibr-isotx2-gate-disable
TMP=/tmp/startup.sh.mibr-isotx2-restore.$$
LEGACYTMP=/tmp/startup.sh.mibr-isotx2-legacy.$$
BLOCK=/tmp/startup.sh.mibr-isotx2-block.$$

EXPECTED_STOCK=869a64efbb3c0423951c2c31899743f4c635871b8c81236a459df36ee41793b8
EXPECTED_SIZE=33908
STOCK_LINE='    MALLOC_ARENA_CACHE_MAXSZ=400000 on -p 15 /eso/bin/apps/displaymanager ${DM_EXTRA_OPTS} ${LVDS2} &'

cleanup()
{
    rm -f "$TMP" "$LEGACYTMP" "$BLOCK" 2>/dev/null || true
}
trap cleanup 0 1 2 15

hashf()
{
    "$HASH" "$1" 2>/dev/null | awk '{print $1}'
}

make_block()
{
    cat > "$BLOCK" <<'MIBR_EOF'
    # MIBR ISOTX2 GATE BEGIN
    # Preload is enabled by default. A persistent disable marker or a missing
    # gate library forces the exact stock DisplayManager command.
    if [ -f /mnt/app/root/mibr-isotx2-gate-disable ] || [ ! -r /mnt/app/eso/lib/libmibr_isotx2_gate.so ]; then
    MALLOC_ARENA_CACHE_MAXSZ=400000 on -p 15 /eso/bin/apps/displaymanager ${DM_EXTRA_OPTS} ${LVDS2} &
    else
        LD_PRELOAD=/mnt/app/eso/lib/libmibr_isotx2_gate.so MALLOC_ARENA_CACHE_MAXSZ=400000 on -p 15 /eso/bin/apps/displaymanager ${DM_EXTRA_OPTS} ${LVDS2} &
    fi
    # MIBR ISOTX2 GATE END
MIBR_EOF
}

make_legacy_block()
{
    cat > "$BLOCK" <<'MIBR_EOF'
    # MIBR ISOTX2 GATE BEGIN
    # Fail-safe opt-in: if the SD marker is absent or the SD is not mounted
    # yet, start the exact stock DisplayManager command without LD_PRELOAD.
    if [ -f /fs/sda0/mibr-enable-isotx2-gate ] && [ -r /mnt/app/eso/lib/libmibr_isotx2_gate.so ]; then
        LD_PRELOAD=/mnt/app/eso/lib/libmibr_isotx2_gate.so MALLOC_ARENA_CACHE_MAXSZ=400000 on -p 15 /eso/bin/apps/displaymanager ${DM_EXTRA_OPTS} ${LVDS2} &
    else
    MALLOC_ARENA_CACHE_MAXSZ=400000 on -p 15 /eso/bin/apps/displaymanager ${DM_EXTRA_OPTS} ${LVDS2} &
    fi
    # MIBR ISOTX2 GATE END
MIBR_EOF
}

generate_from_stock()
{
    IN="$1"
    OUT="$2"
    MODE="$3"

    if [ "$MODE" = "legacy" ]; then
        make_legacy_block || return 1
    else
        make_block || return 1
    fi

    awk -v stock="$STOCK_LINE" -v block="$BLOCK" '
    BEGIN {
        n=0
        hits=0
        while ((getline line < block) > 0) b[++n]=line
        close(block)
    }
    {
        if ($0 == stock) {
            for (i=1; i<=n; i++) print b[i]
            hits++
            next
        }
        print
    }
    END { if (hits != 1) exit 42 }
    ' "$IN" > "$OUT"
}

echo "=== MU1440 isoTX2 DisplayManager preload restore ==="
[ -x "$HASH" ] || { echo "FAIL missing hash helper"; exit 20; }
[ -r "$TARGET" ] || { echo "FAIL missing persistent startup"; exit 21; }

CURRENT=$(hashf "$TARGET")
if [ "$CURRENT" = "$EXPECTED_STOCK" ]; then
    echo "startup_state=already_stock"
else
    [ -r "$BACKUP" ] || { echo "FAIL no stock backup at $BACKUP"; exit 22; }
    BH=$(hashf "$BACKUP")
    [ "$BH" = "$EXPECTED_STOCK" ] || {
        echo "FAIL backup hash mismatch: $BH"
        exit 23
    }

    generate_from_stock "$BACKUP" "$TMP" new || {
        echo "FAIL cannot regenerate expected current MIBR patch"
        exit 24
    }
    NEW_HASH=$(hashf "$TMP")

    generate_from_stock "$BACKUP" "$LEGACYTMP" legacy || {
        echo "FAIL cannot regenerate expected legacy SD patch"
        exit 25
    }
    LEGACY_HASH=$(hashf "$LEGACYTMP")

    if [ "$CURRENT" = "$NEW_HASH" ]; then
        echo "startup_state=new_patch"
    elif [ "$CURRENT" = "$LEGACY_HASH" ]; then
        echo "startup_state=legacy_sd_patch"
    else
        echo "FAIL current startup is neither exact new MIBR patch nor exact legacy SD patch"
        echo " current=$CURRENT"
        echo " expected_new=$NEW_HASH"
        echo " expected_legacy=$LEGACY_HASH"
        exit 26
    fi

    /bin/sh -n "$BACKUP" >/dev/null 2>&1 || { echo "FAIL stock backup rejected by /bin/sh -n"; exit 27; }
    /bin/ksh -n "$BACKUP" >/dev/null 2>&1 || { echo "FAIL stock backup rejected by /bin/ksh -n"; exit 28; }

    mount -uw /mnt/system 2>/dev/null || { echo "FAIL cannot remount /mnt/system rw"; exit 29; }
    cp "$BACKUP" "$TARGET.restore" &&
    chmod 755 "$TARGET.restore" 2>/dev/null &&
    mv "$TARGET.restore" "$TARGET"
    RC=$?
    sync
    mount -ur /mnt/system 2>/dev/null || true
    [ "$RC" -eq 0 ] || { echo "FAIL restore copy"; exit 30; }
fi

FINAL=$(hashf "$TARGET")
[ "$FINAL" = "$EXPECTED_STOCK" ] || {
    echo "FAIL final startup hash is not canonical stock: $FINAL"
    exit 31
}

set -- $(wc -c < "$TARGET" 2>/dev/null)
[ "$1" = "$EXPECTED_SIZE" ] || { echo "FAIL final startup size mismatch: $1"; exit 32; }

rm -f /tmp/mibr-isotx2-gate.direct /tmp/mibr-isotx2-gate.reset 2>/dev/null || true

if mount -uw /mnt/app 2>/dev/null; then
    rm -f "$DST_LIB" "$DST_LIB.new" "$DISABLE_MARKER" 2>/dev/null || true
    sync
    mount -ur /mnt/app 2>/dev/null || true
fi

echo "RESTORE=PASS"
echo "startup_sha256=$FINAL"
echo "DIRECT_MARKER=ABSENT"
echo "PRELOAD_DISABLE_MARKER=ABSENT"
echo "REBOOT_REQUIRED=YES"
exit 0
