#!/bin/ksh
# mibr-menu.ksh load
# Stores the menu file from the SD card: /mibr-menu/mibr-menu.txt -> config/mibr-menu.conf. The menu has checked the
# file before this and compares the stored bytes afterwards.
# Last output line: result=<OK|NO_FILE|TOO_LARGE|BUSY|WRITE_FAILED|USAGE>.
SRC=${MIBR_MENU_SRC:-/net/mmx/fs/sda0/mibr-menu/mibr-menu.txt}
DIR=${MIBR_MENU_DIR:-/mnt/app/root/altscreen-u2/config}
MNT=${MIBR_VIEW_MOUNT:-/mnt/app}
NOMOUNT=${MIBR_VIEW_NOMOUNT:-0}
APPLOCK=${MIBR_APP_RW_LOCK:-/tmp/mibr-app-rw.lock}
MAX=16384

finish(){ echo "result=$1"; [ "$1" = OK ] && exit 0; exit 1; }
# Same write window as mibr-view.ksh and the broker (mibr_app_rw_lease.c).
lease_get(){
    lease_try=0
    while :; do
        if ( set -C; echo $$ > "$APPLOCK" ) 2>/dev/null; then return 0; fi
        lease_pid=; read lease_pid < "$APPLOCK" 2>/dev/null
        if [ -n "$lease_pid" ] && ! kill -0 "$lease_pid" 2>/dev/null; then rm -f "$APPLOCK"; continue; fi
        lease_try=$((lease_try+1))
        [ "$lease_try" -lt 30 ] || return 1
        sleep 0.1
    done
}
rw(){
    [ "$NOMOUNT" = 1 ] && return 0
    lease_get || return 1
    mount -uw "$MNT" 2>/dev/null || { rm -f "$APPLOCK"; return 1; }
}
ro(){
    [ "$NOMOUNT" = 1 ] && return 0
    sync; mount -ur "$MNT" 2>/dev/null
    rm -f "$APPLOCK"
}
[ "$1" = load ] || finish USAGE
[ -f "$SRC" ] || finish NO_FILE
size=$(ls -l "$SRC" 2>/dev/null) || finish NO_FILE
set -- $size
{ [ "$5" -gt 0 ] && [ "$5" -le "$MAX" ]; } 2>/dev/null || finish TOO_LARGE
rw || finish BUSY
STAGE="$DIR/mibr-menu.conf.new.$$"
if cp "$SRC" "$STAGE" 2>/dev/null && chmod 644 "$STAGE" 2>/dev/null && mv "$STAGE" "$DIR/mibr-menu.conf" 2>/dev/null; then
    ro; finish OK
fi
rm -f "$STAGE"; ro; finish WRITE_FAILED
