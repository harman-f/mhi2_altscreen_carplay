#!/bin/ksh
# MIBR/3 broker boot start (r10), called once from lsd.sh before J9, after the
# CPVC profile replay. With the single-writer marker the broker starts with
# --qualify-durable: a SET then writes the CPVC profile (backup .lastgood,
# atomic rename, RO restore) and materializes the value in the TEMP layer, so
# the change is live and persistent. If the durable preflight fails (marker,
# mount, recovery or profile parity), the same binary starts read-only.
# Never blocks the HMI boot. RAM-only credential, new per boot.
B=/mnt/app/root/mibr-v3
S=/tmp/mibr-v3-hmi.secret
P=/tmp/mibr-v3-service.pid
L=/tmp/mibr-v3-service.log
MARK=/mnt/app/root/altscreen-u2/config/mibr-v3-single-writer.enabled
# r21: KEY40 long-press route toggle daemon (passive DebugSPI receiver), independent of the broker state.
K40=$B/bin/mibr-key40d
if [ -x "$K40" ]; then
    if [ -s /tmp/mibr-key40d.pid ] && kill -0 "$(cat /tmp/mibr-key40d.pid)" 2>/dev/null; then :; else
        "$K40" >>/tmp/mibr-key40d.log 2>&1 &
        echo $! > /tmp/mibr-key40d.pid
    fi
fi
[ -x "$B/bin/mibr-v3-service" ] && [ -x "$B/bin/mibr-v3-genkey" ] || { echo MIBR_V3_BOOT=COMPONENT_MISSING; exit 0; }
if [ -s "$P" ] && kill -0 "$(cat "$P")" 2>/dev/null; then echo MIBR_V3_BOOT=ALREADY_RUNNING; exit 0; fi
[ -e "$S" ] || "$B/bin/mibr-v3-genkey" "$S" || { echo MIBR_V3_BOOT=GENKEY_FAILED; exit 0; }
if [ -r "$MARK" ] && [ "$(cat "$MARK" 2>/dev/null)" = 1 ]; then
    "$B/bin/mibr-v3-service" --port 28743 --secret-file "$S" --qualify-durable >"$L" 2>&1 &
    echo $! > "$P"
    sleep 2
    if kill -0 "$(cat "$P")" 2>/dev/null; then echo "MIBR_V3_BOOT=STARTED_DURABLE pid=$(cat "$P")"; exit 0; fi
    echo MIBR_V3_BOOT=DURABLE_PREFLIGHT_FAILED_FALLBACK_READONLY
fi
"$B/bin/mibr-v3-service" --port 28743 --secret-file "$S" >>"$L" 2>&1 &
echo $! > "$P"
echo "MIBR_V3_BOOT=STARTED_READONLY pid=$(cat "$P")"
exit 0
