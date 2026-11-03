#!/bin/ksh
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init_durable || { echo "FAIL runtime/log bootstrap"; exit 3; }

STATE=/tmp/mibr-carplay111.state
LOGFILE=/tmp/altscreen111.log

echo "=== MU1440 CarPlay111 boot preload verification ==="
echo "hook=$CARPLAY_HOOK"
echo "config=$TARGET"
[ -e /mnt/app/root/mibr-carplay111-viewareas.enabled ] &&
  echo "viewarea_fallback=ENABLED_THIS_BOOT" ||
  echo "viewarea_fallback=DISABLED_THIS_BOOT"

[ -r "$CARPLAY_HOOK" ] || {
  echo "VERIFY_CARPLAY111_BOOT=FAIL_HOOK_MISSING"
  exit 20
}

grep -q "LD_PRELOAD=$CARPLAY_HOOK" "$TARGET" 2>/dev/null || {
  echo "VERIFY_CARPLAY111_BOOT=FAIL_CONFIG_NOT_PATCHED"
  exit 21
}

SID=$(pidin ar 2>/dev/null | awk '/[s]martphone_integrator/ {print $1; exit}')
DIO=$(pidin ar 2>/dev/null | awk '/[d]io_manager/ {print $1; exit}')
echo "smartphone_integrator_pid=${SID:-NONE}"
echo "dio_manager_pid=${DIO:-NONE}"

[ -n "${SID:-}" ] || {
  echo "VERIFY_CARPLAY111_BOOT=FAIL_NO_SMARTPHONE_INTEGRATOR"
  exit 22
}
[ -n "${DIO:-}" ] || {
  echo "CARPLAY111_PERSISTENT_CONFIG=READY"
  echo "VERIFY_CARPLAY111_BOOT=WAITING_FOR_DIO_MANAGER"
  echo "dio_manager is the on-demand CarPlay child and may be absent until an iPhone is connected."
  echo "Connect CarPlay, then rerun this verifier before passive stream111 capture."
  exit 0
}

echo
echo "=== DIO PRELOAD LIBRARY (INFORMATIONAL MAP CHECK) ==="
# Exact-unit vehicle evidence shows QNX pidin mapinfo can omit an active
# LD_PRELOAD library name even while its constructor/wrappers execute. Do not
# use mapinfo as a hard load gate.
MAPTMP=/tmp/mibr-carplay111-map.$$
pidin -p "$DIO" mapinfo > "$MAPTMP" 2>/dev/null ||
  pidin -p "$DIO" memory > "$MAPTMP" 2>/dev/null || true
if grep -E 'libmibr_carplay111|libaltscreen111' "$MAPTMP"; then
  echo "CARPLAY111_MAPINFO=VISIBLE"
else
  echo "CARPLAY111_MAPINFO=NOT_VISIBLE"
fi
rm -f "$MAPTMP" 2>/dev/null || true

echo
echo "=== DIO ENV ==="
ENVTMP=/tmp/mibr-carplay111-env.$$
pidin -p "$DIO" environment > "$ENVTMP" 2>/dev/null || true
grep -E 'LD_PRELOAD|ALTSCREEN111_|IPL_CONFIG_DIR_DIO_MANAGER' "$ENVTMP" || true
if grep -q "LD_PRELOAD=$CARPLAY_HOOK" "$ENVTMP"; then
  echo "CARPLAY111_PRELOAD_ENV=YES"
else
  echo "VERIFY_CARPLAY111_BOOT=FAIL_PRELOAD_ENV_MISSING"
  rm -f "$ENVTMP" 2>/dev/null || true
  exit 24
fi
rm -f "$ENVTMP" 2>/dev/null || true

echo
echo "=== OBSERVER STATE ==="
if [ -r "$STATE" ]; then
  echo "state=$(cat "$STATE" 2>/dev/null)"
else
  echo "VERIFY_CARPLAY111_BOOT=FAIL_STATE_MISSING"
  [ -r "$LOGFILE" ] && tail -120 "$LOGFILE" 2>/dev/null || true
  exit 25
fi

echo
echo "=== PORTS ==="
netstat -an 2>/dev/null | grep -E '(:19820|:6031)' || true

echo
echo "=== HOOK LOG ==="
[ -r "$LOGFILE" ] && tail -120 "$LOGFILE" 2>/dev/null || echo "no hook log"

CUR=$(cat "$STATE" 2>/dev/null)
case "$CUR" in
  ready|setup|listening|connected|video_config|streaming|idle|disconnected)
    ;;
  *)
    echo "VERIFY_CARPLAY111_BOOT=FAIL_STATE_$CUR"
    exit 26
    ;;
esac

echo
echo "VERIFY_CARPLAY111_BOOT=PASS"
echo "This proves boot loading only. Stream111 video still requires a separate passive capture/observer PASS."
exit 0
