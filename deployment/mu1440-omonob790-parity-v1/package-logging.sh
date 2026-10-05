# SPDX-License-Identifier: GPL-3.0-or-later
# M.I.B. SD bootstrap precedent, plus existing MU1440 session logger.
PATH=/sbin:/bin:/usr/sbin:/usr/bin:/net/rcc/bin:/net/rcc/usr/bin
export PATH
unset LD_PRELOAD
CARD=/net/mmx/fs/sda0
PACKAGE_CARD_RW=0
package_card_ro(){
  if [ "$PACKAGE_CARD_RW" -eq 1 ]; then
    sync
    mount -ur "$CARD" 2>/dev/null || return 1
    PACKAGE_CARD_RW=0
  fi
}
package_log_init(){
  . "$ROOT/runtime/session-logging.sh" || return 1
  [ -x "$CARD/apps/mounts" ] || return 2
  . "$CARD/apps/mounts" -usb >/dev/null 2>&1 || return 3
  PACKAGE_CARD_RW=1
  trap 'package_card_ro' 0
  trap 'package_card_ro; exit 129' 1
  trap 'package_card_ro; exit 130' 2
  trap 'package_card_ro; exit 143' 15
  mibr_prepare_session "$1" "$CARD" "$CARD/apps/sbin/tee" "$ROOT/payload/sha256sum"
}
