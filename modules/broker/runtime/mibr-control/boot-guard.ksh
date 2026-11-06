#!/bin/ksh
# Boot guard, called from the MIBR-KIT block in lsd.sh before the MIBR JARs are put on the classpath.
#   check  rc 0 = load MIBR, rc 1 = this boot runs without MIBR.
#   clear  called by mibr-watch.ksh once the HMI has been up for a while.
# After LIMIT boots in a row without a cleared counter it writes the kill switch, so a menu JAR that
# stops the HMI from starting cannot lock the unit out. Back on: delete /mnt/app/root/mibr/state/boot/disabled.
# The ONLY kill switch is $MIBR_ROOT/state/boot/disabled and the counter is state/boot/boot-count; the legacy
# mibr-kit/disabled is never read (single kill switch, E4).
# A broken structure behaves as DISABLED (rc 1, MIBR_BOOT_GUARD=STRUCTURE_INVALID): state/boot exists but is
# not a directory, or $MIBR_ROOT/version/ is missing (never migrated / damaged install).
# A mere write failure of the counter is not a structure problem and keeps fail-open: MIBR loads.
# Any other failure of the guard itself also means "load MIBR": it must never be the reason for a lost feature.
PATH=$PATH:/proc/boot:/bin:/usr/bin
A=${MIBR_GUARD_APP:-/mnt/app}
MIBR_ROOT=${MIBR_ROOT:-$A/root/mibr}
BOOTD=$MIBR_ROOT/state/boot
VERSIOND=$MIBR_ROOT/version
COUNT=$BOOTD/boot-count
DISABLED=$BOOTD/disabled
LIMIT=${MIBR_GUARD_LIMIT:-4}
LEASE=${MIBR_APP_RW_LOCK:-/tmp/mibr-app-rw.lock}

read_count(){
    n=0
    [ -s "$COUNT" ] && read n < "$COUNT"
    case "$n" in ''|*[!0-9]*) n=0 ;; esac
}
write_file(){
    mount -uw "$A" 2>/dev/null || return 1
    [ -d "$BOOTD" ] || mkdir -p "$BOOTD" 2>/dev/null
    echo "$2" > "$1.tmp" 2>/dev/null && mv "$1.tmp" "$1" 2>/dev/null
    rc=$?
    sync
    mount -ur "$A" 2>/dev/null
    return $rc
}
lease_get(){
    i=0
    while :; do
        if ( set -C; echo $$ > "$LEASE" ) 2>/dev/null; then return 0; fi
        p=; read p < "$LEASE" 2>/dev/null
        if [ -n "$p" ] && ! kill -0 "$p" 2>/dev/null; then rm -f "$LEASE"; continue; fi
        i=$((i+1))
        [ "$i" -lt 30 ] || return 1
        sleep 0.1
    done
}

case "$1" in
    check)
        [ -r "$DISABLED" ] && { echo MIBR_BOOT_GUARD=DISABLED; exit 1; }
        if { [ -e "$BOOTD" ] && [ ! -d "$BOOTD" ]; } || [ ! -d "$VERSIOND" ]; then
            echo MIBR_BOOT_GUARD=STRUCTURE_INVALID; exit 1
        fi
        read_count
        if [ "$n" -ge "$LIMIT" ]; then
            write_file "$COUNT" 0
            write_file "$DISABLED" "auto: $n boots without a confirmed HMI start"
            echo "MIBR_BOOT_GUARD=AUTO_DISABLED count=$n"
            exit 1
        fi
        write_file "$COUNT" $((n+1)) || echo MIBR_BOOT_GUARD=COUNT_NOT_WRITTEN
        echo "MIBR_BOOT_GUARD=LOAD count=$((n+1))"
        exit 0
        ;;
    clear)
        read_count
        [ "$n" -eq 0 ] && exit 0
        lease_get || { echo MIBR_BOOT_GUARD=CLEAR_BUSY; exit 1; }
        write_file "$COUNT" 0
        rc=$?
        rm -f "$LEASE"
        echo MIBR_BOOT_GUARD=CLEARED
        exit $rc
        ;;
esac
echo 'usage: boot-guard.ksh check|clear'
exit 2
