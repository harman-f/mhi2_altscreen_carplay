#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
. /mnt/app/root/altscreen-u2/scripts/common.sh
runtime_init || { echo "DIRECT_FPS=FAIL_RUNTIME"; exit 3; }
load_altscreen_config || { echo "DIRECT_FPS=FAIL_CONFIG"; exit 4; }

FILE=$DIRECT_FPS_OVERRIDE_FILE
SOURCE_FILE=$SOURCE_FPS_OVERRIDE_FILE
BRIDGEPID=/tmp/mibr-direct-auto-bridge.pid

show_status(){
  load_altscreen_config >/dev/null 2>&1 || true
  echo "source_max_fps=$ALTSCREEN111_FPS"
  echo "direct_output_fps=$DIRECT_OUTPUT_FPS"
  echo "direct_pace=$DIRECT_PACE"
  echo "direct_pace_buffer=$DIRECT_PACE_BUFFER"
  [ -r "$FILE" ] && echo "direct_override=$(cat "$FILE" 2>/dev/null)" || echo "direct_override=none"
  [ -r "$SOURCE_FILE" ] && echo "source_override=$(cat "$SOURCE_FILE" 2>/dev/null)" || echo "source_override=none"
  if [ -r /tmp/mibr-direct-remux.status ]; then
    grep -E '^(pace_|last_input_interval_us|min_input_interval_us|max_input_interval_us|last_emit_interval_us|max_emit_jitter_us)=' /tmp/mibr-direct-remux.status 2>/dev/null || true
  fi
}

OLD_SOURCE_FPS=$ALTSCREEN111_FPS
if [ -r "$SOURCE_FILE" ]; then
  OLD_SOURCE_FPS=$(cat "$SOURCE_FILE" 2>/dev/null)
fi
case "$OLD_SOURCE_FPS" in 20|25|30) ;; *) OLD_SOURCE_FPS=$ALTSCREEN111_FPS ;; esac

case "${1:-status}" in
  status)
    show_status
    exit 0
    ;;
  20|25|30)
    FPS=$1
    mount -uw /mnt/app 2>/dev/null || { echo "DIRECT_FPS=FAIL_MOUNT_RW"; exit 10; }
    TMP="$FILE.new.$"
    STMP="$SOURCE_FILE.new.$"
    echo "$FPS" > "$TMP" || {
      rm -f "$TMP" "$STMP" 2>/dev/null || true
      mount -ur /mnt/app 2>/dev/null || true
      echo "DIRECT_FPS=FAIL_WRITE"
      exit 11
    }
    echo "$FPS" > "$STMP" || {
      rm -f "$TMP" "$STMP" 2>/dev/null || true
      mount -ur /mnt/app 2>/dev/null || true
      echo "DIRECT_FPS=FAIL_SOURCE_WRITE"
      exit 11
    }
    mv "$TMP" "$FILE" || {
      rm -f "$TMP" "$STMP" 2>/dev/null || true
      mount -ur /mnt/app 2>/dev/null || true
      echo "DIRECT_FPS=FAIL_RENAME"
      exit 12
    }
    mv "$STMP" "$SOURCE_FILE" || {
      rm -f "$STMP" 2>/dev/null || true
      mount -ur /mnt/app 2>/dev/null || true
      echo "DIRECT_FPS=FAIL_SOURCE_RENAME"
      exit 12
    }
    sync
    mount -ur /mnt/app 2>/dev/null || true
    echo "DIRECT_FPS=SET fps=$FPS"
    if [ "$FPS" != "$ALTSCREEN111_FPS" ]; then
      echo "SOURCE_RATE_NOTE=new /info advertisements request maxFPS=$FPS"
      echo "SOURCE_RATE_NOTE=current CarPlay session keeps its existing negotiation; reconnect CarPlay before judging the matched $FPS-fps test"
    fi
    if [ "$FPS" != "$OLD_SOURCE_FPS" ]; then
      echo "CARPLAY_RECONNECT_REQUIRED=YES old_source_fps=$OLD_SOURCE_FPS new_source_fps=$FPS"
      echo "bridge_restart_requested=deferred_until_source_renegotiation"
    else
      P=
      [ -r "$BRIDGEPID" ] && P=$(cat "$BRIDGEPID" 2>/dev/null)
      if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then
        kill "$P" 2>/dev/null || true
        echo "bridge_restart_requested=1"
      else
        echo "bridge_restart_requested=0"
      fi
    fi
    exit 0
    ;;
  default)
    mount -uw /mnt/app 2>/dev/null || { echo "DIRECT_FPS=FAIL_MOUNT_RW"; exit 10; }
    rm -f "$FILE" "$SOURCE_FILE" 2>/dev/null || true
    sync
    mount -ur /mnt/app 2>/dev/null || true
    echo "DIRECT_FPS=DEFAULT"
    if [ "$OLD_SOURCE_FPS" != "$ALTSCREEN111_FPS" ]; then
      echo "CARPLAY_RECONNECT_REQUIRED=YES old_source_fps=$OLD_SOURCE_FPS new_source_fps=$ALTSCREEN111_FPS"
      echo "bridge_restart_requested=deferred_until_source_renegotiation"
    else
      P=
      [ -r "$BRIDGEPID" ] && P=$(cat "$BRIDGEPID" 2>/dev/null)
      if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then
        kill "$P" 2>/dev/null || true
        echo "bridge_restart_requested=1"
      else
        echo "bridge_restart_requested=0"
      fi
    fi
    exit 0
    ;;
  *)
    echo "usage: $0 status|20|25|30|default"
    exit 64
    ;;
esac
