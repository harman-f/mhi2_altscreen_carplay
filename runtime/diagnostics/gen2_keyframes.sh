#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
. "${0%/*}/master_settings.sh" || exit 10
case "${1:-status}" in
  status) exec "$HELPER" status ;;
  persist|clear-persist) blocked ;;
  clear-temp|default) clear_key keyframe.mode; exit $? ;;
  temp) shift ;;
esac
case "${1:-}" in
  on) [ "$#" -eq 1 ] || usage; set_key keyframe.mode source_frames ;;
  off) [ "$#" -eq 1 ] || usage; set_key keyframe.mode off ;;
  mode) [ "$#" -eq 2 ] || usage; set_key keyframe.mode "$2" ;;
  frames) [ "$#" -eq 2 ] || usage; set_key keyframe.interval_frames "$2" ;;
  source-time)
    [ "$#" -eq 2 ] || usage
    batch <<EOF
keyframe.mode=source_time
keyframe.interval_ms=$2
EOF
    ;;
  timing)
    echo "result=POLICY_BLOCKED legacy_wall_timer_removed_use_source_frames_or_source_time"; exit 24 ;;
  *) usage ;;
esac
