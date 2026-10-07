#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Shared SD-root logging/evidence helpers for the MU1440 developer deployment.
# Keep this file QNX/ksh friendly: no GNU-only shell features are required.

mibr_stamp(){
  if [ -x /net/rcc/usr/bin/date ]; then
    /net/rcc/usr/bin/date +%Y%m%d-%H%M%S 2>/dev/null && return 0
  fi
  echo "run-$$"
}

mibr_media_rw(){
  P=$1
  case "$P" in
    /net/mmx/fs/*)
      mount -uw "$P" 2>/dev/null || return 1
      ;;
  esac
  T="$P/.mibr-altscreen-session-write-test.$$"
  touch "$T" 2>/dev/null || return 1
  [ -f "$T" ] || return 1
  rm -f "$T" 2>/dev/null || return 1
  return 0
}

mibr_hash_file(){
  F=$1
  [ -r "$F" ] || return 1
  set -- $("$MIBR_SESSION_SHA" "$F" 2>/dev/null)
  [ -n "${1:-}" ] || return 1
  echo "$1"
}

mibr_hex_ascii(){
  awk '
    function hv(c, p) {
      p=index("0123456789abcdef",tolower(c))
      return p ? p-1 : -1
    }
    function byte(s, a,b) {
      a=hv(substr(s,1,1)); b=hv(substr(s,2,1))
      if (a<0 || b<0) return -1
      return a*16+b
    }
    {
      line=$0
      if (line !~ /^0x[0-9A-Fa-f]+/) next
      sub(/^0x[0-9A-Fa-f]+[^0-9A-Fa-f]+/,"",line)
      gsub(/[^0-9A-Fa-f]/,"",line)
      for (i=1; i+1<=length(line); i+=2) {
        n=byte(substr(line,i,2))
        if (n>=32 && n<=126) out=out sprintf("%c",n)
      }
    }
    END {
      gsub(/[^A-Za-z0-9_-]/,"",out)
      if (length(out)) print out
    }'
}

mibr_e2p_ascii(){
  ADDR=$1
  LEN=$2
  on -f rcc /net/rcc/usr/apps/modifyE2P r "$ADDR" "$LEN" 2>/dev/null | mibr_hex_ascii
}

mibr_prepare_session(){
  MIBR_SESSION_ACTION=$1
  MIBR_SESSION_ROOT=$2
  MIBR_SESSION_TEE=$3
  MIBR_SESSION_SHA=$4

  [ -x "$MIBR_SESSION_TEE" ] || return 2
  [ -x "$MIBR_SESSION_SHA" ] || return 3
  mibr_media_rw "$MIBR_SESSION_ROOT" || return 4

  MIBR_SESSION_STAMP=$(mibr_stamp)
  MIBR_SESSION_DIR="$MIBR_SESSION_ROOT/mhi2-altscreen-logs/$MIBR_SESSION_STAMP-$MIBR_SESSION_ACTION-$$"
  MIBR_LOG_FILE="$MIBR_SESSION_DIR/session.log"
  MIBR_ARCHIVE_DIR="$MIBR_SESSION_DIR/archive"

  mkdir -p "$MIBR_ARCHIVE_DIR" 2>/dev/null || return 5
  touch "$MIBR_LOG_FILE" 2>/dev/null || return 6

  export MIBR_SESSION_ACTION MIBR_SESSION_ROOT MIBR_SESSION_TEE MIBR_SESSION_SHA
  export MIBR_SESSION_STAMP MIBR_SESSION_DIR MIBR_LOG_FILE MIBR_ARCHIVE_DIR
  return 0
}

mibr_run_logged(){
  SCRIPT=$1
  shift
  RCFILE="/tmp/mibr-altscreen-session-rc.$$"

  [ ! -e "$RCFILE" ] || return 99
  MIBR_LOG_ACTIVE=1
  export MIBR_LOG_ACTIVE

  (
    "$SCRIPT" "$@"
    RC=$?
    echo "$RC" > "$RCFILE"
    exit "$RC"
  ) 2>&1 | "$MIBR_SESSION_TEE" -i -a "$MIBR_LOG_FILE"

  TEE_RC=$?
  if [ -r "$RCFILE" ]; then
    RC=$(cat "$RCFILE" 2>/dev/null)
    rm -f "$RCFILE" 2>/dev/null || true
  else
    RC=99
  fi
  sync 2>/dev/null || true
  echo "Issue log: $MIBR_LOG_FILE"
  [ "$TEE_RC" -eq 0 ] || return 98
  return "$RC"
}

