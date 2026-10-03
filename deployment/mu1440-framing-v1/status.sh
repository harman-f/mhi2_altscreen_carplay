#!/bin/ksh
set -u
SELF=$0
case "$SELF" in */*) ROOT=${SELF%/*} ;; *) ROOT=. ;; esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2
DST=/mnt/app/root/altscreen-u2
HOOK=/mnt/app/eso/lib/libmibr_carplay111.so
ACTIVE=/mnt/app/root/mibr-framing-v1-active
SHA=$ROOT/payload/sha256sum

hashf(){
  set -- $("$SHA" "$1" 2>/dev/null)
  [ -n "${1:-}" ] || return 1
  echo "$1"
}

echo "=== MU1440 Classic Type-111 candidate ==="
[ -e "$ACTIVE" ] && { echo "candidate_active=1"; cat "$ACTIVE" 2>/dev/null; } || echo "candidate_active=0"

if [ -x "$SHA" ]; then
  for SPEC in     "gen2:$DST/bin/libaltscreen111.so:$ROOT/payload/libaltscreen111.so"     "hook:$HOOK:$ROOT/payload/libaltscreen111.so"     "remux:$DST/bin/direct-ts-remux:$ROOT/payload/direct-ts-remux"
  do
    N=${SPEC%%:*}; REST=${SPEC#*:}; LIVE=${REST%%:*}; PKG=${REST#*:}
    LH=$(hashf "$LIVE" 2>/dev/null); PH=$(hashf "$PKG" 2>/dev/null)
    echo "${N}_live_sha256=${LH:-MISSING}"
    echo "${N}_candidate_sha256=${PH:-MISSING}"
    [ -n "$LH" ] && [ "$LH" = "$PH" ] && echo "${N}_state=PASS_CANDIDATE" || echo "${N}_state=DIFFERENT"
  done
fi

echo
echo "=== CONFIG CONTRACT ==="
echo "precedence=/tmp_then_/mnt/app/root_then_default"

for H in   gen2_enabled.sh   direct_fps.sh   direct_source_mode.sh   gen2_video.sh   gen2_keyframes.sh   gen2_sourceversion.sh   gen2_url.sh   gen2_ui_urls.sh   gen2_nav_config.sh   gen2_display.sh   gen2_viewareas.sh
do
  echo
  if [ -x "$DST/scripts/$H" ]; then
    "$DST/scripts/$H" status 2>/dev/null || echo "$H=STATUS_FAILED"
  else
    echo "$H=MISSING"
  fi
done

echo
echo "=== GEN2 CORE ==="
if [ -r /tmp/mibr-alt111-gen2.status ]; then
  cat /tmp/mibr-alt111-gen2.status
else
  echo "gen2_core_status=NOT_AVAILABLE"
fi

echo
echo "=== SOURCE TIMING ==="
if [ -r /tmp/mibr-alt111-source-timing.status ]; then
  cat /tmp/mibr-alt111-source-timing.status
else
  echo "source_timing_status=NOT_AVAILABLE"
fi
echo "source_timestamp_policy=raw_8_bytes_preserved_in_m1au_not_used_for_pts_pcr"
echo "pts_pcr=CFR_UNCHANGED"

echo
echo "=== AUTO-DIRECT / REMUX / MOST ==="
if [ -x "$DST/scripts/direct_ts_auto_status.sh" ]; then
  "$DST/scripts/direct_ts_auto_status.sh"
else
  echo "direct_ts_auto_status=MISSING"
fi
