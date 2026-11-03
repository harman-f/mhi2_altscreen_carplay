#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

MARKER=/mnt/app/root/mibr-isotx2-gate-disable
LIB=/mnt/app/eso/lib/libmibr_isotx2_gate.so

remount_rw()
{
    mount -uw /mnt/app 2>/dev/null || {
        echo "FAIL cannot remount /mnt/app rw"
        exit 20
    }
}

remount_ro()
{
    sync
    mount -ur /mnt/app 2>/dev/null || true
}

status()
{
    if [ -e "$MARKER" ]; then
        echo "PRELOAD_NEXT_BOOT=DISABLED"
    else
        echo "PRELOAD_NEXT_BOOT=ENABLED"
    fi
    echo "disable_marker=$MARKER"
    if [ -r "$LIB" ]; then
        echo "gate_library=present"
    else
        echo "gate_library=missing"
    fi
}

case "${1:-status}" in
    status)
        status
        ;;
    disable)
        remount_rw
        : > "$MARKER" || {
            remount_ro
            echo "FAIL cannot create $MARKER"
            exit 21
        }
        remount_ro
        [ -f "$MARKER" ] || {
            echo "FAIL disable marker verification failed"
            exit 22
        }
        echo "PRELOAD_NEXT_BOOT=DISABLED"
        echo "Next boot uses the exact stock DisplayManager launch."
        echo "Current DisplayManager process is unchanged until reboot."
        ;;
    enable)
        remount_rw
        rm -f "$MARKER" 2>/dev/null || {
            remount_ro
            echo "FAIL cannot remove $MARKER"
            exit 23
        }
        remount_ro
        [ ! -e "$MARKER" ] || {
            echo "FAIL disable marker still exists"
            exit 24
        }
        echo "PRELOAD_NEXT_BOOT=ENABLED"
        echo "Next boot preloads libmibr_isotx2_gate.so into DisplayManager."
        echo "Gate mode itself still defaults to STOCK."
        echo "Current DisplayManager process is unchanged until reboot."
        ;;
    *)
        echo "Usage: $0 [status|enable|disable]"
        exit 2
        ;;
esac
