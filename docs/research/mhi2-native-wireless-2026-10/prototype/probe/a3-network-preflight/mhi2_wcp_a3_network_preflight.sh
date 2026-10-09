#!/bin/sh
#
# MU1440 Wireless CarPlay A3 network preflight.
# READ-ONLY with respect to WLAN/network configuration.
#
# It intentionally does not call:
#   ifconfig <write args>, uaputl, wpa_cli, slay, kill, pfctl,
#   route add/delete, dnsmasq restart, or wpa_supplicant restart.
#

set -u

OUT=""
if [ "${1:-}" = "--output" ] && [ -n "${2:-}" ]; then
    OUT="$2"
fi

emit()
{
    if [ -n "$OUT" ]; then
        printf '%s\n' "$*" | tee -a "$OUT"
    else
        printf '%s\n' "$*"
    fi
}

run_ro()
{
    label="$1"
    shift
    emit "===== $label ====="
    if [ -n "$OUT" ]; then
        "$@" 2>&1 | tee -a "$OUT"
    else
        "$@" 2>&1
    fi
    emit ""
}

if [ -n "$OUT" ]; then
    : > "$OUT" || exit 1
fi

emit "A3_PREFLIGHT_BEGIN"
emit "date=$(date 2>/dev/null || true)"
emit "hostname=$(hostname 2>/dev/null || true)"
emit ""

for ifn in uap0 mlan0; do
    emit "===== interface:$ifn ====="
    if ifconfig "$ifn" >/dev/null 2>&1; then
        emit "present=1"
        if [ -n "$OUT" ]; then
            ifconfig "$ifn" 2>&1 | tee -a "$OUT"
        else
            ifconfig "$ifn" 2>&1
        fi
    else
        emit "present=0"
    fi
    emit ""
done

if command -v netstat >/dev/null 2>&1; then
    run_ro "routes" netstat -rn
fi

if command -v pidin >/dev/null 2>&1; then
    emit "===== processes ====="
    for p in wpa_supplicant dnsmasq connectionmanager btstack bluetooth mm-ipod mdnsd; do
        pidin -p "$p" arg 2>/dev/null || true
    done
    emit ""

    emit "===== mm-ipod argv candidates ====="
    pidin ar 2>/dev/null | grep 'mm-ipod' || true
    emit ""
fi

emit "===== iAP runtime namespace ====="
for p in /dev/ipod /dev/ipod0 /dev/ipod1 /dev/mhi2-iap2-rfcomm; do
    if [ -e "$p" ]; then
        emit "$p=present"
        ls -l "$p" 2>/dev/null || true
    else
        emit "$p=absent"
    fi
done
emit ""

emit "===== stock ACP module ====="
ACP_MOD=/mnt/app/armle/lib/dll/ipod-acp-i2c.so
if [ -r "$ACP_MOD" ]; then
    ls -l "$ACP_MOD" 2>/dev/null || true
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$ACP_MOD" 2>/dev/null || true
    fi
else
    emit "$ACP_MOD=(missing or unreadable)"
fi
emit ""

emit "===== stock launcher hints ====="
for cfg in /etc/usblauncher.lua /etc/mm/ipod.cfg; do
    if [ -r "$cfg" ]; then
        emit "--- $cfg ---"
        grep -n 'mm-ipod' "$cfg" 2>/dev/null || true
        grep -n 'ipod-acp' "$cfg" 2>/dev/null || true
        grep -n 'i2c' "$cfg" 2>/dev/null || true
    else
        emit "$cfg=(missing or unreadable)"
    fi
done
emit ""

emit "===== stock-markers ====="
for p in /tmp/mvloaded /tmp/uap0 /tmp/mlan0; do
    if [ -e "$p" ]; then
        emit "$p=present"
    else
        emit "$p=absent"
    fi
done
emit ""

emit "===== /tmp/uaputl.cfg ====="
if [ -r /tmp/uaputl.cfg ]; then
    # Credential extraction is separate; preflight logs never need AP secrets.
    emit "readable=1 contents=omitted-credentials"
else
    emit "(missing or unreadable)"
fi
emit ""

emit "===== /etc/mm/iap2.cfg [WiFi] ====="
if [ -r /etc/mm/iap2.cfg ]; then
    emit "readable=1 wifi_contents=omitted-credentials"
else
    emit "(missing or unreadable)"
fi
emit ""

emit "===== /etc/mm/iap2.cfg [bluetooth] ====="
if [ -r /etc/mm/iap2.cfg ]; then
    awk '
        BEGIN { in_bt=0 }
        /^\[bluetooth\][[:space:]]*$/ { in_bt=1; print; next }
        /^\[/ && in_bt { exit }
        in_bt { print }
    ' /etc/mm/iap2.cfg 2>/dev/null
else
    emit "(missing or unreadable)"
fi
emit ""

emit "A3_PREFLIGHT_END"
exit 0
