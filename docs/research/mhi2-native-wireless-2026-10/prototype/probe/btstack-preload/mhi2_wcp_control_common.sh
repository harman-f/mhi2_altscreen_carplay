#!/bin/sh
# Shared volatile control contract. Source from each independent entry point.
# No flock/GNU options; exact QNX ps/mount formats are checked, not guessed.
WCP_LOCK=/tmp/mhi2-wcp-control.lock
WCP_CONTROL=/tmp/mhi2-wcp-btstack-control.state
WCP_READY=/tmp/mhi2-wcp-provider.ready
WCP_IPOD_STATE=/tmp/mhi2-wcp-mm-ipod.state
WCP_HAS_LOCK=0
WCP_OWN_LOCK=0
WCP_PS=
WCP_MOUNTS=

wcp_acquire()
{
    umask 077
    for c in ps awk mkdir mv rm rmdir; do
        command -v "$c" >/dev/null 2>&1 || return 1
    done
    if [ -n "${WCP_LOCK_OWNER:-}" ]; then
        [ -r "$WCP_LOCK/owner" ] || return 1
        read wcp_owner < "$WCP_LOCK/owner" || return 1
        [ "$wcp_owner" = "$WCP_LOCK_OWNER" ] || return 1
        kill -0 "$wcp_owner" 2>/dev/null || return 1
        printf '%s\n' "$WCP_LOCK_OWNER" > "$WCP_LOCK/lease.$$" || return 1
    else
        if ! mkdir "$WCP_LOCK" 2>/dev/null; then
            [ "${WCP_RECOVER_STALE:-0}" -eq 1 ] || return 1
            [ -r "$WCP_LOCK/owner" ] || return 1
            read wcp_owner < "$WCP_LOCK/owner" || return 1
            case "$wcp_owner" in ''|*[!0-9]*) return 1 ;; esac
            [ "$wcp_owner" -gt 1 ] || return 1
            kill -0 "$wcp_owner" 2>/dev/null && return 1
            mkdir "$WCP_LOCK.recovery" 2>/dev/null || return 1
            # Recheck under the recovery claim. Preserve abandoned files.
            read wcp_again < "$WCP_LOCK/owner" || {
                rmdir "$WCP_LOCK.recovery"; return 1;
            }
            if [ "$wcp_again" != "$wcp_owner" ] || kill -0 "$wcp_owner" 2>/dev/null; then
                rmdir "$WCP_LOCK.recovery"; return 1
            fi
            for lease in "$WCP_LOCK"/lease.*; do
                [ -f "$lease" ] || continue
                child=${lease##*.}
                case "$child" in ''|*[!0-9]*) rmdir "$WCP_LOCK.recovery"; return 1 ;; esac
                if kill -0 "$child" 2>/dev/null; then
                    rmdir "$WCP_LOCK.recovery"; return 1
                fi
            done
            stale="$WCP_LOCK.abandoned.$$"
            if [ -e "$stale" ] || ! mv "$WCP_LOCK" "$stale"; then
                rmdir "$WCP_LOCK.recovery"; return 1
            fi
            if ! mkdir "$WCP_LOCK" 2>/dev/null; then
                rmdir "$WCP_LOCK.recovery"; return 1
            fi
            rmdir "$WCP_LOCK.recovery" || return 1
        fi
        WCP_OWN_LOCK=1
        WCP_HAS_LOCK=1
        WCP_LOCK_OWNER=$$
        printf '%s\n' "$$" > "$WCP_LOCK/owner.$$" || return 1
        mv "$WCP_LOCK/owner.$$" "$WCP_LOCK/owner" || return 1
    fi
    export WCP_LOCK_OWNER
    WCP_HAS_LOCK=1
    WCP_PS="$WCP_LOCK/ps.$$"
    WCP_MOUNTS="$WCP_LOCK/mounts.$$"
    return 0
}

wcp_release()
{
    [ "$WCP_HAS_LOCK" -eq 1 ] || return 0
    rm -f "$WCP_PS" "$WCP_MOUNTS" "$WCP_LOCK/lease.$$"
    [ "$WCP_OWN_LOCK" -eq 1 ] || return 0
    # A still-running nested stop/down helper keeps the dead owner's claim.
    # A later restore can recover only after every lease process is gone.
    for lease in "$WCP_LOCK"/lease.*; do
        [ -f "$lease" ] || continue
        child=${lease##*.}
        kill -0 "$child" 2>/dev/null && return 0
    done
    [ -r "$WCP_LOCK/owner" ] || return 0
    read wcp_owner < "$WCP_LOCK/owner" || return 0
    [ "$wcp_owner" = "$$" ] || return 0
    rm -f "$WCP_LOCK/owner"
    rmdir "$WCP_LOCK" 2>/dev/null || true
    WCP_HAS_LOCK=0
}

wcp_snapshot()
{
    ps -ef > "$WCP_PS" 2>/dev/null || return 1
    awk '
      NR==1 {if ($1!="UID" || $2!="PID" || $3!="PPID") exit 2; next}
      NF<8 || $2!~/^[0-9]+$/ || $3!~/^[0-9]+$/ {bad=1}
      END {if (bad || NR<2) exit 2}
    ' "$WCP_PS"
}

wcp_process_rows()
{
    # One checked snapshot; callers reject zero/multiple matches as appropriate.
    awk -v a="$1" -v b="${2:-}" -v c="${3:-}" '
      NR>1 && ($8==a || (b!="" && $8==b) || (c!="" && $8==c)) {print $2 " " $3}
    ' "$WCP_PS"
}

wcp_devb_rows()
{
    awk 'NR>1 && ($8=="devb-ram" || $8=="/sbin/devb-ram") {
      found=0; for(i=9;i<=NF;i++) if($i=="name=wcpbtram") found=1
      if(found) print $2 " " $3
    }' "$WCP_PS"
}

wcp_ipod_rows()
{
    awk 'NR>1 && ($8=="mm-ipod" || $8=="/mnt/app/armle/usr/sbin/mm-ipod" ||
                           $8=="/usr/sbin/mm-ipod") {print $2 " " $3}' "$WCP_PS"
}

wcp_owned_ipod_rows()
{
    awk -v cfg="$1" 'NR>1 && $8=="/mnt/app/armle/usr/sbin/mm-ipod" {
      c=0; m=0; for(i=9;i<NF;i++) {
        if($i=="-d" && $(i+1)=="iap2,config="cfg) c=1
        if($i=="-m" && $(i+1)=="/dev/ipod0") m=1
      }
      if(c && m) print $2 " " $3
    }' "$WCP_PS"
}

wcp_no_mutators()
{
    awk 'NR>1 {
      cmd=$8; sub(/^.*\//,"",cmd)
      if(cmd=="cp" || cmd=="mv" || cmd=="mount" || cmd=="umount" ||
         cmd=="mhi2-wcp-iap2-runtime-config")
        for(i=9;i<=NF;i++) if($i ~ /^\/tmp\/mhi2-wcp-/ ||
          $i ~ /^\/ramdisk\/mhi2-wcp-stock/ || $i=="/eso/bin/apps") bad=1
    } END {if(bad) exit 2}' "$WCP_PS"
}

wcp_no_launchers()
{
    awk 'NR>1 {for(i=8;i<=NF;i++)
      if($i ~ /(^|\/)mhi2_wcp_mm_ipod_launch.sh$/) bad=1
    } END {if(bad) exit 2}' "$WCP_PS"
}

wcp_ready_for_pid()
{
    [ -r "$WCP_READY" ] || return 1
    ready_pid=; ready_channel=; ready_registered=; ready_sdp=; ready_endpoint=
    while IFS='=' read key value; do
      case "$key" in
        pid) ready_pid="$value" ;;
        channel) ready_channel="$value" ;;
        registered) ready_registered="$value" ;;
        sdp) ready_sdp="$value" ;;
        endpoint) ready_endpoint="$value" ;;
      esac
    done < "$WCP_READY"
    case "$ready_channel" in ''|*[!0-9]*) return 1 ;; esac
    [ "$ready_pid" = "$1" ] && [ "$ready_registered:$ready_sdp:$ready_endpoint" = 1:1:1 ] &&
    [ "$ready_channel" -ge 1 ] && [ "$ready_channel" -le 30 ]
}

wcp_mount_snapshot()
{
    mount > "$WCP_MOUNTS" 2>/dev/null || return 1
    # Support documented Unix-style QNX listings. A different target format
    # fails before unmount/signalling, and must be captured read-only.
    awk 'NF {if(NF<4 || $2!="on" || $3!~/^\//) bad=1; n++}
         END {if(bad || n==0) exit 2}' "$WCP_MOUNTS"
}

wcp_mount_count()
{
    awk -v dev="$1" -v point="$2" '
      $3==point {
        if($1!=dev) {bad=1; next}
        if(!($4=="type" && $5=="qnx4") && $4!~/^\(qnx4[,)]/) {bad=1; next}
        n++
      }
      END {if(bad || n>1) exit 2; print n+0}
    ' "$WCP_MOUNTS"
}

wcp_detach_owned()
{
    wcp_mount_snapshot || return 1
    count=$(wcp_mount_count "$1" "$2") || return 1
    [ "$count" -eq 1 ] || return 0
    # No forced unmount and no status-based signal fallback.
    umount "$2" || return 1
    wcp_mount_snapshot || return 1
    count=$(wcp_mount_count "$1" "$2") || return 1
    [ "$count" -eq 0 ]
}

wcp_atomic_line()
{
    file="$1"; value="$2"
    printf '%s\n' "$value" > "$file.$$" || return 1
    chmod 0600 "$file.$$" || return 1
    mv "$file.$$" "$file"
}

wcp_load_control()
{
    WCP_PHASE=
    WCP_ACTIVATION=
    WCP_RESTORATION=
    WCP_HOOK_PID=
    WCP_LAUNCHER_PID=
    WCP_BASE_PID=
    [ -r "$WCP_CONTROL" ] || return 1
    while IFS='=' read key value; do
        case "$key" in
          phase) WCP_PHASE="$value" ;;
          activation) WCP_ACTIVATION="$value" ;;
          restoration) WCP_RESTORATION="$value" ;;
          hook_pid) WCP_HOOK_PID="$value" ;;
          launcher_pid) WCP_LAUNCHER_PID="$value" ;;
          base_pid) WCP_BASE_PID="$value" ;;
        esac
    done < "$WCP_CONTROL"
    case "$WCP_ACTIVATION:$WCP_RESTORATION" in 0:0|1:0|1:1) ;; *) return 1 ;; esac
    case "$WCP_HOOK_PID:$WCP_LAUNCHER_PID:$WCP_BASE_PID" in *[!0-9:]*|:*|*::*|*:) return 1 ;; esac
    [ "$WCP_LAUNCHER_PID" -gt 1 ] && [ "$WCP_BASE_PID" -gt 1 ] || return 1
    case "$WCP_PHASE" in prepared|activation-signal-intent|activating|active|restoration-signal-intent|detach-intent|backing-stop-intent|restored) ;; *) return 1 ;; esac
}

wcp_save_control()
{
    WCP_PHASE="$1"
    {
      echo "phase=$WCP_PHASE"
      echo "activation=$WCP_ACTIVATION"
      echo "restoration=$WCP_RESTORATION"
      echo "hook_pid=$WCP_HOOK_PID"
      echo "launcher_pid=$WCP_LAUNCHER_PID"
      echo "base_pid=$WCP_BASE_PID"
    } > "$WCP_CONTROL.$$" || return 1
    chmod 0600 "$WCP_CONTROL.$$" || return 1
    mv "$WCP_CONTROL.$$" "$WCP_CONTROL"
}

wcp_signal_once()
{
    # Caller has checked exact argv/PID ownership in a fresh snapshot.
    wcp_signal_status=0
    slay -f -m pid -s "$2" "$1" >/dev/null 2>&1 || wcp_signal_status=$?
    echo "WCP_SIGNAL_ATTEMPT pid=$1 signal=$2 count_status=$wcp_signal_status delivery=unconfirmed"
}
