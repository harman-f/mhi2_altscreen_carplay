#!/bin/sh
# Bounded exact-target first-test activation/restore.
# This helper NEVER starts btstack itself; connectivity_launcher owns restart.
# At most one activation signal and one restoration signal per fresh boot.
set -u
USB_LAN_CONFIRMED=0
ACTION=
TIMEOUT=180
STATE=/tmp/mhi2-wcp-btstack-overlay.state
MODE_STATE=/tmp/mhi2-wcp-btstack-preload.mode
RUNTIME_STATE=/tmp/mhi2-wcp-btstack-runtime.state
CYCLE_LOG=/tmp/mhi2-wcp-btstack-cycle.log
STOCK_COPY=/ramdisk/mhi2-wcp-stock/btstack
ENDPOINT=/dev/mhi2-iap2-rfcomm
EXPECTED_BTSTACK=d2b55046b8f22302c27811ab2070dc87f0408702c8764b43ad2ff135a66444a0
EXPECTED_BLUETOOTH=d3efa55f8bd089c027c89e84fda3e8f5136afd22f7e11862acd4f305d3dd5995
EXPECTED_LAUNCHER=13586753493d9cb4709196c672f81cbbf81ebfe44ae655a330d98324e04d8bb8
case "$0" in */*) SELF_DIR=${0%/*} ;; *) SELF_DIR=. ;; esac
. "$SELF_DIR/mhi2_wcp_control_common.sh" || exit 2
OVERLAY_DOWN="$SELF_DIR/mhi2_wcp_btstack_overlay_down.sh"
IPOD_STOP="$SELF_DIR/../runtime-launcher/mhi2_wcp_mm_ipod_stop.sh"
WCP_RECOVER_STALE=1
CONTROL_LOADED=0
trap 'wcp_release' 0
trap 'fail interrupted-state-retained' 1 2 15
usage() { echo "usage: $0 --usb-lan-confirmed (--activate|--restore-stock) [--timeout SEC]"; }
say() { printf '%s\n' "$*" | tee -a "$CYCLE_LOG"; }
fail()
{
    if [ "$WCP_HAS_LOCK" -eq 1 ] && [ "$CONTROL_LOADED" -eq 1 ]; then
        wcp_atomic_line "$MODE_STATE" stock || true
        say "WCP_BTSTACK_CYCLE_FAILSAFE next_wrapper_mode=stock state=retained"
    fi
    say "WCP_BTSTACK_CYCLE_BLOCKED reason=$*"
    exit 2
}
hash_file() { sha256sum "$1" 2>/dev/null | awk '{print $1}'; }
read_runtime()
{
    RUNTIME_MODE=; RUNTIME_PID=; RUNTIME_SHA=
    [ -r "$RUNTIME_STATE" ] || return 1
    while IFS='=' read key value; do
      case "$key" in
        mode) RUNTIME_MODE="$value" ;;
        pid) RUNTIME_PID="$value" ;;
        real_sha256) RUNTIME_SHA="$value" ;;
      esac
    done < "$RUNTIME_STATE"
    [ "$RUNTIME_SHA" = "$EXPECTED_BTSTACK" ] || return 1
    case "$RUNTIME_PID" in ''|*[!0-9]*) return 1 ;; esac
    case "$RUNTIME_MODE" in hooked|stock) ;; *) return 1 ;; esac
}
set_mode() { wcp_atomic_line "$MODE_STATE" "$1" || fail mode-publication; }
kill_unexpected()
{
    victim="$1"
    say "WCP_BTSTACK_CYCLE trigger=unexpected-child-death pid=$victim signal=9"
    slay_status=0
    slay -f -m pid -s 9 "$victim" >/dev/null 2>&1 || slay_status=$?
    say "WCP_BTSTACK_CYCLE signal_attempt_pid=$victim slay_status=$slay_status delivery=unconfirmed"
}
check_launcher()
{
    rows=$(wcp_process_rows ./bin/apps/connectivity_launcher /eso/bin/apps/connectivity_launcher /mnt/app/eso/bin/apps/connectivity_launcher) || return 1
    set -- $rows
    [ "$#" -eq 2 ] && [ "$1" = "$WCP_LAUNCHER_PID" ]
}
wait_for_ram_mode()
{
    want_mode="$1"; old_pid="$2"; polls=0; previous_candidate=0
    # QNX ksh's SECONDS is not assumed. Every failed observation consumes
    # one poll and one sleep; two consecutive observations prove stability.
    while [ "$polls" -lt "$TIMEOUT" ]; do
        polls=$((polls+1))
        wcp_snapshot || fail recovery-process-query
        check_launcher || fail launcher-changed-during-recovery
        rows=$(wcp_process_rows "$STOCK_COPY") || fail recovery-child-query
        set -- $rows
        [ "$#" -eq 0 ] || [ "$#" -eq 2 ] || fail recovery-child-not-unique
        observed=0
        if [ "$#" -eq 2 ] && [ "$1" != "$old_pid" ] && [ "$2" = "$WCP_LAUNCHER_PID" ]; then
            candidate=$1
            if read_runtime && [ "$RUNTIME_MODE" = "$want_mode" ] && [ "$RUNTIME_PID" = "$candidate" ]; then
                if [ "$want_mode" = hooked ]; then
                    WCP_HOOK_PID=$candidate
                    wcp_save_control activating || fail hook-pid-journal
                    if wcp_ready_for_pid "$candidate" && [ -e "$ENDPOINT" ]; then observed=$candidate; fi
                else
                    [ -e "$ENDPOINT" ] || observed=$candidate
                fi
                if [ "$observed" != 0 ] && [ "$observed" = "$previous_candidate" ]; then
                    NEW_PID=$candidate
                    return 0
                fi
            fi
        fi
        previous_candidate=$observed
        sleep 1
    done
    return 1
}
while [ "$#" -gt 0 ]; do
    case "$1" in
      --usb-lan-confirmed) USB_LAN_CONFIRMED=1; shift ;;
      --activate) [ -z "$ACTION" ] || fail multiple-actions; ACTION=activate; shift ;;
      --restore-stock) [ -z "$ACTION" ] || fail multiple-actions; ACTION=restore; shift ;;
      --timeout) [ "$#" -ge 2 ] || fail missing-timeout; TIMEOUT="$2"; shift 2 ;;
      --help) usage; exit 0 ;;
      *) fail "unknown-option:$1" ;;
    esac
done
[ "$USB_LAN_CONFIRMED" -eq 1 ] || fail usb-lan-not-confirmed
[ -n "$ACTION" ] || fail action-required
case "$TIMEOUT" in ''|*[!0-9]*) fail invalid-timeout ;; esac
[ "$TIMEOUT" -gt 0 ] && [ "$TIMEOUT" -le 300 ] || fail timeout-out-of-bounds
for c in sha256sum slay tee chmod sleep; do command -v "$c" >/dev/null 2>&1 || fail "utility-unavailable:$c"; done
wcp_acquire || fail control-lock-busy-or-invalid
[ -f "$STATE" ] || fail overlay-not-prepared
wcp_load_control || fail control-journal-invalid
CONTROL_LOADED=1
[ -r "$STOCK_COPY" ] && [ "$(hash_file "$STOCK_COPY")" = "$EXPECTED_BTSTACK" ] || fail stock-copy-sha
[ "$(hash_file /eso/bin/apps/bluetooth)" = "$EXPECTED_BLUETOOTH" ] || fail bluetooth-sha
[ "$(hash_file /eso/bin/apps/connectivity_launcher)" = "$EXPECTED_LAUNCHER" ] || fail launcher-sha
wcp_snapshot && wcp_no_mutators || fail process-query-or-worker-conflict
check_launcher || fail launcher-not-unique-or-changed
if [ "$ACTION" = activate ]; then
    [ "$WCP_PHASE:$WCP_ACTIVATION:$WCP_RESTORATION" = prepared:0:0 ] || fail activation-budget-or-phase
    [ ! -e "$ENDPOINT" ] && [ ! -e "$WCP_READY" ] && [ ! -e /tmp/mhi2-wcp-hook-consumed ] || fail prior-provider-state
    rows=$(wcp_process_rows /eso/bin/apps/btstack /mnt/app/eso/bin/apps/btstack) || fail stock-child-query
    set -- $rows
    [ "$#" -eq 2 ] && [ "$1" = "$WCP_BASE_PID" ] && [ "$2" = "$WCP_LAUNCHER_PID" ] || fail original-stock-child-changed
    OLD_PID=$1
    rows=$(wcp_process_rows "$STOCK_COPY") || fail ram-child-query
    [ -z "$rows" ] || fail unexpected-ram-child
    WCP_ACTIVATION=1
    wcp_save_control activation-signal-intent || fail activation-journal
    set_mode hooked
    kill_unexpected "$OLD_PID"
    NEW_PID=0
    wait_for_ram_mode hooked "$OLD_PID" || fail hooked-recovery-timeout-stock-armed
    wcp_save_control active || fail active-journal
    say "WCP_BTSTACK_CYCLE_ACTIVE old_pid=$OLD_PID new_pid=$NEW_PID parent=$WCP_LAUNCHER_PID ready=native-registration-sdp-endpoint"
    exit 0
fi
# Restore is an independent entry point. Stop owned mm-ipod before the provider.
[ -r "$IPOD_STOP" ] && [ -r "$OVERLAY_DOWN" ] || fail restore-helper-missing
sh "$IPOD_STOP" --usb-lan-confirmed || fail owned-ipod-stop
set_mode stock
wcp_snapshot || fail restore-process-query
check_launcher || fail restore-launcher-changed
rows=$(wcp_process_rows "$STOCK_COPY") || fail restore-child-query
set -- $rows
[ "$#" -eq 0 ] || [ "$#" -eq 2 ] || fail restore-child-not-unique
OLD_PID=0
if [ "$#" -eq 2 ]; then
    [ "$2" = "$WCP_LAUNCHER_PID" ] || fail restore-child-parent
    OLD_PID=$1
    read_runtime && [ "$RUNTIME_PID" = "$OLD_PID" ] || fail restore-runtime-identity
    if [ "$RUNTIME_MODE" = hooked ]; then
        [ "$WCP_ACTIVATION:$WCP_RESTORATION" = 1:0 ] || fail restoration-budget-exhausted
        WCP_HOOK_PID=$OLD_PID
        WCP_RESTORATION=1
        wcp_save_control restoration-signal-intent || fail restoration-journal
        kill_unexpected "$OLD_PID"
        NEW_PID=0
        wait_for_ram_mode stock "$OLD_PID" || fail stock-recovery-timeout-state-retained
    else
        # Already unhooked after an automatic retry; no additional signal.
        NEW_PID=$OLD_PID
        [ ! -e "$ENDPOINT" ] || fail stock-runtime-with-provider-endpoint
    fi
else
    rows=$(wcp_process_rows /eso/bin/apps/btstack /mnt/app/eso/bin/apps/btstack) || fail restore-stock-query
    set -- $rows
    if [ "$#" -eq 2 ] && [ "$1" = "$WCP_BASE_PID" ] && [ "$2" = "$WCP_LAUNCHER_PID" ]; then
        NEW_PID=$1 # No successful exec transition; original stock still owns it.
    else
        NEW_PID=0
        wait_for_ram_mode stock 0 || fail stock-restore-not-observed
    fi
fi
sh "$OVERLAY_DOWN" --usb-lan-confirmed || fail overlay-down-state-retained
say "WCP_BTSTACK_CYCLE_STOCK pid=$NEW_PID launcher_owned=1 visible_stock=verified mm_ipod=drained"
