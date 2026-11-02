#!/bin/ksh
# Platform watchdog, started once by mibr-v3-boot.ksh. Restarts the broker, the key daemon and the
# cockpit supervisor when they died, at most MAX times per boot each, and reports the state for the
# Diagnose page (/tmp/mibr-watch.state). Once the HMI is up for a while it clears the boot guard's
# counter. It never touches parity-session or CarPlay itself. /tmp/mibr-watch.stop ends it (installers).
PATH=$PATH:/proc/boot:/bin:/usr/bin:/mnt/app/armle/bin:/mnt/app/armle/usr/bin
A=${MIBR_WATCH_APP:-/mnt/app}
T=${MIBR_WATCH_TMP:-/tmp}
SHELLX=${MIBR_WATCH_SHELL:-/bin/ksh}
TICK=${MIBR_WATCH_TICK:-15}
INITIAL=${MIBR_WATCH_INITIAL:-60}
MAX=${MIBR_WATCH_MAX:-3}
HMI_STABLE=${MIBR_WATCH_HMI_STABLE:-120}
BOOT=$A/root/mibr-v3/mibr-v3-boot.ksh
BROKER=$A/root/mibr-v3/bin/mibr-v3-service
KEY40=$A/root/mibr-v3/bin/mibr-key40d
SUP=$A/root/altscreen-u2/scripts/parity_drive_supervisor.sh
SUP_ON=$A/root/mibr-parity-drive.enabled
GUARD=$A/root/mibr-kit/boot-guard.ksh
STATE=$T/mibr-watch.state
PID=$T/mibr-watch.pid
STOP=$T/mibr-watch.stop
HMI_UP=$T/mibr-hmi-up
LOG=$T/mibr-watch.log
PROFILE_READY=$T/mibr-cpvc-profile-ready

alive(){
    p=; [ -s "$1" ] && read p < "$1"
    [ -n "$p" ] && kill -0 "$p" 2>/dev/null
}
if alive "$PID"; then echo MIBR_WATCH=ALREADY_RUNNING; exit 0; fi
echo $$ > "$PID" || exit 1

broker_n=0; key40_n=0; sup_n=0
broker_s=ok; key40_s=ok; sup_s=ok
guard_cleared=0
waited=0

note(){ echo "$1" >> "$LOG" 2>/dev/null; }
publish(){
    { echo "broker=$broker_s"; echo "key40d=$key40_s"; echo "supervisor=$sup_s"; } > "$STATE.tmp" 2>/dev/null &&
        mv "$STATE.tmp" "$STATE" 2>/dev/null
}
restart_boot(){
    note "RESTART $1 attempt $2"
    "$SHELLX" "$BOOT" --from-watch >>"$LOG" 2>&1
}
check_broker(){
    [ -x "$BROKER" ] || { broker_s=absent; return 0; }
    if alive "$T/mibr-v3-service.pid"; then
        [ "$broker_n" -eq 0 ] && broker_s=ok || broker_s=restarted:$broker_n
        return 0
    fi
    if [ "$broker_n" -ge "$MAX" ]; then broker_s=gaveup:$broker_n; return 0; fi
    broker_n=$((broker_n+1)); broker_s=restarted:$broker_n
    restart_boot broker "$broker_n"
}
check_key40(){
    [ -x "$KEY40" ] || { key40_s=absent; return 0; }
    if alive "$T/mibr-key40d.pid"; then
        [ "$key40_n" -eq 0 ] && key40_s=ok || key40_s=restarted:$key40_n
        return 0
    fi
    if [ "$key40_n" -ge "$MAX" ]; then key40_s=gaveup:$key40_n; return 0; fi
    key40_n=$((key40_n+1)); key40_s=restarted:$key40_n
    restart_boot key40d "$key40_n"
}
check_supervisor(){
    # Switched off, or nothing for it to run yet: its own start would end at once by design.
    v=; [ -r "$SUP_ON" ] && read v < "$SUP_ON"
    if [ "$v" != 1 ] || [ ! -e "$PROFILE_READY" ]; then sup_s=off; return 0; fi
    if alive "$T/mibr-parity-drive-supervisor.pid"; then
        [ "$sup_n" -eq 0 ] && sup_s=ok || sup_s=restarted:$sup_n
        return 0
    fi
    if [ "$sup_n" -ge "$MAX" ]; then sup_s=gaveup:$sup_n; return 0; fi
    sup_n=$((sup_n+1)); sup_s=restarted:$sup_n
    note "RESTART supervisor attempt $sup_n"
    "$SHELLX" "$SUP" >>"$T/mibr-parity-drive-boot.log" 2>&1 &
}
check_guard(){
    [ "$guard_cleared" -eq 0 ] && [ -e "$HMI_UP" ] && [ "$waited" -ge "$HMI_STABLE" ] || return 0
    guard_cleared=1
    [ -r "$GUARD" ] && "$SHELLX" "$GUARD" clear >>"$LOG" 2>&1
}

sleep "$INITIAL"
waited=$INITIAL
while [ ! -e "$STOP" ]; do
    check_broker
    check_key40
    check_supervisor
    check_guard
    publish
    sleep "$TICK"
    waited=$((waited+TICK))
done
rm -f "$PID" 2>/dev/null
note STOPPED
exit 0
