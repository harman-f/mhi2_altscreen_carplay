#!/bin/ksh
set -u

SESSION_MARKER=/tmp/mibr-alt111-keyframe-policy.enabled
MIBR_ROOT=${MIBR_ROOT:-/mnt/app/root/mibr}
PERSIST_MARKER=$MIBR_ROOT/config/features/mibr-alt111-keyframe-policy.enabled
STATUS=/tmp/mibr-alt111-gen2.status

usage(){
  echo "usage: $0 status|on|off|session-on|session-off"
  exit 2
}

enabled(){
  [ -e "$SESSION_MARKER" ] || [ -e "$PERSIST_MARKER" ]
}

case "${1:-status}" in
  status)
    enabled && echo "GEN2_D2_KEYFRAMES=ENABLED" || echo "GEN2_D2_KEYFRAMES=DISABLED"
    if [ -e "$PERSIST_MARKER" ]; then
      echo "GEN2_D2_MODE=persistent"
    elif [ -e "$SESSION_MARKER" ]; then
      echo "GEN2_D2_MODE=session"
    else
      echo "GEN2_D2_MODE=off"
    fi
    echo "persistent_marker=$PERSIST_MARKER"
    echo "session_marker=$SESSION_MARKER"
    if [ -r "$STATUS" ]; then
      grep '^d2_' "$STATUS" 2>/dev/null || true
      grep '^resync_' "$STATUS" 2>/dev/null || true
      grep '^source_idrs=' "$STATUS" 2>/dev/null || true
    else
      echo "GEN2_CORE_STATUS=NOT_AVAILABLE"
    fi
    ;;
  on)
    touch "$PERSIST_MARKER" || exit 1
    touch "$SESSION_MARKER" 2>/dev/null || true
    sync
    echo "GEN2_D2_KEYFRAMES=ENABLED"
    echo "GEN2_D2_MODE=persistent"
    echo "Policy: turns-edge/suggestUI -> 250ms debounce; 1s IDR watchdog; 1s minimum request gap."
    echo "Persistent across unit reboot. No reboot required for the current session."
    ;;
  off)
    rm -f "$PERSIST_MARKER" "$SESSION_MARKER"
    sync
    echo "GEN2_D2_KEYFRAMES=DISABLED"
    echo "GEN2_D2_MODE=off"
    echo "No reboot required. Manual Candidate-D controls remain separate."
    ;;
  session-on)
    touch "$SESSION_MARKER" || exit 1
    sync
    echo "GEN2_D2_KEYFRAMES=ENABLED"
    echo "GEN2_D2_MODE=session"
    echo "Volatile session-only enable; cleared by reboot."
    ;;
  session-off)
    rm -f "$SESSION_MARKER"
    sync
    if [ -e "$PERSIST_MARKER" ]; then
      echo "GEN2_D2_KEYFRAMES=ENABLED"
      echo "GEN2_D2_MODE=persistent"
    else
      echo "GEN2_D2_KEYFRAMES=DISABLED"
      echo "GEN2_D2_MODE=off"
    fi
    ;;
  *)
    usage
    ;;
esac
