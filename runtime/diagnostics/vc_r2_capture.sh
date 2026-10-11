#!/bin/ksh
# Two independent receive-only loggers, one shared QNX CLOCK_MONOTONIC domain.
set -u
ROOT=$(pwd) || exit 2
case "$ROOT" in /net/mmx/fs/sda0/*|/net/mmx.mibhigh.net/fs/sda0/*) ;; *) echo 'CAPTURE=FAIL not_in_sd_directory'; exit 2 ;; esac
[ -x ./mibr-dsi-rx ] && [ -x ./mibr-keypanel-native ] || { echo 'CAPTURE=FAIL missing_QNX_binary'; exit 2; }
[ ! -e ./mibr-keypanel-native-current ] || { echo 'CAPTURE=FAIL existing_keypanel_pointer_inspect_manually'; exit 2; }
DURATION=${1:-240}
case "$DURATION" in ''|*[!0-9]*) echo 'CAPTURE=FAIL duration_invalid'; exit 2;; esac
[ "$DURATION" -ge 30 ] && [ "$DURATION" -le 1800 ] || { echo 'CAPTURE=FAIL duration_30_to_1800'; exit 2; }
[ -w "$ROOT" ] || { echo 'CAPTURE=FAIL sd_not_writable'; exit 2; }
RUN="$ROOT/vc-r2-capture-$$"
mkdir "$RUN" || { echo 'CAPTURE=FAIL cannot_create_run_dir'; exit 2; }
echo "RUN_DIR=$RUN"
echo 'Set notes BEFORE each action using shell 2: /bin/ksh ./keypanel_note_native.sh'
echo 'Keep the original keypanel pointer untouched. STOP if HMI becomes unstable.'
pidin ar > "$RUN/pidin-before.txt" 2>&1 || true
[ -x /bin/sloginfo ] && /bin/sloginfo > "$RUN/slog-before.txt" 2>&1 || true
./mibr-dsi-rx --capture --out "$RUN" --seconds "$DURATION" --port 1800 > "$RUN/dsi-console.log" 2>&1 &
D=$!
/bin/ksh ./keypanel_start_native.sh "$DURATION" > "$RUN/keypanel-console.log" 2>&1 &
K=$!
echo "DSI_PID=$D KEYPANEL_WRAPPER_PID=$K"
echo 'Waiting for bounded capture; note console from second SSH session; do not restart HMI while driving.'
wait "$D"; DR=$?
wait "$K"; KR=$?
[ -x /bin/sloginfo ] && /bin/sloginfo > "$RUN/slog-after.txt" 2>&1 || true
echo "dsi_exit=$DR" > "$RUN/capture-exit.txt"
echo "keypanel_exit=$KR" >> "$RUN/capture-exit.txt"
if [ -r "$RUN/dsi-report.txt" ]; then
  BYTES=$(awk -F= '$1=="raw_bytes"{print $2}' "$RUN/dsi-report.txt")
  echo "dsi_raw_bytes=${BYTES:-UNKNOWN}" >> "$RUN/capture-exit.txt"
  [ "${BYTES:-0}" -gt 0 ] 2>/dev/null || echo 'DSI_DATA_GATE=INCONCLUSIVE_NO_BYTES (not proof of absent DSI traffic)' >> "$RUN/capture-exit.txt"
else echo 'DSI_DATA_GATE=REPORT_MISSING' >> "$RUN/capture-exit.txt"; fi
cat "$RUN/dsi-console.log" "$RUN/keypanel-console.log" "$RUN/capture-exit.txt"
echo "RUN_DIR=$RUN"
[ "$DR" = 0 ] && [ "$KR" = 0 ] || exit 3
