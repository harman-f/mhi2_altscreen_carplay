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

echo "=== MU1440 framing-v1 candidate ==="
[ -e "$ACTIVE" ] && { echo "candidate_active=1"; cat "$ACTIVE" 2>/dev/null; } || echo "candidate_active=0"

if [ -x "$SHA" ]; then
  for SPEC in     "gen2:$DST/bin/libaltscreen111.so:$ROOT/payload/libaltscreen111.so"     "hook:$HOOK:$ROOT/payload/libaltscreen111.so"     "remux:$DST/bin/direct-ts-remux:$ROOT/payload/direct-ts-remux"; do
      N=${SPEC%%:*}; REST=${SPEC#*:}; LIVE=${REST%%:*}; PKG=${REST#*:}
      LH=$(hashf "$LIVE" 2>/dev/null); PH=$(hashf "$PKG" 2>/dev/null)
      echo "${N}_live_sha256=${LH:-MISSING}"
      echo "${N}_candidate_sha256=${PH:-MISSING}"
      [ -n "$LH" ] && [ "$LH" = "$PH" ] && echo "${N}_state=PASS_CANDIDATE" || echo "${N}_state=DIFFERENT"
  done
fi

echo
if [ -x "$DST/scripts/direct_source_mode.sh" ]; then
  "$DST/scripts/direct_source_mode.sh" status
else
  echo "direct_source_mode=missing"
fi

echo
if [ -x "$DST/scripts/direct_fps.sh" ]; then
  "$DST/scripts/direct_fps.sh" status
fi

echo
if [ -x "$DST/scripts/gen2_safearea.sh" ]; then
  "$DST/scripts/gen2_safearea.sh" status
fi

echo
if [ -x "$DST/scripts/gen2_keyframes.sh" ]; then
  "$DST/scripts/gen2_keyframes.sh" status
else
  echo "gen2_keyframes=missing"
fi

echo
if [ -x "$DST/scripts/gen2_sourceversion.sh" ]; then
  "$DST/scripts/gen2_sourceversion.sh" status
else
  echo "gen2_sourceversion=missing"
fi

echo
if [ -x "$DST/scripts/viewarea_mode.sh" ]; then
  "$DST/scripts/viewarea_mode.sh" status
fi

echo
if [ -x "$DST/scripts/gen2_nav_config.sh" ]; then
  "$DST/scripts/gen2_nav_config.sh" status
fi

echo
if [ -r /tmp/mibr-alt111-gen2.status ]; then
  grep '^source_version_' /tmp/mibr-alt111-gen2.status 2>/dev/null || true
fi

echo
if [ -x "$DST/scripts/direct_ts_auto_status.sh" ]; then
  "$DST/scripts/direct_ts_auto_status.sh"
fi
