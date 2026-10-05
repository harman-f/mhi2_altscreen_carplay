#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
case "$0" in */*) MASTER_SCRIPT_ROOT=${0%/*} ;; *) MASTER_SCRIPT_ROOT=. ;; esac
. "$MASTER_SCRIPT_ROOT/master_settings.sh" || exit 10
KEY=maxFPS
case "${1:-status}" in
  status) exec "$HELPER" get --key "$KEY" ;;
  temp) [ "$#" -eq 2 ] || usage; set_key "$KEY" "$2" ;;
  persist|clear-persist) blocked ;;
  clear-temp|default) clear_key "$KEY" ;;
  apply) [ "$KEY" = navigation.url ] || usage; apply_presentation ;;
  *) [ "$#" -eq 1 ] || usage; set_key "$KEY" "$1" ;;
esac
