#!/bin/sh
# Volatile exact-target QNX4 namespace overlay; no persistent app writes.
set -u
USB_LAN_CONFIRMED=0
FRESH_BOOT_CONFIRMED=0
HOOK=
WRAPPER=
DRY_RUN=0
RD_NAME=wcpbtram
RD_MB=4
DEVICE=/dev/${RD_NAME}0t77
STAGE=/tmp/mhi2-wcp-btstage
TARGET=/eso/bin/apps
STATE=/tmp/mhi2-wcp-btstack-overlay.state
HOOK_STATE=/tmp/mhi2-wcp-btstack-hook.path
MODE_STATE=/tmp/mhi2-wcp-btstack-preload.mode
RUNTIME_STATE=/tmp/mhi2-wcp-btstack-runtime.state
STOCK_DIR=/ramdisk/mhi2-wcp-stock
STOCK_COPY=$STOCK_DIR/btstack
EXPECTED_BTSTACK=d2b55046b8f22302c27811ab2070dc87f0408702c8764b43ad2ff135a66444a0
EXPECTED_BLUETOOTH=d3efa55f8bd089c027c89e84fda3e8f5136afd22f7e11862acd4f305d3dd5995
EXPECTED_LAUNCHER=13586753493d9cb4709196c672f81cbbf81ebfe44ae655a330d98324e04d8bb8
DEVBPID=0
WRAPPER_HASH=
CLEANUP_ARMED=0
PHASE=preflight
case "$0" in */*) SELF_DIR=${0%/*} ;; *) SELF_DIR=. ;; esac
. "$SELF_DIR/mhi2_wcp_control_common.sh" || exit 2
[ -n "$WRAPPER" ] || WRAPPER="$SELF_DIR/mhi2_wcp_btstack_wrapper.sh"
trap 'wcp_release' 0
trap 'fail interrupted' 1 2 15

usage()
{
    echo "usage: $0 --usb-lan-confirmed --fresh-boot-confirmed --hook PATH [--wrapper PATH] [--dry-run]"
}

publish_state()
{
    PHASE="$1"
    {
      echo "version=2"
      echo "phase=$PHASE"
      echo "target=$TARGET"
      echo "device=$DEVICE"
      echo "devb_pid=$DEVBPID"
      echo "wrapper_sha256=$WRAPPER_HASH"
      echo "hook=$HOOK"
      echo "stock_copy=$STOCK_COPY"
    } > "$STATE.$$" || return 1
    chmod 0600 "$STATE.$$" || return 1
    mv "$STATE.$$" "$STATE"
}

cleanup_partial()
{
    # Do not guess which mount completed, force-detach, signal backing, or
    # erase recovery evidence after an error/signal. Explicit down rechecks
    # all ownership from a fresh snapshot and the write-ahead journal.
    wcp_atomic_line "$MODE_STATE" stock || true
    echo "WCP_BTSTACK_OVERLAY_RETAINED phase=$PHASE stock_mode=armed state=$STATE"
}

fail()
{
    echo "WCP_BTSTACK_OVERLAY_BLOCKED reason=$*" >&2
    [ "$CLEANUP_ARMED" -eq 0 ] || cleanup_partial
    exit 2
}

hash_file() { sha256sum "$1" 2>/dev/null | awk '{print $1}'; }

while [ "$#" -gt 0 ]; do
    case "$1" in
      --usb-lan-confirmed) USB_LAN_CONFIRMED=1; shift ;;
      --fresh-boot-confirmed) FRESH_BOOT_CONFIRMED=1; shift ;;
      --hook) [ "$#" -ge 2 ] || fail missing-hook; HOOK="$2"; shift 2 ;;
      --wrapper) [ "$#" -ge 2 ] || fail missing-wrapper; WRAPPER="$2"; shift 2 ;;
      --dry-run) DRY_RUN=1; shift ;;
      --help) usage; exit 0 ;;
      *) fail "unknown-option:$1" ;;
    esac
done
[ "$USB_LAN_CONFIRMED" -eq 1 ] || fail usb-lan-not-confirmed
[ "$FRESH_BOOT_CONFIRMED" -eq 1 ] || fail healthy-fresh-boot-not-confirmed
[ -n "$HOOK" ] && [ -r "$HOOK" ] || fail hook-missing
[ -r "$WRAPPER" ] || fail wrapper-missing
for c in sha256sum mount umount devb-ram slay chmod cp sync sleep; do
    command -v "$c" >/dev/null 2>&1 || fail "utility-unavailable:$c"
done
wcp_acquire || fail control-lock-busy-or-invalid
[ -d "$TARGET" ] && [ -w /ramdisk ] || fail target-or-ramdisk-unavailable
for path in "$STATE" "$HOOK_STATE" "$MODE_STATE" "$RUNTIME_STATE" "$WCP_CONTROL" "$WCP_READY" "$STOCK_DIR" "$STAGE" "$DEVICE" /tmp/mhi2-wcp-hook-consumed; do
    [ ! -e "$path" ] || fail "preexisting-state:$path"
done
[ "$(hash_file /mnt/app/eso/bin/apps/btstack)" = "$EXPECTED_BTSTACK" ] || fail real-btstack-sha
[ "$(hash_file /eso/bin/apps/btstack)" = "$EXPECTED_BTSTACK" ] || fail visible-btstack-sha
[ "$(hash_file /eso/bin/apps/bluetooth)" = "$EXPECTED_BLUETOOTH" ] || fail bluetooth-sha
[ "$(hash_file /eso/bin/apps/connectivity_launcher)" = "$EXPECTED_LAUNCHER" ] || fail launcher-sha
wcp_snapshot && wcp_no_mutators || fail process-query-or-worker-conflict
rows=$(wcp_process_rows ./bin/apps/connectivity_launcher /eso/bin/apps/connectivity_launcher /mnt/app/eso/bin/apps/connectivity_launcher) || fail launcher-query
set -- $rows
[ "$#" -eq 2 ] || fail launcher-not-unique
LAUNCHER_PID=$1
rows=$(wcp_process_rows /eso/bin/apps/btstack /mnt/app/eso/bin/apps/btstack) || fail btstack-query
set -- $rows
[ "$#" -eq 2 ] && [ "$2" = "$LAUNCHER_PID" ] || fail stock-child-topology
BASE_PID=$1
rows=$(wcp_devb_rows) || fail devb-query
[ -z "$rows" ] || fail devb-already-present
wcp_mount_snapshot || fail mount-query
[ "$(wcp_mount_count "$DEVICE" "$TARGET")" = 0 ] || fail target-mount-conflict
[ "$(wcp_mount_count "$DEVICE" "$STAGE")" = 0 ] || fail stage-mount-conflict
if [ "$DRY_RUN" -eq 1 ]; then
    echo "WCP_BTSTACK_OVERLAY_DRY_RUN no_mutation=1"
    exit 0
fi
WCP_ACTIVATION=0; WCP_RESTORATION=0; WCP_HOOK_PID=0; WCP_LAUNCHER_PID=$LAUNCHER_PID; WCP_BASE_PID=$BASE_PID
wcp_save_control prepared || fail control-journal-write
publish_state prepare-intent || fail overlay-journal-write
CLEANUP_ARMED=1
mkdir "$STOCK_DIR" || fail stock-dir-create
cp /mnt/app/eso/bin/apps/btstack "$STOCK_COPY" || fail stock-copy
chmod 0755 "$STOCK_COPY" || fail stock-permissions
[ "$(hash_file "$STOCK_COPY")" = "$EXPECTED_BTSTACK" ] || fail stock-copy-sha
mkdir "$STAGE" || fail stage-create
# All wrapper inputs exist in stock mode BEFORE namespace visibility.
wcp_atomic_line "$HOOK_STATE" "$HOOK" || fail hook-publication
wcp_atomic_line "$MODE_STATE" stock || fail stock-mode-publication
publish_state devb-intent || fail devb-journal
devb-ram blk cache=512k ram capacity=$((2048 * RD_MB)) disk name=$RD_NAME >/tmp/mhi2-wcp-devb-ram.log 2>&1 || fail devb-start
wcp_snapshot || fail devb-process-query
rows=$(wcp_devb_rows) || fail devb-query
set -- $rows
[ "$#" -eq 2 ] || fail devb-not-unique
DEVBPID=$1
publish_state device-wait || fail device-journal
w=0
while [ ! -e "$DEVICE" ] && [ "$w" -lt 10 ]; do sleep 1; w=$((w+1)); done
[ -e "$DEVICE" ] || fail device-timeout
publish_state stage-mount-intent || fail stage-journal
mount -t qnx4 "$DEVICE" "$STAGE" || fail stage-mount
wcp_mount_snapshot || fail stage-mount-query
[ "$(wcp_mount_count "$DEVICE" "$STAGE")" = 1 ] || fail stage-mapping-not-proven
cp "$WRAPPER" "$STAGE/btstack" || fail wrapper-copy
chmod 0755 "$STAGE/btstack" || fail wrapper-permissions
sync
WRAPPER_HASH=$(hash_file "$STAGE/btstack")
[ -n "$WRAPPER_HASH" ] || fail wrapper-hash
publish_state stage-detach-intent || fail stage-journal
wcp_detach_owned "$DEVICE" "$STAGE" || fail stage-detach
publish_state overlay-mount-intent || fail overlay-journal
mount -t qnx4 -o before "$DEVICE" "$TARGET" || fail overlay-mount
wcp_mount_snapshot || fail mounted-query
[ "$(wcp_mount_count "$DEVICE" "$TARGET")" = 1 ] || fail overlay-mapping-not-proven
[ "$(hash_file /eso/bin/apps/btstack)" = "$WRAPPER_HASH" ] || fail wrapper-not-visible
[ "$(hash_file /eso/bin/apps/bluetooth)" = "$EXPECTED_BLUETOOTH" ] || fail stock-fallthrough
wcp_snapshot || fail final-process-query
rows=$(wcp_process_rows /eso/bin/apps/btstack /mnt/app/eso/bin/apps/btstack) || fail final-child-query
set -- $rows
[ "$#" -eq 2 ] && [ "$1" = "$BASE_PID" ] && [ "$2" = "$LAUNCHER_PID" ] || fail stock-child-changed-during-prepare
publish_state prepared || fail prepared-journal
CLEANUP_ARMED=0
echo "WCP_BTSTACK_OVERLAY_ACTIVE mode=stock activation_required=1 devb_pid=$DEVBPID wrapper_sha256=$WRAPPER_HASH"
