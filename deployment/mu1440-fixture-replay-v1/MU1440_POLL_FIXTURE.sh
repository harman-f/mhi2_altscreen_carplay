#!/bin/ksh
# Fixed 120-second M1AU fixture; never boot-autostarts; same owner, gate and writer.
set -u
export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin:/mnt/app/armle/usr/sbin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1
BASE=/mnt/app/root/altscreen-u2/bin
CARD=/net/mmx/fs/sda0
PKG=$CARD/esd/carplay-test/omonob-clock-test/pollwait-v1
FILE=$CARD/esd/carplay-test/fixtures/mu1440-motion-v1/mu1440_motion_1010x376_30fps_gop20.m1au
INPUT=fixture:$FILE
LOGROOT=$CARD/esd/carplay-test/logs/parity-drive
SHA=$BASE/sha256sum
EXPECTED_FIXTURE=e853dbf2d690e534f9020fd3c206550ca44177408d3d2c5d20f2f863645724b9
RUNNER=$BASE/parity-session
BRIDGE=$BASE/direct-ts-parity
MODE=${1:-status}
RW=0
RUN=
MARK=
SAMPLER=
hashfile(){ "$SHA" "$1" 2>/dev/null | awk '{print $1}'; }
fail(){ echo "M1AU_REPLAY=FAIL reason=$1"; exit 1; }
stock(){
  [ ! -e /tmp/mibr-parity-session.lock ] || fail session_lock_exists
  [ ! -e /tmp/mibr-parity-session-bridge.pid ] || fail bridge_pid_present
  [ ! -e /tmp/mibr-parity-session-watchdog.pid ] || fail watchdog_pid_present
  [ ! -e /tmp/mibr-parity-session.pid ] || fail owner_pid_present
  [ ! -e /tmp/mibr-parity-drive-supervisor.pid ] || fail supervisor_pid_present
  if [ -r /mnt/app/root/mibr-parity-drive.enabled ]; then
    [ "$(cat /mnt/app/root/mibr-parity-drive.enabled 2>/dev/null)" != 1 ] || fail persistent_supervisor_enabled
  fi
  [ -r /tmp/mibr-alt111-native-gate.status ] || fail gate_status_missing
  G=$(cat /tmp/mibr-alt111-native-gate.status 2>/dev/null)
  case "$G" in 'M1GATE1 0 '*) : ;; *) fail native_gate_not_stock ;; esac
  [ "$(cat /tmp/mibr-carplay111.state 2>/dev/null)" != streaming ] || fail iphone_still_streaming
}
pair(){
  [ -x "$SHA" ] || fail sha_helper_missing
  [ -r "$PKG/PAIR_SHA256SUMS.txt" ] || fail pair_manifest_missing
  B=$(awk '$2=="direct-ts-parity"{print $1}' "$PKG/PAIR_SHA256SUMS.txt" 2>/dev/null)
  O=$(awk '$2=="parity-session"{print $1}' "$PKG/PAIR_SHA256SUMS.txt" 2>/dev/null)
  [ -n "$B" ] && [ -n "$O" ] || fail pair_manifest_malformed
  [ "$(hashfile "$BRIDGE")" = "$B" ] || fail bridge_not_fixture_build
  [ "$(hashfile "$RUNNER")" = "$O" ] || fail owner_not_fixture_build
}
fixture(){
  [ -r "$FILE" ] || fail fixture_missing
  [ "$(hashfile "$FILE")" = "$EXPECTED_FIXTURE" ] || fail fixture_hash_mismatch
}
snapshot(){
  { echo "===== sample=$2 ====="; echo '--- parity ---'
    [ -r /tmp/mibr-parity-ts.status ] && cat /tmp/mibr-parity-ts.status
    echo '--- owner ---'; [ -r /tmp/mibr-parity-session.state ] && cat /tmp/mibr-parity-session.state
    echo '--- gate ---'; [ -r /tmp/mibr-alt111-native-gate.status ] && cat /tmp/mibr-alt111-native-gate.status
  } >> "$1/status-snapshots.log" 2>/dev/null
}
case "$MODE" in
  --sample)
    [ "$#" -eq 2 ] || exit 2
    N=0
    while [ -e "$2/.recording" ]; do
      N=$((N+1)); snapshot "$2" "$N"; sleep 3
    done
    exit 0 ;;
  status)
    echo '=== REPLAY ==='; [ -r "$PKG/last-run.txt" ] && cat "$PKG/last-run.txt"
    echo '=== OWNER ==='; [ -r /tmp/mibr-parity-session.state ] && cat /tmp/mibr-parity-session.state
    echo '=== GATE ==='; [ -r /tmp/mibr-alt111-native-gate.status ] && cat /tmp/mibr-alt111-native-gate.status
    echo '=== WRITER ==='; [ -r /tmp/mibr-parity-ts.status ] && grep -E '^(state|input_records|input_idrs|output_aus_completed|blocks_written|write_errors|write_eagain|writer_eagain_sleep_us_total|transport_pcr90k|pts_rebases|last_emitted_pts90k)=' /tmp/mibr-parity-ts.status
    exit 0 ;;
  stop) exec "$RUNNER" --stop ;;
  preflight|start) : ;;
  *) echo "usage: $0 [preflight|start|status|stop]"; exit 2 ;;
esac
pair
fixture
stock
"$BRIDGE" --self-test >/dev/null 2>&1 || fail bridge_self_test
"$RUNNER" --self-test >/dev/null 2>&1 || fail owner_self_test
echo 'M1AU_REPLAY=PREFLIGHT_PASS frames=3600 fps=30 duration=120s'
[ "$MODE" = start ] || exit 0
cleanup(){
  RC=$?
  trap - 0 1 2 15
  [ -z "$MARK" ] || rm -f "$MARK" 2>/dev/null || true
  [ -z "$SAMPLER" ] || wait "$SAMPLER" 2>/dev/null || true
  if [ "$RW" -eq 1 ]; then
    sync 2>/dev/null || true
    if [ ! -e /tmp/mibr-parity-session.lock ]; then
      mount -ur "$CARD" 2>/dev/null || echo 'M1AU_REPLAY=WARNING_SD_MOUNT_RO_FAILED'
    else
      echo 'M1AU_REPLAY=WARNING_OWNER_ACTIVE_SD_LEFT_RW'
    fi
  fi
  exit "$RC"
}
trap cleanup 0
trap '"$RUNNER" --stop >/dev/null 2>&1 || true; exit 130' 1 2 15
mount -uw "$CARD" 2>/dev/null || fail sd_mount_rw
RW=1
mkdir -p "$LOGROOT" 2>/dev/null || fail logroot
STAMP=$(/net/rcc/usr/bin/date +%Y%m%d-%H%M%S 2>/dev/null)
[ -n "$STAMP" ] || STAMP=mono-$$
RUN=$LOGROOT/pollwait-fixture-$STAMP-$$
mkdir -p "$RUN" || fail logdir
: > "$RUN/.write-test" 2>/dev/null || fail sd_write_test
rm -f "$RUN/.write-test"
echo "path=$RUN" > "$PKG/last-run.txt" || fail last_run_write
: > "$RUN/session.log" || fail session_log
: > "$RUN/status-snapshots.log" || fail snapshot_log
MARK=$RUN/.recording
: > "$MARK" || fail recording_marker
/bin/ksh "$0" --sample "$RUN" &
SAMPLER=$!
echo "M1AU_REPLAY=STARTED log=$RUN"
echo 'M1AU_REPLAY=FOREGROUND approx_120sec; stop_from_second_ssh_if_needed'
"$RUNNER" --fixture "$BRIDGE" "$INPUT" /dev/mlb/isoTX2 150 >> "$RUN/session.log" 2>&1
OWNER_RC=$?
rm -f "$MARK"; MARK=
wait "$SAMPLER" 2>/dev/null || true; SAMPLER=
[ -r /tmp/mibr-parity-ts.status ] && cp /tmp/mibr-parity-ts.status "$RUN/parity-final.status"
[ -r /tmp/mibr-alt111-native-gate.status ] && cp /tmp/mibr-alt111-native-gate.status "$RUN/gate-final.status"
{ echo "owner_rc=$OWNER_RC"; echo "owner_state=$(cat /tmp/mibr-parity-session.state 2>/dev/null)"; echo 'frames_expected=3600'; } > "$RUN/summary.txt"
echo "M1AU_REPLAY=END owner_rc=$OWNER_RC log=$RUN"
case "$OWNER_RC" in
  0|130) stock; echo 'M1AU_REPLAY=STOCK_CONFIRMED'; exit 0 ;;
  *) echo "M1AU_REPLAY=FAILED owner_rc=$OWNER_RC verify_stock_before_next_test"; exit "$OWNER_RC" ;;
esac
