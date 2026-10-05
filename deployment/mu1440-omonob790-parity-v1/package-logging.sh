# SPDX-License-Identifier: GPL-3.0-or-later
# M.I.B. SD bootstrap precedent, plus existing MU1440 session logger.
# BEGIN_TARGET_ENV -- proven installed MU1440 runtime paths
export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/media/gracenote/bin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin:/mnt/app/armle/usr/sbin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1
# END_TARGET_ENV
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
