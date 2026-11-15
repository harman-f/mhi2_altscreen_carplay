#!/bin/sh
# Select the firmware profile from the SHA-256 of /ifs/lsd.jxe (owner decision E3).
# The train string is only a plausibility cross-check, never a second selector.
# Read-only: writes nothing but the result line on stdout. POSIX sh / QNX ksh.
#
# Usage: select-profile.ksh PROFILES_LIST [--jxe PATH] [--train VALUE]
# Output: PROFILE=<id> on stdout, exit 0 only if exactly one line matches,
#         install_enabled=1 and the train cross-check passes.
# Exit:   0 ok, 2 unreadable/usage, 3 train mismatch, 4 unknown digest,
#         5 ambiguous, 6 install disabled for the matched profile.

SHA=${MIBR_SHA256:-}
if [ -z "$SHA" ]; then
  # The unit has no sha256sum of its own; the package ships one (like
  # deployment/mu1440/install.sh: $PAYLOAD/sha256sum). Prefer the copy next
  # to this script, then PATH (host tests).
  for C in "${0%/*}/sha256sum" "${0%/*}/bin/sha256sum" "${0%/*}/../common/bin/sha256sum"; do
    if [ -x "$C" ]; then SHA=$C; break; fi
  done
fi

hashf(){
  set -- $("$SHA" "$1" 2>/dev/null)
  [ -n "${1:-}" ] || return 1
  echo "$1"
}

msg(){ echo "SELECT_PROFILE=$*" >&2; }

LIST=
JXE=/ifs/lsd.jxe
TRAIN=
HAVE_TRAIN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --jxe) [ $# -ge 2 ] || { msg "FAIL usage"; exit 2; }; JXE=$2; shift 2 ;;
    --train) [ $# -ge 2 ] || { msg "FAIL usage"; exit 2; }; TRAIN=$2; HAVE_TRAIN=1; shift 2 ;;
    -*) msg "FAIL usage"; exit 2 ;;
    *) [ -z "$LIST" ] || { msg "FAIL usage"; exit 2; }; LIST=$1; shift ;;
  esac
done
[ -n "$LIST" ] || { msg "FAIL usage"; exit 2; }
[ -r "$LIST" ] || { msg "FAIL unreadable_list"; exit 2; }
[ -r "$JXE" ] || { msg "FAIL unreadable_jxe"; exit 2; }
[ -n "$SHA" ] || { msg "FAIL missing_sha256_helper"; exit 2; }
H=$(hashf "$JXE") || { msg "FAIL hash_failed"; exit 2; }
case "$H" in
  *[!0123456789abcdef]*) msg "FAIL hash_format"; exit 2 ;;
esac
[ ${#H} -eq 64 ] || { msg "FAIL hash_format"; exit 2; }

N=0
MID=
MFW=
MEN=
BAD=0
while read -r D PID FW EN EXTRA || [ -n "$D" ]; do
  case "$D" in ''|'#'*) continue ;; esac
  if [ -z "$PID" ] || [ -z "$FW" ] || [ -z "$EN" ] || [ -n "$EXTRA" ]; then BAD=1; continue; fi
  case "$EN" in 0|1) ;; *) BAD=1; continue ;; esac
  if [ "$D" = "$H" ]; then
    N=$((N + 1))
    MID=$PID; MFW=$FW; MEN=$EN
  fi
done < "$LIST"

[ "$BAD" -eq 0 ] || { msg "FAIL malformed_list"; exit 2; }
[ "$N" -ne 0 ] || { msg "UNKNOWN"; exit 4; }
[ "$N" -eq 1 ] || { msg "AMBIGUOUS"; exit 5; }
[ "$MEN" = 1 ] || { msg "DISABLED profile=$MID"; exit 6; }
if [ "$MFW" != "-" ]; then
  if [ "$HAVE_TRAIN" -ne 1 ] || [ -z "$TRAIN" ] || [ "$TRAIN" != "$MFW" ]; then
    msg "TRAIN_MISMATCH profile=$MID"
    exit 3
  fi
fi
echo "PROFILE=$MID"
exit 0
