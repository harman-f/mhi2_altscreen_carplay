#!/bin/sh
#
# Read-only target verifier for the MU1440 Wireless CarPlay vehicle bundle.
# It does not start, stop, preload, mount, reconfigure, or persist anything.
#

set -u

USB_LAN_CONFIRMED=0
OUT=""

usage()
{
    echo "usage: $0 --usb-lan-confirmed [--output FILE]" >&2
}

emit()
{
    if [ -n "$OUT" ]; then
        printf '%s\n' "$*" | tee -a "$OUT"
    else
        printf '%s\n' "$*"
    fi
}

sha_gate()
{
    path="$1"
    expected="$2"
    label="$3"

    if [ ! -r "$path" ]; then
        emit "VERIFY_FAIL label=$label reason=missing path=$path"
        return 1
    fi
    actual=$(sha256sum "$path" 2>/dev/null | awk '{print $1}')
    if [ "$actual" != "$expected" ]; then
        emit "VERIFY_FAIL label=$label reason=sha256 actual=$actual expected=$expected path=$path"
        return 1
    fi
    emit "VERIFY_OK label=$label sha256=$actual path=$path"
    return 0
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --usb-lan-confirmed)
            USB_LAN_CONFIRMED=1
            shift
            ;;
        --output)
            [ "$#" -ge 2 ] || { usage; exit 64; }
            OUT="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            usage
            exit 64
            ;;
    esac
done

[ "$USB_LAN_CONFIRMED" -eq 1 ] || {
    echo "VERIFY_BLOCKED reason=usb-lan-not-confirmed" >&2
    exit 2
}

command -v sha256sum >/dev/null 2>&1 || {
    echo "VERIFY_BLOCKED reason=sha256sum-unavailable" >&2
    exit 2
}

if [ -n "$OUT" ]; then
    : > "$OUT" || exit 2
fi

emit "MHI2_WCP_VERIFY_BEGIN"
emit "date=$(date 2>/dev/null || true)"
emit "hostname=$(hostname 2>/dev/null || true)"

fail=0
sha_gate /eso/bin/apps/connectivity_launcher 13586753493d9cb4709196c672f81cbbf81ebfe44ae655a330d98324e04d8bb8 connectivity-launcher || fail=1
sha_gate /eso/bin/apps/bluetooth d3efa55f8bd089c027c89e84fda3e8f5136afd22f7e11862acd4f305d3dd5995 bluetooth || fail=1
sha_gate /eso/bin/apps/btstack d2b55046b8f22302c27811ab2070dc87f0408702c8764b43ad2ff135a66444a0 btstack || fail=1
sha_gate /mnt/app/armle/usr/sbin/mm-ipod de99a7f4dd941589c6d5173b7601856275c4ea615229058ec84b8e3efa748d27 mm-ipod || fail=1
sha_gate /mnt/app/armle/lib/dll/ipod-drvr-iap2.so 7149a3e75b1b19e89021841759f420a6eced456b6c697a3dd1f0e436abea0b8c ipod-drvr-iap2 || fail=1
sha_gate /mnt/app/armle/lib/dll/ipod-acp-i2c.so 551f974eb2f9141bc4cfc598d15042d30a9ee8c44dcb0837d81ab901f3097660 ipod-acp-i2c || fail=1

emit "===== interfaces ====="
for ifn in uap0 mlan0; do
    if ifconfig "$ifn" >/dev/null 2>&1; then
        emit "$ifn=present"
    else
        emit "$ifn=absent"
    fi
done

emit "===== MFi auth hardware ====="
if [ -e /dev/i2c8 ]; then
    emit "/dev/i2c8=present"
    ls -l /dev/i2c8 2>/dev/null || true
else
    emit "/dev/i2c8=absent"
    fail=1
fi
emit ""

emit "===== iAP namespace ====="
for p in /dev/ipod /dev/ipod0 /dev/ipod1 /dev/mhi2-iap2-rfcomm; do
    if [ -e "$p" ]; then
        emit "$p=present"
    else
        emit "$p=absent"
    fi
done

emit "===== launcher child topology ====="
if command -v ps >/dev/null 2>&1; then
    ps -ef 2>/dev/null | awk '
      $8=="./bin/apps/connectivity_launcher" ||
      $8=="/eso/bin/apps/connectivity_launcher" ||
      $8=="/mnt/app/eso/bin/apps/connectivity_launcher" ||
      $8=="/eso/bin/apps/btstack" ||
      $8=="/mnt/app/eso/bin/apps/btstack" ||
      $8=="/eso/bin/apps/bluetooth" ||
      $8=="/mnt/app/eso/bin/apps/bluetooth" { print }' || true
fi
emit ""

emit "===== mm-ipod argv ====="
if command -v pidin >/dev/null 2>&1; then
    pidin ar 2>/dev/null | grep 'mm-ipod' || true
fi

if [ "$fail" -ne 0 ]; then
    emit "MHI2_WCP_VERIFY_END result=blocked"
    exit 2
fi

emit "MHI2_WCP_VERIFY_END result=ok"
exit 0
