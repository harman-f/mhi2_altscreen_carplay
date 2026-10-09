#!/bin/sh
#
# First-vehicle MU1440 Wireless CarPlay mm-ipod launcher.
#
# This script intentionally starts only the stock mm-ipod/iAP2 side. The
# RFCOMM provider must already be active and expose /dev/mhi2-iap2-rfcomm.
# Nothing is persisted to the stock filesystem.
#

set -u

MM_IPOD=/mnt/app/armle/usr/sbin/mm-ipod
ACP_MODULE=/mnt/app/armle/lib/dll/ipod-acp-i2c.so
IAP2_DRIVER=/mnt/app/armle/lib/dll/ipod-drvr-iap2.so
BASE_CFG=/etc/mm/iap2.cfg
A3_STATE=/tmp/mhi2-wcp-a3-wifi.state
RUNTIME_CFG="/tmp/mhi2-wcp-iap2.$$.cfg"
ENDPOINT=/dev/mhi2-iap2-rfcomm
MOUNT_PATH=/dev/ipod0
LOG_PATH=/tmp/mhi2-wcp-mm-ipod.log
LINKPARAMS=0100dc0549001e0305000008
ACP_SPEC=
ACP_SPEC_SOURCE=
DERIVED_ACP_SPEC='i2c,addr=0x11,path=/dev/i2c8'
USB_LAN_CONFIRMED=0
DRY_RUN=0

MM_IPOD_SHA256=de99a7f4dd941589c6d5173b7601856275c4ea615229058ec84b8e3efa748d27
ACP_MODULE_SHA256=551f974eb2f9141bc4cfc598d15042d30a9ee8c44dcb0837d81ab901f3097660
IAP2_DRIVER_SHA256=7149a3e75b1b19e89021841759f420a6eced456b6c697a3dd1f0e436abea0b8c

case "$0" in
    */*) SELF_DIR=${0%/*} ;;
    *) SELF_DIR=. ;;
esac
. "$SELF_DIR/../btstack-preload/mhi2_wcp_control_common.sh" || exit 2
trap 'wcp_release' 0
trap 'fail interrupted-owned-state-retained' 1 2 15
CONFIG_GEN="$SELF_DIR/../runtime-iap2-config/mhi2-wcp-iap2-runtime-config"
BTSTREAM_DIR="$SELF_DIR/../transport-btstream"

usage()
{
    cat <<EOF
usage: $0 (--acp-spec SPEC | --use-derived-acp-spec) --usb-lan-confirmed [options]

Required ACP choice:
  --acp-spec SPEC          exact stock mm-ipod -a argument captured live
  --use-derived-acp-spec   explicitly use the independently reconstructed
                           MU1440 MFi hardware spec:
                           i2c,addr=0x11,path=/dev/i2c8

Required:
  --usb-lan-confirmed      acknowledge independent USB-LAN recovery is active

Options:
  --config-generator PATH  runtime config generator binary
  --btstream-dir DIR       directory containing ipod-transport-btstream.so
  --mount PATH             device mount (default: /dev/ipod0)
  --log PATH               mm-ipod logfile
  --dry-run                validate and print sanitized launch plan only
  --help
EOF
}

fail()
{
    echo "WCP_LAUNCH_BLOCKED reason=$*" >&2
    exit 2
}

sha_check()
{
    path="$1"
    expected="$2"
    label="$3"

    [ -r "$path" ] || fail "$label-missing:$path"
    if ! command -v sha256sum >/dev/null 2>&1; then
        fail "sha256sum-unavailable"
    fi
    actual=$(sha256sum "$path" 2>/dev/null | awk '{print $1}')
    [ "$actual" = "$expected" ] || fail "$label-sha256-mismatch:$actual"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --acp-spec)
            [ "$#" -ge 2 ] || fail "missing-acp-spec-value"
            ACP_SPEC="$2"
            ACP_SPEC_SOURCE=explicit
            shift 2
            ;;
        --use-derived-acp-spec)
            ACP_SPEC="$DERIVED_ACP_SPEC"
            ACP_SPEC_SOURCE=derived-mfi-hardware
            shift
            ;;
        --usb-lan-confirmed)
            USB_LAN_CONFIRMED=1
            shift
            ;;
        --config-generator)
            [ "$#" -ge 2 ] || fail "missing-config-generator-value"
            CONFIG_GEN="$2"
            shift 2
            ;;
        --btstream-dir)
            [ "$#" -ge 2 ] || fail "missing-btstream-dir-value"
            BTSTREAM_DIR="$2"
            shift 2
            ;;
        --mount)
            [ "$#" -ge 2 ] || fail "missing-mount-value"
            MOUNT_PATH="$2"
            shift 2
            ;;
        --log)
            [ "$#" -ge 2 ] || fail "missing-log-value"
            LOG_PATH="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            usage >&2
            fail "unknown-option:$1"
            ;;
    esac
done

[ "$USB_LAN_CONFIRMED" -eq 1 ] || fail "usb-lan-not-confirmed"
[ -n "$ACP_SPEC" ] || fail "acp-spec-required-use---acp-spec-or---use-derived-acp-spec"
case "$ACP_SPEC" in
    i2c|i2c,*) ;;
    *) fail "unexpected-acp-module-spec" ;;
esac

[ "$MOUNT_PATH" = /dev/ipod0 ] || fail "first-probe-mount-must-be-/dev/ipod0"

wcp_acquire || fail control-lock-busy-or-invalid

sha_check "$MM_IPOD" "$MM_IPOD_SHA256" "mm-ipod"
sha_check "$ACP_MODULE" "$ACP_MODULE_SHA256" "ipod-acp-i2c"
sha_check "$IAP2_DRIVER" "$IAP2_DRIVER_SHA256" "ipod-drvr-iap2"

[ -x "$CONFIG_GEN" ] || fail "config-generator-missing:$CONFIG_GEN"
[ -r "$BTSTREAM_DIR/ipod-transport-btstream.so" ] || fail "btstream-missing:$BTSTREAM_DIR/ipod-transport-btstream.so"
[ -r "$BASE_CFG" ] || fail "stock-iap2-config-missing"
[ -r "$A3_STATE" ] || fail "a3-state-missing"
[ -e /dev/i2c8 ] || fail "mfi-i2c8-missing"
[ -e "$ENDPOINT" ] || fail "rfcomm-endpoint-missing"
[ -r "$ENDPOINT" ] || fail "rfcomm-endpoint-not-readable"
[ -w "$ENDPOINT" ] || fail "rfcomm-endpoint-not-writable"

wcp_snapshot && wcp_no_mutators || fail process-query-or-worker-conflict
[ -z "$(wcp_ipod_rows)" ] || fail mm-ipod-already-running
[ ! -e "$WCP_IPOD_STATE" ] || fail previous-owned-mm-ipod-state
wcp_load_control && [ "$WCP_PHASE" = active ] || fail control-not-active
wcp_ready_for_pid "$WCP_HOOK_PID" || fail provider-not-ready
rows=$(wcp_process_rows /ramdisk/mhi2-wcp-stock/btstack) || fail provider-process-query
set -- $rows
[ "$#" -eq 2 ] && [ "$1" = "$WCP_HOOK_PID" ] && [ "$2" = "$WCP_LAUNCHER_PID" ] || fail provider-process-identity

[ ! -e /dev/ipod ] || fail "root-ipod-namespace-already-present"
[ ! -e "$MOUNT_PATH" ] || fail "target-mount-already-present"

echo "WCP_LAUNCH_READY endpoint=$ENDPOINT mount=$MOUNT_PATH runtime_cfg=$RUNTIME_CFG"
echo "WCP_LAUNCH_READY linkparams=$LINKPARAMS log=$LOG_PATH acp_module=i2c acp_source=$ACP_SPEC_SOURCE"
echo "WCP_LAUNCH_READY acp_path=/dev/i2c8 acp_addr=0x11"
echo "WCP_LAUNCH_READY stock_consumers=dio_manager,smartphone_integrator mount_contract=/dev/ipod0"

if [ "$DRY_RUN" -eq 1 ]; then
    echo "WCP_LAUNCH_DRY_RUN no_process_started=1"
    exit 0
fi

LD_LIBRARY_PATH="$BTSTREAM_DIR:/mnt/app/armle/lib/dll:${LD_LIBRARY_PATH:-}"
export LD_LIBRARY_PATH

[ ! -e "$RUNTIME_CFG" ] || fail config-collision
IPOD_PID=0
write_ipod_state()
{
    {
      echo "phase=$1"
      echo "config=$RUNTIME_CFG"
      echo "pid=$IPOD_PID"
    } > "$WCP_IPOD_STATE.$$" || return 1
    chmod 0600 "$WCP_IPOD_STATE.$$" || return 1
    mv "$WCP_IPOD_STATE.$$" "$WCP_IPOD_STATE"
}
write_ipod_state config-intent || fail config-journal
"$CONFIG_GEN" --base "$BASE_CFG" --state "$A3_STATE" --output "$RUNTIME_CFG" || fail runtime-config-generation-failed
chmod 0600 "$RUNTIME_CFG" || fail config-permissions
write_ipod_state spawn-intent || fail spawn-journal
"$MM_IPOD" \
    -a "$ACP_SPEC" \
    -d "iap2,config=$RUNTIME_CFG" \
    -t "btstream,path=$ENDPOINT,linkparams=$LINKPARAMS" \
    -m "$MOUNT_PATH" \
    -l "$LOG_PATH" \
    -v &
SPAWN_PID=$!
write_ipod_state process-wait || fail process-wait-journal
elapsed=0
while [ "$elapsed" -lt 15 ]; do
    wcp_snapshot || fail launch-process-query
    rows=$(wcp_owned_ipod_rows "$RUNTIME_CFG") || fail launch-owner-query
    all=$(wcp_ipod_rows) || fail launch-process-query
    set -- $rows
    if [ "$#" -eq 2 ] && [ "$rows" = "$all" ] && [ -e /dev/ipod ] && [ -e "$MOUNT_PATH" ]; then
        candidate=$1
        sleep 1
        wcp_snapshot || fail launch-stability-query
        rows=$(wcp_owned_ipod_rows "$RUNTIME_CFG") || fail launch-stability-query
        all=$(wcp_ipod_rows) || fail launch-stability-query
        set -- $rows
        if [ "$#" -eq 2 ] && [ "$1" = "$candidate" ] && [ "$rows" = "$all" ]; then
            IPOD_PID=$candidate
            break
        fi
    fi
    sleep 1; elapsed=$((elapsed+1))
done
[ "$IPOD_PID" -gt 1 ] || fail launch-timeout-owned-state-retained
wcp_ready_for_pid "$WCP_HOOK_PID" || fail provider-lost-during-launch
write_ipod_state running || fail running-journal
echo "WCP_LAUNCH_RUNNING pid=$IPOD_PID spawn_pid=$SPAWN_PID runtime_cfg=$RUNTIME_CFG stop_helper=$SELF_DIR/mhi2_wcp_mm_ipod_stop.sh"
