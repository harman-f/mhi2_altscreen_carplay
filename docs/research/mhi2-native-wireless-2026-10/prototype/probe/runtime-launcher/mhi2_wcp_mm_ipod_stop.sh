#!/bin/sh
# Independent stop of only the journal-owned stock mm-ipod test process.
set -u
USB_LAN_CONFIRMED=0
case "$0" in */*) SELF_DIR=${0%/*} ;; *) SELF_DIR=. ;; esac
. "$SELF_DIR/../btstack-preload/mhi2_wcp_control_common.sh" || exit 2
WCP_RECOVER_STALE=1
trap 'wcp_release' 0
trap 'fail interrupted-state-retained' 1 2 15
fail() { echo "WCP_MM_IPOD_STOP_BLOCKED reason=$*" >&2; exit 2; }
while [ "$#" -gt 0 ]; do
    case "$1" in
      --usb-lan-confirmed) USB_LAN_CONFIRMED=1; shift ;;
      --help) echo "usage: $0 --usb-lan-confirmed"; exit 0 ;;
      *) fail "unknown-option:$1" ;;
    esac
done
[ "$USB_LAN_CONFIRMED" -eq 1 ] || fail usb-lan-not-confirmed
for c in sha256sum slay sleep chmod; do
    command -v "$c" >/dev/null 2>&1 || fail "utility-unavailable:$c"
done
wcp_acquire || fail control-lock-busy-or-invalid
wcp_snapshot && wcp_no_mutators && wcp_no_launchers || fail query-or-incomplete-launch
all=$(wcp_ipod_rows) || fail ipod-query
if [ ! -r "$WCP_IPOD_STATE" ]; then
    [ -z "$all" ] && [ ! -e /dev/ipod ] && [ ! -e /dev/ipod0 ] || fail unowned-ipod-process-or-namespace
    echo "WCP_MM_IPOD_STOP state=absent no_op=1"
    exit 0
fi
phase=; cfg=; owned_pid=0
while IFS='=' read key value; do
    case "$key" in
      phase) phase="$value" ;;
      config) cfg="$value" ;;
      pid) owned_pid="$value" ;;
    esac
done < "$WCP_IPOD_STATE"
case "$cfg" in /tmp/mhi2-wcp-iap2.*.cfg) ;; *) fail invalid-config-identity ;; esac
tag=${cfg#/tmp/mhi2-wcp-iap2.}; tag=${tag%.cfg}
case "$tag:$owned_pid" in *[!0-9:]*|:*|*:) fail invalid-process-identity ;; esac
[ "$tag" -gt 1 ] || fail invalid-config-tag
case "$phase" in config-intent|spawn-intent|process-wait|running|stopping) ;; *) fail invalid-journal-phase ;; esac
[ "$(sha256sum /mnt/app/armle/usr/sbin/mm-ipod 2>/dev/null | awk '{print $1}')" = de99a7f4dd941589c6d5173b7601856275c4ea615229058ec84b8e3efa748d27 ] || fail stock-mm-ipod-sha
own=$(wcp_owned_ipod_rows "$cfg") || fail owned-ipod-query
[ "$own" = "$all" ] || fail foreign-or-unidentified-ipod-process
set -- $own
if [ "$#" -ne 0 ]; then
    [ "$#" -eq 2 ] || fail owned-ipod-not-unique-daemonization-pending
    if [ "$owned_pid" = 0 ]; then
        case "$phase" in spawn-intent|process-wait) owned_pid=$1 ;; *) fail process-without-spawn-intent ;; esac
    fi
    [ "$1" = "$owned_pid" ] || fail owned-pid-changed
    {
      echo phase=stopping
      echo "config=$cfg"
      echo "pid=$owned_pid"
    } > "$WCP_IPOD_STATE.$$" || fail stop-journal-write
    chmod 0600 "$WCP_IPOD_STATE.$$" || fail stop-journal-permissions
    mv "$WCP_IPOD_STATE.$$" "$WCP_IPOD_STATE" || fail stop-journal-publish
    wcp_signal_once "$owned_pid" 15
    elapsed=0
    while [ "$elapsed" -lt 5 ]; do
        wcp_snapshot || fail stop-process-query
        own=$(wcp_owned_ipod_rows "$cfg") || fail stop-owner-query
        [ -n "$own" ] || break
        sleep 1; elapsed=$((elapsed+1))
    done
    if [ -n "$own" ]; then
        # Escalation is based on observed lifetime, never slay's count status.
        # Recheck unique fingerprint/PID immediately before the one force kill.
        all=$(wcp_ipod_rows) || fail force-process-query
        [ "$own" = "$all" ] || fail foreign-ipod-before-force
        set -- $own
        [ "$#" -eq 2 ] && [ "$1" = "$owned_pid" ] || fail force-owner-changed
        wcp_signal_once "$owned_pid" 9
    fi
fi
elapsed=0
while [ "$elapsed" -lt 10 ]; do
    wcp_snapshot && wcp_no_mutators && wcp_no_launchers || fail final-process-query
    all=$(wcp_ipod_rows) || fail final-ipod-query
    if [ -z "$all" ] && [ ! -e /dev/ipod ] && [ ! -e /dev/ipod0 ]; then break; fi
    sleep 1; elapsed=$((elapsed+1))
done
[ -z "$all" ] && [ ! -e /dev/ipod ] && [ ! -e /dev/ipod0 ] || fail process-or-namespace-not-drained-retained
# Recheck absence across a second snapshot before removing the owned config.
sleep 1
wcp_snapshot && wcp_no_mutators && wcp_no_launchers || fail stable-absence-query
[ -z "$(wcp_ipod_rows)" ] && [ ! -e /dev/ipod ] && [ ! -e /dev/ipod0 ] || fail absence-not-stable
rm -f "$cfg" "$WCP_IPOD_STATE" || fail owned-config-cleanup

echo "WCP_MM_IPOD_STOP result=owned-process-and-namespaces-drained"
