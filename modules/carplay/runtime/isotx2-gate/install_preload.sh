#!/bin/ksh
set -u

SELF=$0
case "$SELF" in */*) BASE=${SELF%/*} ;; *) BASE=. ;; esac
BASE=$(cd "$BASE" 2>/dev/null && pwd) || exit 2
SRC_LIB="${MIBR_GATE_LIB:-$BASE/../../payload/libmibr_isotx2_gate.so}"
HASH="${MIBR_SHA256:-$BASE/../../payload/sha256sum}"

TARGET=/mnt/system/etc/boot/startup.sh
RUNTIME=/etc/boot/startup.sh
DST_LIB=/mnt/app/eso/lib/libmibr_isotx2_gate.so
BACKDIR=/mnt/app/root/mibr-isotx2-gate-backup
BACKUP="$BACKDIR/startup.sh.stock"
DISABLE_MARKER=/mnt/app/root/mibr-isotx2-gate-disable
TMP=/tmp/startup.sh.mibr-isotx2.$$
CHECKTMP=/tmp/startup.sh.mibr-isotx2-check.$$
LEGACYTMP=/tmp/startup.sh.mibr-isotx2-legacy.$$
BLOCK=/tmp/startup.sh.mibr-isotx2-block.$$
SHLOG=/tmp/startup.sh.mibr-isotx2-sh.$$
KSHLOG=/tmp/startup.sh.mibr-isotx2-ksh.$$

EXPECTED_STOCK=869a64efbb3c0423951c2c31899743f4c635871b8c81236a459df36ee41793b8
EXPECTED_SIZE=33908
EXPECTED_LIB=05673010a88c25022145ffb4e75d3715eaf686f4127ac188e91a52f512b9d957

STOCK_LINE='    MALLOC_ARENA_CACHE_MAXSZ=400000 on -p 15 /eso/bin/apps/displaymanager ${DM_EXTRA_OPTS} ${LVDS2} &'
GATE_LINE='        LD_PRELOAD=/mnt/app/eso/lib/libmibr_isotx2_gate.so MALLOC_ARENA_CACHE_MAXSZ=400000 on -p 15 /eso/bin/apps/displaymanager ${DM_EXTRA_OPTS} ${LVDS2} &'
DISABLE_IF='    if [ -f /mnt/app/root/mibr-isotx2-gate-disable ] || [ ! -r /mnt/app/eso/lib/libmibr_isotx2_gate.so ]; then'
LEGACY_SD_IF='    if [ -f /fs/sda0/mibr-enable-isotx2-gate ] && [ -r /mnt/app/eso/lib/libmibr_isotx2_gate.so ]; then'
BEGIN_LINE='    # MIBR ISOTX2 GATE BEGIN'
END_LINE='    # MIBR ISOTX2 GATE END'

cleanup()
{
    rm -f "$TMP" "$CHECKTMP" "$LEGACYTMP" "$BLOCK" "$SHLOG" "$KSHLOG" 2>/dev/null || true
}
trap 'cleanup; exit 129' 1
trap 'cleanup; exit 130' 2
trap 'cleanup; exit 143' 15
trap cleanup 0

hashf()
{
    "$HASH" "$1" 2>/dev/null | awk '{print $1}'
}

filesize()
{
    set -- $(wc -c < "$1" 2>/dev/null)
    echo "$1"
}

count_exact()
{
    awk -v wanted="$2" 'BEGIN{n=0} $0==wanted{n++} END{print n+0}' "$1"
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
        while ((getline line < block) > 0) {
            b[++n]=line
        }
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
    END {
        if (hits != 1) exit 42
    }
    ' "$IN" > "$OUT"
}

validate_new_patch()
{
    F="$1"

    BC=$(count_exact "$F" "$BEGIN_LINE")
    EC=$(count_exact "$F" "$END_LINE")
    SC=$(count_exact "$F" "$STOCK_LINE")
    GC=$(count_exact "$F" "$GATE_LINE")
    DC=$(count_exact "$F" "$DISABLE_IF")

    echo "generated_begin_count=$BC"
    echo "generated_end_count=$EC"
    echo "generated_stock_fallback_count=$SC"
    echo "generated_gate_launch_count=$GC"
    echo "generated_disable_guard_count=$DC"

    [ "$BC" = "1" ] || { echo "FAIL generated BEGIN marker count"; return 60; }
    [ "$EC" = "1" ] || { echo "FAIL generated END marker count"; return 61; }
    [ "$SC" = "1" ] || { echo "FAIL exact stock fallback is not present exactly once"; return 62; }
    [ "$GC" = "1" ] || { echo "FAIL gate DisplayManager launch is not present exactly once"; return 63; }
    [ "$DC" = "1" ] || { echo "FAIL persistent disable guard is not present exactly once"; return 64; }

    : > "$SHLOG"
    /bin/sh -n "$F" >"$SHLOG" 2>&1
    RC=$?
    if [ "$RC" -ne 0 ]; then
        echo "FAIL /bin/sh -n rejected generated startup.sh rc=$RC"
        cat "$SHLOG"
        return 65
    fi
    echo "qnx_sh_syntax=PASS"

    : > "$KSHLOG"
    /bin/ksh -n "$F" >"$KSHLOG" 2>&1
    RC=$?
    if [ "$RC" -ne 0 ]; then
        echo "FAIL /bin/ksh -n rejected generated startup.sh rc=$RC"
        cat "$KSHLOG"
        return 66
    fi
    echo "qnx_ksh_syntax=PASS"
    return 0
}

classify_current()
{
    TH="$1"

    if [ "$TH" = "$EXPECTED_STOCK" ]; then
        echo "STOCK"
        return 0
    fi

    [ -r "$BACKUP" ] || {
        echo "UNKNOWN"
        return 0
    }

    BH=$(hashf "$BACKUP")
    [ "$BH" = "$EXPECTED_STOCK" ] || {
        echo "UNKNOWN"
        return 0
    }

    generate_from_stock "$BACKUP" "$CHECKTMP" new || {
        echo "UNKNOWN"
        return 0
    }
    EH=$(hashf "$CHECKTMP")
    if [ "$TH" = "$EH" ]; then
        echo "NEW"
        return 0
    fi

    generate_from_stock "$BACKUP" "$LEGACYTMP" legacy || {
        echo "UNKNOWN"
        return 0
    }
    LH=$(hashf "$LEGACYTMP")
    if [ "$TH" = "$LH" ]; then
        echo "LEGACY_SD"
        return 0
    fi

    echo "UNKNOWN"
}

preflight()
{
    [ -x "$HASH" ] || { echo "FAIL missing executable hash helper: $HASH"; return 20; }
    [ -s "$SRC_LIB" ] || { echo "FAIL missing gate library: $SRC_LIB"; return 21; }
    [ "$EXPECTED_LIB" != "BUILD_PENDING" ] || { echo "FAIL installer was not finalized by CI"; return 22; }
    [ -r "$TARGET" ] || { echo "FAIL missing persistent startup file: $TARGET"; return 23; }
    [ -r "$RUNTIME" ] || { echo "FAIL missing runtime startup file: $RUNTIME"; return 24; }

    LH=$(hashf "$SRC_LIB")
    [ "$LH" = "$EXPECTED_LIB" ] || {
        echo "FAIL gate library hash mismatch"
        echo " expected=$EXPECTED_LIB"
        echo " actual=$LH"
        return 25
    }

    TH=$(hashf "$TARGET")
    RH=$(hashf "$RUNTIME")
    TS=$(filesize "$TARGET")
    RS=$(filesize "$RUNTIME")

    echo "persistent_startup_sha256=$TH"
    echo "runtime_startup_sha256=$RH"
    echo "persistent_startup_size=$TS"
    echo "runtime_startup_size=$RS"
    echo "gate_library_sha256=$LH"
    echo "disable_marker=$DISABLE_MARKER"

    [ "$TH" = "$RH" ] || {
        echo "FAIL runtime/persistent startup mismatch; reboot or restore before migration"
        return 26
    }

    STATE=$(classify_current "$TH")
    echo "detected_startup_state=$STATE"

    case "$STATE" in
        STOCK)
            [ "$TS" = "$EXPECTED_SIZE" ] || { echo "FAIL stock startup size mismatch"; return 27; }
            [ "$RS" = "$EXPECTED_SIZE" ] || { echo "FAIL runtime stock startup size mismatch"; return 28; }
            SC=$(count_exact "$TARGET" "$STOCK_LINE")
            [ "$SC" = "1" ] || { echo "FAIL expected exactly one stock DisplayManager line"; return 29; }
            SOURCE="$TARGET"
            ;;
        LEGACY_SD|NEW)
            [ -r "$BACKUP" ] || { echo "FAIL exact stock backup missing"; return 30; }
            BH=$(hashf "$BACKUP")
            [ "$BH" = "$EXPECTED_STOCK" ] || { echo "FAIL stock backup hash mismatch: $BH"; return 31; }
            SOURCE="$BACKUP"
            echo "backup_sha256=$BH"
            ;;
        *)
            echo "FAIL persistent startup is neither exact stock, exact legacy SD patch, nor exact new MIBR patch"
            return 32
            ;;
    esac

    generate_from_stock "$SOURCE" "$CHECKTMP" new || {
        echo "FAIL could not generate candidate startup patch"
        return 33
    }
    validate_new_patch "$CHECKTMP" || return $?
    EH=$(hashf "$CHECKTMP")
    echo "candidate_patched_sha256=$EH"

    case "$STATE" in
        STOCK) echo "INSTALL_STATE=STOCK_READY" ;;
        LEGACY_SD) echo "INSTALL_STATE=LEGACY_SD_PATCH_READY_FOR_MIGRATION" ;;
        NEW) echo "INSTALL_STATE=NEW_PATCH_READY" ;;
    esac

    return 0
}

echo "=== MU1440 isoTX2 DisplayManager preload installer ==="
echo "target=$TARGET"
echo "library=$DST_LIB"
echo "disable_marker=$DISABLE_MARKER"
echo "boot_policy=PRELOAD_DEFAULT_ON"
echo "gate_policy=STOCK_DEFAULT"
echo "mode=${1:---check}"
echo

preflight || exit $?

case "${1:---check}" in
    --check)
        echo
        echo "CHECK_ONLY=PASS"
        echo "No persistent changes made."
        echo "Next policy after --apply: preload ON by default, gate STOCK by default."
        echo "Persistent disable marker forces the exact stock DisplayManager launch."
        exit 0
        ;;
    --apply)
        ;;
    *)
        echo "Usage: $0 [--check|--apply]"
        exit 2
        ;;
esac

TH=$(hashf "$TARGET")
STATE=$(classify_current "$TH")
case "$STATE" in
    STOCK) SOURCE="$TARGET" ;;
    LEGACY_SD|NEW) SOURCE="$BACKUP" ;;
    *) echo "FAIL refusing --apply from unrecognized startup state"; exit 34 ;;
esac

echo
echo "[1/7] Generate candidate and validate with the UNIT'S own shells"
generate_from_stock "$SOURCE" "$TMP" new || { echo "FAIL patch generation"; exit 40; }
validate_new_patch "$TMP" || exit $?
PH=$(hashf "$TMP")
echo "candidate_patched_sha256=$PH"

echo
echo "[2/7] Create/verify durable exact-stock backup"
mount -uw /mnt/app 2>/dev/null || { echo "FAIL cannot remount /mnt/app rw"; exit 41; }
mkdir -p "$BACKDIR" || { mount -ur /mnt/app 2>/dev/null; exit 42; }

if [ ! -e "$BACKUP" ]; then
    [ "$STATE" = "STOCK" ] || {
        echo "FAIL non-stock migration requires pre-existing exact stock backup"
        mount -ur /mnt/app 2>/dev/null || true
        exit 43
    }
    cp -p "$TARGET" "$BACKUP" || { mount -ur /mnt/app 2>/dev/null; exit 44; }
    chmod 755 "$BACKUP" 2>/dev/null || true
fi

BH=$(hashf "$BACKUP")
[ "$BH" = "$EXPECTED_STOCK" ] || {
    echo "FAIL backup is not exact canonical stock: $BH"
    mount -ur /mnt/app 2>/dev/null || true
    exit 45
}
echo "backup_sha256=$BH"

echo
echo "[3/7] Install and verify process-local preload library"
cp "$SRC_LIB" "$DST_LIB.new" || { mount -ur /mnt/app 2>/dev/null; exit 46; }
chmod 755 "$DST_LIB.new" 2>/dev/null || true
mv "$DST_LIB.new" "$DST_LIB" || { mount -ur /mnt/app 2>/dev/null; exit 47; }
sync
DH=$(hashf "$DST_LIB")
[ "$DH" = "$EXPECTED_LIB" ] || {
    echo "FAIL installed library hash mismatch: $DH"
    rm -f "$DST_LIB" 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    exit 48
}
echo "installed_library_sha256=$DH"
mount -ur /mnt/app 2>/dev/null || true

echo
echo "[4/7] Atomically install persistent startup policy"
CURRENT=$(hashf "$TARGET")
if [ "$CURRENT" != "$PH" ]; then
    mount -uw /mnt/system 2>/dev/null || {
        echo "FAIL cannot remount /mnt/system rw"
        exit 49
    }
    cp "$TMP" "$TARGET.mibr-new" &&
    chmod 755 "$TARGET.mibr-new" 2>/dev/null &&
    mv "$TARGET.mibr-new" "$TARGET"
    RC=$?
    sync
    mount -ur /mnt/system 2>/dev/null || true
    [ "$RC" -eq 0 ] || { echo "FAIL persistent startup replacement"; exit 50; }
else
    echo "persistent_startup_already_current=yes"
fi

echo
echo "[5/7] Exact post-write verification"
AH=$(hashf "$TARGET")
[ "$AH" = "$PH" ] || {
    echo "FAIL post-write startup hash mismatch"
    echo " expected=$PH"
    echo " actual=$AH"
    exit 51
}
validate_new_patch "$TARGET" || exit $?
[ -r "$DST_LIB" ] || { echo "FAIL installed library disappeared"; exit 52; }
DH=$(hashf "$DST_LIB")
[ "$DH" = "$EXPECTED_LIB" ] || { echo "FAIL installed library post-hash mismatch"; exit 53; }

echo
echo "[6/7] Enable preload for next boot"
mount -uw /mnt/app 2>/dev/null || { echo "FAIL cannot remount /mnt/app rw for enable"; exit 54; }
rm -f "$DISABLE_MARKER" 2>/dev/null || {
    mount -ur /mnt/app 2>/dev/null || true
    echo "FAIL cannot remove persistent disable marker"
    exit 55
}
sync
[ ! -e "$DISABLE_MARKER" ] || {
    mount -ur /mnt/app 2>/dev/null || true
    echo "FAIL persistent disable marker still exists"
    exit 56
}
mount -ur /mnt/app 2>/dev/null || true
echo "PRELOAD_NEXT_BOOT=ENABLED"

echo
echo "[7/7] Force runtime gate to STOCK"
rm -f /tmp/mibr-isotx2-gate.direct /tmp/mibr-isotx2-gate.reset 2>/dev/null || true

echo
echo "INSTALL=PASS"
echo "BOOT_POLICY=PRELOAD_DEFAULT_ON"
echo "DIRECT_DEFAULT=OFF"
echo "DISABLE_MARKER=$DISABLE_MARKER"
echo "BACKUP=$BACKUP"
echo "REBOOT_REQUIRED=YES"
echo
echo "RECOVERY:"
echo "  Before reboot: ./preload_control.sh disable"
echo "  After a bad preload boot, if SSH is available: ./preload_control.sh disable ; ./reboot_fast.sh"
echo "  Full stock restore: ./restore_preload.sh"
exit 0
