#!/bin/ksh
# mibr-engine.ksh get | set <gas|diesel|electric|cng>
# Reads or changes the engine type that the HARMAN [vehicle] block of /etc/mm/iap2.cfg announces to the iPhone.
# The iPhone sees it in the CarPlay Identify; mm-ipod reads the file only at its start, so a change takes effect
# after the next restart. iap2.cfg is the single source of truth (no second config file).
# Output (one key=value per line): engine=<value in iap2.cfg> announced=<value at boot> pending=<0|1> result=<OK|...>
# Safety: only the engine= line inside [vehicle] is replaced; line count must stay equal; atomic mv on the same
# filesystem; /mnt/system is remounted read-only again on every path.
CFG=${MIBR_ENGINE_CFG:-/mnt/system/etc/mm/iap2.cfg}
SYS=${MIBR_ENGINE_MOUNT:-/mnt/system}
BOOTMARK=${MIBR_ENGINE_BOOT:-/tmp/mibr-engine.boot}
LOCK=${MIBR_ENGINE_LOCK:-/tmp/mibr-engine.lock}
NOMOUNT=${MIBR_ENGINE_NOMOUNT:-0}
NEW=$CFG.engine.$$

say(){ echo "$1"; }
cur(){
    inv=0; val=
    while IFS= read -r line; do
        case "$line" in
            "["*) if [ "$line" = "[vehicle]" ]; then inv=1; else inv=0; fi ;;
            engine=*) if [ "$inv" -eq 1 ]; then val=${line#engine=}; fi ;;
        esac
    done < "$CFG"
    echo "$val"
}
valid(){ case "$1" in gas|diesel|electric|cng) return 0 ;; esac; return 1; }
ro(){ [ "$NOMOUNT" = 1 ] || { sync; mount -ur "$SYS" 2>/dev/null; }; }
done_out(){
    c=$(cur); b=
    [ -s "$BOOTMARK" ] && read b < "$BOOTMARK"
    [ -n "$b" ] || b=$c
    p=0; [ "$c" = "$b" ] || p=1
    say "engine=$c"; say "announced=$b"; say "pending=$p"; say "result=$1"
    rm -f "$LOCK"
    [ "$1" = OK ] && exit 0
    exit 1
}
[ -f "$CFG" ] || { say "engine="; say "announced="; say "pending=0"; say "result=NO_CFG"; exit 1; }
# /tmp on the unit is a RAM filesystem without mkdir/rmdir: the lock is a pid file created with noclobber.
getlock(){
    if ( set -C; echo $$ > "$LOCK" ) 2>/dev/null; then return 0; fi
    p=; read p < "$LOCK" 2>/dev/null
    if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then return 1; fi
    rm -f "$LOCK"
    ( set -C; echo $$ > "$LOCK" ) 2>/dev/null
}
getlock || { say "result=BUSY"; exit 1; }
c0=$(cur)
# The value the running mm-ipod announces = the value at first look after boot (/tmp is RAM, empty at boot).
if [ ! -s "$BOOTMARK" ] && [ -n "$c0" ]; then echo "$c0" > "$BOOTMARK" 2>/dev/null; fi
case "$1" in
    get) done_out OK ;;
    set)
        valid "$2" || done_out BAD_VALUE
        [ -n "$c0" ] || done_out NO_VEHICLE_BLOCK
        [ "$c0" = "$2" ] && done_out OK
        n0=0; while IFS= read -r line; do n0=$((n0+1)); done < "$CFG"
        inv=0; n1=0; hit=0
        : > "$NEW" || done_out NO_TMP
        while IFS= read -r line; do
            case "$line" in
                "["*) if [ "$line" = "[vehicle]" ]; then inv=1; else inv=0; fi ;;
                engine=*) if [ "$inv" -eq 1 ]; then line="engine=$2"; hit=$((hit+1)); fi ;;
            esac
            echo "$line" >> "$NEW"; n1=$((n1+1))
        done < "$CFG"
        if [ "$hit" -ne 1 ] || [ "$n0" -ne "$n1" ]; then rm -f "$NEW"; done_out BAD_LAYOUT; fi
        if [ "$NOMOUNT" != 1 ]; then mount -uw "$SYS" 2>/dev/null || { rm -f "$NEW"; done_out REMOUNT_FAILED; }; fi
        if cp "$NEW" "$NEW.2" 2>/dev/null && chmod 755 "$NEW.2" 2>/dev/null && mv "$NEW.2" "$CFG" 2>/dev/null; then rm -f "$NEW"; ro; else rm -f "$NEW" "$NEW.2"; ro; done_out WRITE_FAILED; fi
        [ "$(cur)" = "$2" ] || done_out VERIFY_FAILED
        done_out OK ;;
    *) done_out USAGE ;;
esac
