#!/bin/sh
# Independent, journalled restore. Never force-detaches or guesses a PID.
set -u
USB_LAN_CONFIRMED=0
STATE=/tmp/mhi2-wcp-btstack-overlay.state
HOOK_STATE=/tmp/mhi2-wcp-btstack-hook.path
MODE_STATE=/tmp/mhi2-wcp-btstack-preload.mode
RUNTIME_STATE=/tmp/mhi2-wcp-btstack-runtime.state
DEFAULT_STOCK_COPY=/ramdisk/mhi2-wcp-stock/btstack
DEFAULT_STOCK_DIR=/ramdisk/mhi2-wcp-stock
EXPECTED_BTSTACK=d2b55046b8f22302c27811ab2070dc87f0408702c8764b43ad2ff135a66444a0
EXPECTED_BLUETOOTH=d3efa55f8bd089c027c89e84fda3e8f5136afd22f7e11862acd4f305d3dd5995
case "$0" in */*) SELF_DIR=${0%/*} ;; *) SELF_DIR=. ;; esac
. "$SELF_DIR/mhi2_wcp_control_common.sh" || exit 2
WCP_RECOVER_STALE=1
IPOD_STOP="$SELF_DIR/../runtime-launcher/mhi2_wcp_mm_ipod_stop.sh"
trap 'wcp_release' 0
trap 'fail interrupted-state-retained' 1 2 15
fail() { echo "WCP_BTSTACK_OVERLAY_DOWN_BLOCKED reason=$*" >&2; exit 2; }
hash_file() { sha256sum "$1" 2>/dev/null | awk '{print $1}'; }

while [ "$#" -gt 0 ]; do
    case "$1" in
      --usb-lan-confirmed) USB_LAN_CONFIRMED=1; shift ;;
      --help) echo "usage: $0 --usb-lan-confirmed"; exit 0 ;;
      *) fail "unknown-option:$1" ;;
    esac
done
[ "$USB_LAN_CONFIRMED" -eq 1 ] || fail usb-lan-not-confirmed
for c in sha256sum mount umount slay chmod sleep; do
    command -v "$c" >/dev/null 2>&1 || fail "utility-unavailable:$c"
done
wcp_acquire || fail control-lock-busy-or-invalid
if [ ! -f "$STATE" ]; then
    [ ! -f "$WCP_IPOD_STATE" ] || sh "$IPOD_STOP" --usb-lan-confirmed || fail mm-ipod-stop
    echo "WCP_BTSTACK_OVERLAY_DOWN state=absent no_overlay_mutation=1"
    exit 0
fi
wcp_atomic_line "$MODE_STATE" stock || fail stock-mode-arm
version=; phase=; target=; device=; devb_pid=; stock_copy=; wrapper_hash=
while IFS='=' read key value; do
    case "$key" in
      version) version="$value" ;;
      phase) phase="$value" ;;
      target) target="$value" ;;
      device) device="$value" ;;
      devb_pid) devb_pid="$value" ;;
      stock_copy) stock_copy="$value" ;;
      wrapper_sha256) wrapper_hash="$value" ;;
    esac
done < "$STATE"
[ "$version" = 2 ] && [ "$target" = /eso/bin/apps ] &&
[ "$device" = /dev/wcpbtram0t77 ] && [ "$stock_copy" = "$DEFAULT_STOCK_COPY" ] || fail invalid-journal-identity
case "$devb_pid" in ''|*[!0-9]*) fail invalid-devb-pid ;; esac
wcp_load_control || fail invalid-control-journal
[ -r "$IPOD_STOP" ] || fail independent-ipod-stop-missing
sh "$IPOD_STOP" --usb-lan-confirmed || fail mm-ipod-stop
wcp_snapshot && wcp_no_mutators || fail process-query-or-worker-conflict
rows=$(wcp_process_rows "$DEFAULT_STOCK_COPY") || fail ram-child-query
set -- $rows
retain_stock_copy=0
if [ "$#" -ne 0 ]; then
    [ "$#" -eq 2 ] || fail ram-child-not-unique
    running_ram_pid=$1
    runtime_mode=; runtime_pid=; runtime_sha=
    [ -r "$RUNTIME_STATE" ] || fail ram-child-without-runtime-state
    while IFS='=' read key value; do
      case "$key" in
        mode) runtime_mode="$value" ;;
        pid) runtime_pid="$value" ;;
        real_sha256) runtime_sha="$value" ;;
      esac
    done < "$RUNTIME_STATE"
    [ "$runtime_pid" = "$running_ram_pid" ] && [ "$runtime_sha" = "$EXPECTED_BTSTACK" ] || fail runtime-identity-mismatch
    [ "$runtime_mode" = stock ] || fail hooked-btstack-still-running
    [ "$(hash_file "$stock_copy")" = "$EXPECTED_BTSTACK" ] || fail retained-copy-sha
    retain_stock_copy=1
fi
[ ! -e /dev/mhi2-iap2-rfcomm ] || fail rfcomm-endpoint-still-present
if [ -r "$WCP_READY" ]; then
    ready_pid=
    while IFS='=' read key value; do [ "$key" != pid ] || ready_pid="$value"; done < "$WCP_READY"
    if [ "$WCP_HOOK_PID" = 0 ] && [ "$WCP_ACTIVATION" = 1 ] && [ -r /tmp/mhi2-wcp-hook-consumed/pid ]; then
        read attempt_pid < /tmp/mhi2-wcp-hook-consumed/pid || fail attempt-pid-read
        case "$attempt_pid" in ''|*[!0-9]*) fail attempt-pid-invalid ;; esac
        [ "$attempt_pid" = "$ready_pid" ] || fail attempt-ready-mismatch
        WCP_HOOK_PID=$attempt_pid
    fi
    [ "$ready_pid" = "$WCP_HOOK_PID" ] && [ "$ready_pid" != 0 ] || fail unowned-provider-ready-marker
    awk -v p="$ready_pid" 'NR>1 && $2==p {live=1} END {exit live ? 2 : 0}' "$WCP_PS" || fail provider-pid-still-live
fi
# The exact named devb identity is required even for interrupted startup.
rows=$(wcp_devb_rows) || fail devb-query
set -- $rows
if [ "$#" -ne 0 ]; then
    [ "$#" -eq 2 ] || fail devb-not-unique
    if [ "$devb_pid" = 0 ]; then
        case "$phase" in prepare-intent|'') fail devb-without-start-intent ;; esac
        devb_pid=$1
    fi
    [ "$1" = "$devb_pid" ] || fail devb-pid-mismatch
elif [ -e "$device" ]; then
    fail device-without-proven-owner
fi
wcp_mount_snapshot || fail mount-query
count=$(wcp_mount_count "$device" "$target") || fail overlay-mount-owner
if [ "$count" -eq 1 ]; then
    [ -n "$wrapper_hash" ] && [ "$(hash_file "$target/btstack")" = "$wrapper_hash" ] || fail top-wrapper-identity
fi
wcp_save_control detach-intent || fail detach-journal
wcp_detach_owned "$device" "$target" || fail overlay-detach-retained
wcp_detach_owned "$device" /tmp/mhi2-wcp-btstage || fail stage-detach-retained
# Prove visible stock BEFORE backing signal or evidence cleanup.
[ "$(hash_file /eso/bin/apps/btstack)" = "$EXPECTED_BTSTACK" ] || fail visible-stock-not-restored
[ "$(hash_file /eso/bin/apps/bluetooth)" = "$EXPECTED_BLUETOOTH" ] || fail bluetooth-not-restored
wcp_snapshot && wcp_no_mutators || fail final-owner-query
rows=$(wcp_devb_rows) || fail final-devb-query
set -- $rows
if [ "$#" -ne 0 ]; then
    [ "$#" -eq 2 ] && [ "$1" = "$devb_pid" ] || fail final-devb-identity
    wcp_save_control backing-stop-intent || fail backing-stop-journal
    wcp_signal_once "$devb_pid" 15
fi
elapsed=0
while [ "$elapsed" -lt 10 ]; do
    wcp_snapshot || fail backing-exit-query
    rows=$(wcp_devb_rows) || fail backing-exit-query
    if [ -z "$rows" ] && [ ! -e "$device" ]; then break; fi
    sleep 1; elapsed=$((elapsed+1))
done
[ -z "$rows" ] && [ ! -e "$device" ] || fail backing-exit-not-proven-retained
wcp_mount_snapshot || fail final-mount-query
[ "$(wcp_mount_count "$device" "$target")" = 0 ] || fail target-still-mounted
[ "$(wcp_mount_count "$device" /tmp/mhi2-wcp-btstage)" = 0 ] || fail stage-still-mounted
# Keep the neutral copy until reboot even if the initial snapshot had no RAM
# child: the native launcher may start stock recovery during detach. This is
# one bounded copy per boot, enforced by the retained control journal.
if [ -d /tmp/mhi2-wcp-btstage ]; then
    rmdir /tmp/mhi2-wcp-btstage || fail unexpected-stage-content
fi
# Leave the per-boot control journal to enforce the two-transition budget.
wcp_save_control restored || fail restored-journal
rm -f "$STATE" "$HOOK_STATE" "$MODE_STATE" "$RUNTIME_STATE" "$WCP_READY" || fail evidence-cleanup

echo "WCP_BTSTACK_OVERLAY_DOWN result=stock-restored ram_stock_process_retained=$retain_stock_copy neutral_copy=retained-until-reboot budget_journal=retained"
