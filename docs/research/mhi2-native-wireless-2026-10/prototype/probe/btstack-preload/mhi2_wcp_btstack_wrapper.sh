#!/bin/sh
# Staged as /eso/bin/apps/btstack by the volatile overlay helper.
# REAL is a SHA-gated copy made before the overlay becomes visible.

set -u
umask 077

REAL=/ramdisk/mhi2-wcp-stock/btstack
HOOK_FILE=/tmp/mhi2-wcp-btstack-hook.path
MODE_STATE=/tmp/mhi2-wcp-btstack-preload.mode
RUNTIME_STATE=/tmp/mhi2-wcp-btstack-runtime.state
LOG=/tmp/mhi2-wcp-btstack-wrapper.log
EXPECTED_BTSTACK=d2b55046b8f22302c27811ab2070dc87f0408702c8764b43ad2ff135a66444a0

exec >>"$LOG" 2>&1
echo "WCP_BTSTACK_WRAPPER begin date=$(date 2>/dev/null || true) pid=$$"

if command -v sha256sum >/dev/null 2>&1; then
    got=$(sha256sum "$REAL" 2>/dev/null | awk '{print $1}')
    [ "$got" = "$EXPECTED_BTSTACK" ] || {
        echo "WCP_BTSTACK_WRAPPER fatal=stock-sha-mismatch got=$got"
        exit 122
    }
else
    echo "WCP_BTSTACK_WRAPPER fatal=sha256sum-unavailable"
    exit 123
fi

MODE=stock
if [ -r "$MODE_STATE" ]; then
    read MODE < "$MODE_STATE" || MODE=stock
fi
HOOK=
case "$MODE" in
    hooked)
        # One hook execution per fresh boot, including automatic launcher
        # retries. Consume the request before exposing any preload lab gate.
        if ! mkdir /tmp/mhi2-wcp-hook-consumed 2>/dev/null; then
            MODE=stock
            echo "WCP_BTSTACK_WRAPPER fallback=stock reason=hook-attempt-already-consumed"
        elif ! printf '%s\n' "$$" > /tmp/mhi2-wcp-hook-consumed/pid; then
            MODE=stock
        elif [ -r "$HOOK_FILE" ]; then
            read HOOK < "$HOOK_FILE" || HOOK=
            if [ -z "$HOOK" ] || [ ! -r "$HOOK" ]; then MODE=stock; fi
        else
            MODE=stock
        fi
        tmp_mode="$MODE_STATE.$$"
        if printf '%s\n' stock > "$tmp_mode" && chmod 0600 "$tmp_mode" && mv "$tmp_mode" "$MODE_STATE"; then
            echo "WCP_BTSTACK_WRAPPER next_wrapper_mode=stock"
        else
            MODE=stock
            echo "WCP_BTSTACK_WRAPPER fallback=stock reason=mode-publication-failed"
        fi
        ;;
    stock) ;;
    *) MODE=stock; echo "WCP_BTSTACK_WRAPPER fallback=stock reason=invalid-mode" ;;
esac
if [ "$MODE" = hooked ]; then
    export MHI2_IAP_SERVICEGRAPH_LAB=1
    export MHI2_IAP_RFCOMM_LAB=1
    export MHI2_IAP_FORCE_CONNECTABLE_LAB=1
    export LD_PRELOAD="$HOOK"
else
    HOOK=
    unset MHI2_IAP_SERVICEGRAPH_LAB MHI2_IAP_RFCOMM_LAB MHI2_IAP_FORCE_CONNECTABLE_LAB LD_PRELOAD
fi

tmp_state="$RUNTIME_STATE.$$"
{
    echo "mode=$MODE"
    echo "pid=$$"
    echo "real=$REAL"
    echo "real_sha256=$got"
    echo "hook=$HOOK"
} > "$tmp_state" || {
    echo "WCP_BTSTACK_WRAPPER fatal=runtime-state-write"
    exit 126
}
chmod 0600 "$tmp_state" 2>/dev/null || true
mv "$tmp_state" "$RUNTIME_STATE" || {
    echo "WCP_BTSTACK_WRAPPER fatal=runtime-state-publish"
    exit 127
}

echo "WCP_BTSTACK_WRAPPER exec mode=$MODE pid=$$ real=$REAL hook=$HOOK"
exec "$REAL" "$@"
