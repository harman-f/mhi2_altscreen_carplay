#!/bin/ksh
# Low-overhead 150-second LIVE CarPlay timing capture, exclusive normal session.
set -u
export PATH=/proc/boot:/bin:/usr/bin:/sbin:/usr/sbin:/mnt/app/armle/bin:/mnt/app/armle/usr/bin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1
SD=/net/mmx/fs/sda0
PKG=$SD/esd/carplay-test/omonob-clock-test/clockdiag-v1
LOGROOT=$SD/esd/carplay-test/logs/parity-drive
BASE=/mnt/app/root/altscreen-u2
BRIDGE=$BASE/bin/direct-ts-parity
OWNER=$BASE/bin/parity-session
SHA=$BASE/bin/sha256sum
MODE=${1:-status}
RUN=
MARK=
SAMPLER=
RW=0
fail(){ echo "CLOCKDIAG_LIVE=FAIL reason=$1"; exit 1; }
hashfile(){ "$SHA" "$1" 2>/dev/null | awk '{print $1}'; }
pair(){
  [ -x "$SHA" ] || fail sha_helper
  [ -r "$PKG/PAIR_SHA256SUMS.txt" ] || fail manifest_missing
  B=$(awk '$2=="direct-ts-parity"{print $1}' "$PKG/PAIR_SHA256SUMS.txt")
  O=$(awk '$2=="parity-session"{print $1}' "$PKG/PAIR_SHA256SUMS.txt")
  [ -n "$B" ] && [ -n "$O" ] || fail manifest_invalid
  [ "$(hashfile "$BRIDGE")" = "$B" ] || fail bridge_not_diagd_pair
  [ "$(hashfile "$OWNER")" = "$O" ] || fail owner_not_diag_pair
}
snapshot(){
  { echo "===== sample=$2 ====="
    echo '--- parity ---'
    [ -r /tmp/mibr-parity-ts.status ] && cat /tmp/mibr-parity-ts.status
    echo '--- owner ---'
    [ -r /tmp/mibr-parity-session.state ] && cat /tmp/mibr-parity-session.state
    echo '--- gate ---'
    [ -r /tmp/mibr-alt111-native-gate.status ] && cat /tmp/mibr-alt111-native-gate.status
  } >> "$1/status-snapshots.log" 2>/dev/null
}
case "$MODE" in
  --sample)
    [ "$#" -eq 2 ] || exit 2
    N=0
    while [ -e "$2/.recording" ]; do
      N=$((N+1));snapshot "$2" "$N";sleep 3
    done
    exit 0 ;;
  status)
    [ -r /tmp/mibr-parity-session.state ] && cat /tmp/mibr-parity-session.state
    [ -r /tmp/mibr-parity-ts.status ] && grep -E '^(state|diag_[^=]*|input_records|output_aus_completed|write_errors|pts_pcr_lead_ms)=' /tmp/mibr-parity-ts.status
    exit 0 ;;
  stop) exec "$OWNER" --stop ;;
  preflight|start) : ;;
  *) echo "usage: $0 preflight|start|status|stop";exit 2 ;;
esac
pair
[ -f "$BASE/scripts/parity_session.sh" ] || fail base_session_script_missing
[ "$(cat /tmp/mibr-carplay111.state 2>/dev/null)" = streaming ] || fail source_not_streaming
[ -r /tmp/mibr-carplay111.heartbeat ] || fail heartbeat_missing
[ "$(cat /mnt/app/root/mibr-parity-drive.enabled 2>/dev/null)" != 1 ] || fail drive_supervisor_enabled
[ ! -e /tmp/mibr-parity-session.lock ] || fail owner_lock_present
[ ! -e /tmp/mibr-parity-session.pid ] || fail owner_present
[ ! -e /tmp/mibr-parity-session-bridge.pid ] || fail bridge_present
[ ! -e /tmp/mibr-parity-session-watchdog.pid ] || fail watchdog_present
case "$(cat /tmp/mibr-alt111-native-gate.status 2>/dev/null)" in 'M1GATE1 0 '*) : ;; *) fail gate_not_stock ;; esac
echo CLOCKDIAG_LIVE=PREFLIGHT_PASS
[ "$MODE" = start ] || exit 0
cleanup(){
  RC=$?
  trap - 0 1 2 15
  [ -z "$MARK" ] || rm -f "$MARK" 2>/dev/null || true
  [ -z "$SAMPLER" ] || wait "$SAMPLER" 2>/dev/null || true
  if [ "$RW" -eq 1 ]; then
    sync 2>/dev/null || true
    if [ ! -e /tmp/mibr-parity-session.lock ]; then
      mount -ur "$SD" 2>/dev/null || echo CLOCKDIAG_LIVE=WARNING_SD_RW
    else
      echo CLOCKDIAG_LIVE=WARNING_OWNER_LOCK_SD_RW
    fi
  fi
  exit "$RC"
}
trap cleanup 0
trap '"$OWNER" --stop >/dev/null 2>&1 || true;exit 130' 1 2 15
mount -uw "$SD" 2>/dev/null || fail sd_rw
RW=1
mkdir -p "$LOGROOT" || fail log_root
STAMP=$(/net/rcc/usr/bin/date +%Y%m%d-%H%M%S 2>/dev/null)
[ -n "$STAMP" ] || STAMP=mono-$$
RUN=$LOGROOT/clockdiag-live-$STAMP-$$
mkdir -p "$RUN" || fail log_dir
: > "$RUN/session.log" || fail session_log
: > "$RUN/status-snapshots.log" || fail snapshots_log
MARK=$RUN/.recording
: > "$MARK" || fail marker
/bin/ksh "$0" --sample "$RUN" &
SAMPLER=$!
echo "CLOCKDIAG_LIVE=STARTED log=$RUN"
echo CLOCKDIAG_LIVE=RUNNING_foreground_150_seconds
/bin/ksh "$BASE/scripts/parity_session.sh" 150 >> "$RUN/session.log" 2>&1
RC=$?
rm -f "$MARK";MARK=
wait "$SAMPLER" 2>/dev/null || true;SAMPLER=
[ -r /tmp/mibr-parity-ts.status ] && cp /tmp/mibr-parity-ts.status "$RUN/parity-final.status"
[ -r /tmp/mibr-alt111-native-gate.status ] && cp /tmp/mibr-alt111-native-gate.status "$RUN/gate-final.status"
{ echo "owner_rc=$RC";echo "owner_state=$(cat /tmp/mibr-parity-session.state 2>/dev/null)"; } > "$RUN/summary.txt"
echo "CLOCKDIAG_LIVE=END owner_rc=$RC log=$RUN"
exit "$RC"
