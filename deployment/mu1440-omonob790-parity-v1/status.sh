#!/bin/ksh
set -u

# BEGIN_TARGET_ENV -- proven installed MU1440 runtime paths
export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/media/gracenote/bin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin:/mnt/app/armle/usr/sbin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1
# END_TARGET_ENV

SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2

SHA=$ROOT/payload/sha256sum
DST=/mnt/app/root/altscreen-u2
HOOK=/mnt/app/eso/lib/libmibr_carplay111.so
ACTIVE=/mnt/app/root/mibr-omonob790-parity-v1-active
BASE_REMUX_EXPECTED=3f0e730523bd290608dc13e186baa962eeb9c46f117d4d4976be523c0cd94c09

hashf(){
  [ -x "$SHA" ] || return 1
  set -- $("$SHA" "$1" 2>/dev/null)
  [ -n "${1:-}" ] || return 1
  echo "$1"
}

compare(){
  LABEL=$1
  LIVE=$2
  PKG=$3
  if [ ! -r "$LIVE" ]; then
    echo "$LABEL=FAIL_MISSING"
    return
  fi
  LH=$(hashf "$LIVE" 2>/dev/null)
  PH=$(hashf "$PKG" 2>/dev/null)
  echo "${LABEL}_live_sha256=${LH:-HASH_FAILED}"
  echo "${LABEL}_candidate_sha256=${PH:-HASH_FAILED}"
  [ -n "${LH:-}" ] && [ "$LH" = "$PH" ] && echo "$LABEL=PASS_CANDIDATE" || echo "$LABEL=FAIL_HASH"
}

echo "=== MU1440 OMONOB790 PARITY OVERLAY ==="
[ -e "$ACTIVE" ] && { echo "candidate_active=1"; cat "$ACTIVE" 2>/dev/null || true; } || echo "candidate_active=0"

compare gen2 "$DST/bin/libaltscreen111.so" "$ROOT/payload/libaltscreen111.so"
compare hook "$HOOK" "$ROOT/payload/libaltscreen111.so"
compare parity_bridge "$DST/bin/direct-ts-parity" "$ROOT/payload/direct-ts-parity"
compare parity_session "$DST/bin/parity-session" "$ROOT/payload/parity-session"
compare settings_helper "$DST/bin/alt111-settings" "$ROOT/payload/alt111-settings"
compare native_guard /mnt/app/eso/lib/libmibr_isotx2_guard.so "$ROOT/payload/libmibr_isotx2_guard.so"
echo "displaymanager_guard_requires_fresh_boot=1"
echo "base_gate_live_sha256=$(hashf /mnt/app/eso/lib/libmibr_isotx2_gate.so 2>/dev/null)"
echo "base_gate_expected_sha256=05673010a88c25022145ffb4e75d3715eaf686f4127ac188e91a52f512b9d957"
echo "base_libairplay_live_sha256=$(hashf /mnt/app/eso/lib/libairplay.so 2>/dev/null)"
echo "smartphone_integrator_live_sha256=$(hashf /mnt/system/etc/eso/production/smartphone_integrator.json 2>/dev/null)"

if [ -r "$DST/bin/direct-ts-remux" ]; then
  RH=$(hashf "$DST/bin/direct-ts-remux" 2>/dev/null)
  echo "base_remux_live_sha256=${RH:-HASH_FAILED}"
  [ "$RH" = "$BASE_REMUX_EXPECTED" ] && echo "base_remux_state=PASS_UNCHANGED" || echo "base_remux_state=FAIL_CHANGED"
else
  echo "base_remux_state=FAIL_MISSING"
fi

echo
echo "=== LEGACY AUTO DIRECT ==="
if [ -r /tmp/mibr-carplay-autodirect ]; then
  echo "autodirect_source=temp"
  echo "autodirect=$(cat /tmp/mibr-carplay-autodirect 2>/dev/null)"
elif [ -r /mnt/app/root/mibr-carplay-autodirect ]; then
  echo "autodirect_source=persistent"
  echo "autodirect=$(cat /mnt/app/root/mibr-carplay-autodirect 2>/dev/null)"
else
  echo "autodirect_source=default"
  echo "autodirect=1"
fi

if [ -x "$DST/scripts/omonob790_status.sh" ]; then
  echo
  ksh "$DST/scripts/omonob790_status.sh"
fi
