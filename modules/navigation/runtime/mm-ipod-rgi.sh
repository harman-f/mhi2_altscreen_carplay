#!/bin/sh
# mm-ipod with the MIBR route-guidance library (R2). /etc/usblauncher_otg.lua selects this
# wrapper (with config=/dev/shmem/mibr-rgi-iap2.cfg) only while $MIBR_ROOT/config/features/rgi.on exists
# (default /mnt/app/root/mibr).
# The RAM config starts as an exact copy of /etc/mm/iap2.cfg; the library appends the [ident]
# message IDs only after its driver checks passed. After an IdentificationRejected this start and
# all later ones run fully stock until reboot. The helper starts first, so after the exec its
# parent is mm-ipod and it ends with this connection.
PATH=/proc/boot:/bin:/usr/bin:/mnt/app/armle/bin:/mnt/app/armle/usr/bin
MIBR_ROOT=${MIBR_ROOT:-/mnt/app/root/mibr}
D=$MIBR_ROOT/bin
CFG=/dev/shmem/mibr-rgi-iap2.cfg
cp /etc/mm/iap2.cfg "$CFG" || exit 1
# Single kill switch (E4): only state/boot/disabled, never the legacy mibr-kit/disabled.
if [ -r "$MIBR_ROOT/state/boot/disabled" ] || [ -f /dev/shmem/mibr-rgi-rejected ] || grep -q '^\[ident\]' "$CFG"; then
  exec /mnt/app/armle/usr/sbin/mm-ipod "$@"
fi
"$D/mibr-rgi" </dev/null >/dev/null 2>&1 &
LD_PRELOAD="$D/libmibr_rgi_ipod.so${LD_PRELOAD:+:$LD_PRELOAD}" exec /mnt/app/armle/usr/sbin/mm-ipod "$@"
