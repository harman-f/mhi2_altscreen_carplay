#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
. "${0%/*}/master_settings.sh" || exit 10
case "${1:-status}" in
  status) exec "$HELPER" get --key presentation.suggested_urls ;;
  persist|clear-persist) blocked ;;
  clear-temp) clear_key presentation.suggested_urls ;;
  temp)
    shift; [ "$#" -ge 1 ] && [ "$#" -le 8 ] || usage
    V=
    for U in "$@"; do
      case "$U" in *'|'*|*'='*) usage ;; esac
      [ -z "$V" ] && V=$U || V="$V|$U"
    done
    set_key presentation.suggested_urls "$V" ;;
  *) usage ;;
esac
