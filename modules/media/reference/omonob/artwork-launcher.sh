#!/bin/ksh
# Helper has a crash-safe kernel lock. Duplicate launch attempts return 75.
ROOT=/mnt/app/carplaymaps/information
mkdir -p /ramdisk/cpmap-info || exit 1
while [ -f "$ROOT/ENABLED" ] && [ -x "$ROOT/carplay_artwork_helper" ]; do
    "$ROOT/carplay_artwork_helper" </dev/null >/dev/null 2>&1
    rc=$?
    [ "$rc" -ne 75 ] || exit 0
    sleep 2
done
