#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u
. "${0%/*}/master_settings.sh" || exit 10
case "${1:-status}" in
  status) exec "$HELPER" status ;;
  persist|clear-persist) blocked ;;
  clear-temp) clear_key display.uuid ;;
  temp)
    [ "$#" -eq 6 ] || usage
    batch <<EOF
display.widthPixels=$2
display.heightPixels=$3
display.widthPhysical=$4
display.heightPhysical=$5
display.uuid=$6
EOF
    ;;
  *) usage ;;
esac
