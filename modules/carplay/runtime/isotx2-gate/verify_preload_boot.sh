#!/bin/ksh
set -u

SELF=$0
case "$SELF" in */*) BASE=${SELF%/*} ;; *) BASE=. ;; esac
BASE=$(cd "$BASE" 2>/dev/null && pwd) || exit 2
GATE="${MIBR_GATE_CONTROL:-$BASE/gate.sh}"
CONTROL="${MIBR_PRELOAD_CONTROL:-$BASE/preload_control.sh}"
HASH="${MIBR_SHA256:-$BASE/../../payload/sha256sum}"
TARGET=/mnt/system/etc/boot/startup.sh
STATS=/tmp/mibr-isotx2-gate.stats
DISABLE_MARKER=/mnt/app/root/mibr-isotx2-gate-disable

DM=$(pidin ar 2>/dev/null | awk '/pps\/displaymanager/ && !/awk/ {print $1; exit}')

echo "=== MU1440 DisplayManager preload boot verification ==="
echo "DM_PID=${DM:-NONE}"

[ -n "${DM:-}" ] || {
    echo "VERIFY_PRELOAD_BOOT=FAIL_NO_DISPLAYMANAGER"
    exit 20
}

echo
echo "=== PRELOAD LIBRARY ==="
MAPTMP=/tmp/mibr-isotx2-map.$$
pidin -p "$DM" mapinfo > "$MAPTMP" 2>/dev/null ||
    pidin -p "$DM" memory > "$MAPTMP" 2>/dev/null || true
if grep libmibr_isotx2_gate "$MAPTMP"; then
    echo "PRELOAD_LIBRARY=LOADED"
    LIB_OK=1
else
    echo "PRELOAD_LIBRARY=NOT_LOADED"
    LIB_OK=0
fi
rm -f "$MAPTMP" 2>/dev/null || true

echo
echo "=== DISPLAYMANAGER ENV ==="
pidin -p "$DM" environment 2>/dev/null | grep -E 'LD_PRELOAD|MALLOC_ARENA_CACHE_MAXSZ' || true

echo
echo "=== isoTX2 FD ==="
pidin -p "$DM" fds 2>/dev/null | grep isoTX2 || true

echo
echo "=== PERSISTENT PRELOAD POLICY ==="
"$CONTROL" status

echo
echo "=== GATE STATUS ==="
"$GATE" status

echo
echo "=== PERSISTENT STARTUP HASH ==="
if [ -x "$HASH" ] && [ -r "$TARGET" ]; then
    "$HASH" "$TARGET"
fi

[ ! -e /tmp/mibr-isotx2-gate.direct ] || {
    echo "VERIFY_PRELOAD_BOOT=FAIL_DIRECT_MARKER_PRESENT"
    exit 21
}

[ "$LIB_OK" = "1" ] || {
    echo "VERIFY_PRELOAD_BOOT=FAIL_PRELOAD_NOT_LOADED"
    exit 22
}

[ ! -e "$DISABLE_MARKER" ] || {
    echo "VERIFY_PRELOAD_BOOT=FAIL_PRELOAD_DISABLED_NEXT_BOOT"
    exit 23
}

[ -r "$STATS" ] || {
    echo "VERIFY_PRELOAD_BOOT=FAIL_GATE_STATS_MISSING"
    exit 24
}

grep -Fxq 'loaded=1' "$STATS" || {
    echo "VERIFY_PRELOAD_BOOT=FAIL_GATE_STATS_NOT_LOADED"
    exit 25
}

grep -Fxq 'mode=stock' "$STATS" || {
    echo "VERIFY_PRELOAD_BOOT=FAIL_GATE_STATS_NOT_STOCK"
    exit 26
}

grep -Fxq 'target=/dev/mlb/isoTX2' "$STATS" || {
    echo "VERIFY_PRELOAD_BOOT=FAIL_GATE_WRONG_TARGET"
    exit 27
}

TRACKED=$(awk -F= '$1=="tracked_fds"{print $2; exit}' "$STATS" 2>/dev/null)
OPENED=$(awk -F= '$1=="tracked_open_calls"{print $2; exit}' "$STATS" 2>/dev/null)
case "${TRACKED:-}" in ''|*[!0-9]*) TRACKED=0 ;; esac
case "${OPENED:-}" in ''|*[!0-9]*) OPENED=0 ;; esac
echo "tracked_fds_verified=$TRACKED"
echo "tracked_open_calls_verified=$OPENED"

[ "$TRACKED" -gt 0 ] || {
    echo "VERIFY_PRELOAD_BOOT=FAIL_ISOTX2_NOT_TRACKED"
    exit 28
}

[ "$OPENED" -gt 0 ] || {
    echo "VERIFY_PRELOAD_BOOT=FAIL_ISOTX2_NEVER_OPENED"
    exit 29
}

echo
echo "VERIFY_PRELOAD_BOOT=PASS"
echo "Operator still must confirm native VC map is visually normal."
exit 0
