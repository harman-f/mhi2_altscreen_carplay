#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
# EXPERIMENTAL: updateDisplayPanels scaling A/B for parked MU1440 only.
# No persistent configuration, restart, or changes to stock display 110.
set -u

ENABLED=/tmp/mibr-alt111-panel-poc.enabled
REQUEST=/tmp/mibr-alt111-panel-poc.request
STATUS=/tmp/mibr-alt111-panel-poc.status
GEN2=/tmp/mibr-alt111-gen2.status
LOG=/tmp/altscreen111.log
SELF_DIR=$(cd "$(dirname "$0")" 2>/dev/null && pwd)
ROOT=${MIBR_ROOT:-/mnt/app/root/mibr}

help(){
  echo "usage: /bin/ksh $0 on|off|zoom 70|85|100|125|150|physical BASE|P20|P30|P50|status|logs|collect"
  echo "on/off       volatile test enable/disable (default off)"
  echo "zoom/physical  submit one-shot updateDisplayPanels, live session only"
  echo "status       show reply; ACK != visible scaling proof"
  echo "logs         show existing AltScreen log and POC result"
  echo "collect      reuse gen2_collect_logs.sh (default: internal report directory)"
}
case ${1:-help} in
  on)
    touch "$ENABLED" || { echo "PANEL_POC=ENABLE_FAILED";exit 2; }
    echo "PANEL_POC=ENABLED_VOLATILE"
    ;;
  off)
    rm -f "$ENABLED" "$REQUEST"
    echo "PANEL_POC=DISABLED"
    echo "Note: a previously submitted asynchronous command cannot be unsent."
    ;;
  zoom)
    case ${2:-} in
      70|85|100|125|150) value=ZOOM=$2 ;;
      *) help;exit 2 ;;
    esac
    if [ ! -e "$ENABLED" ];then echo "PANEL_POC=DISABLED";exit 3;fi
    if [ -e "$REQUEST" ];then echo "PANEL_POC=REQUEST_PENDING";exit 3;fi
    echo "$value" > "$REQUEST" || exit 4
    echo "PANEL_POC=REQUESTED $value"
    echo "Use: /bin/ksh $0 status"
    ;;
  physical)
    case ${2:-} in
      BASE|P20|P30|P50) value=PHYSICAL=$2 ;;
      *) help;exit 2 ;;
    esac
    if [ ! -e "$ENABLED" ];then echo "PANEL_POC=DISABLED";exit 3;fi
    if [ -e "$REQUEST" ];then echo "PANEL_POC=REQUEST_PENDING";exit 3;fi
    echo "$value" > "$REQUEST" || exit 4
    echo "PANEL_POC=REQUESTED $value"
    echo "Use: /bin/ksh $0 status"
    ;;
  status)
    echo "=== PANEL POC ==="
    if [ -e "$ENABLED" ];then echo "enabled=1";else echo "enabled=0";fi
    if [ -e "$REQUEST" ];then echo "request=waiting";else echo "request=consumed_or_none";fi
    if [ -r "$STATUS" ];then cat "$STATUS";else echo "state=NOT_YET_TESTED";fi
    echo "=== GEN2 ==="
    if [ -r "$GEN2" ];then
      grep -E '^(control_session|command_ready|stream_gen|codec_gen|consumer_gen|desired_view|acknowledged_view|source_aus|source_idrs)=' "$GEN2" 2>/dev/null || true
    else
      echo "gen2=NO_STATUS"
    fi
    ;;
  logs)
    echo "=== PANEL POC ==="
    if [ -r "$STATUS" ];then cat "$STATUS";else echo "state=NOT_YET_TESTED";fi
    echo "=== RECENT PANEL POC LINES ==="
    if [ -r "$LOG" ];then
      grep 'PANEL_POC' "$LOG" 2>/dev/null | tail -100
    else
      echo "altscreen_log=UNAVAILABLE"
    fi
    ;;
  collect)
    COLLECTOR="$SELF_DIR/gen2_collect_logs.sh"
    if [ ! -r "$COLLECTOR" ];then COLLECTOR="$ROOT/scripts/gen2_collect_logs.sh";fi
    if [ ! -r "$COLLECTOR" ];then
      echo "PANEL_POC=COLLECTOR_NOT_INSTALLED"
      exit 5
    fi
    /bin/ksh "$COLLECTOR"
    ;;
  help|-h|--help) help ;;
  *) help;exit 2 ;;
esac
