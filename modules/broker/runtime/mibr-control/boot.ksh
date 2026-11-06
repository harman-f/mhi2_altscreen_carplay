#!/bin/ksh
# MIBR CarPlay kit boot start, called once from the MIBR-KIT block in lsd.sh right before the HMI (J9) starts.
# It repeats, in the same order and with the same conditions, the three blocks of the accepted development unit
# (lsd.sh "MIBR AUTO-DIRECT", "MIBR CPVC R5" + "MIBR PARITY-DRIVE", "MIBR V3 BROKER"). The environment (LD_PRELOAD etc.)
# is inherited from lsd.sh exactly as it was for those blocks. Never blocks the HMI boot: every step is optional and
# logs to /tmp.
MIBR_ROOT=${MIBR_ROOT:-/mnt/app/root/mibr}
A=$MIBR_ROOT
# Single kill switch (E4): only state/boot/disabled; the legacy mibr-kit/disabled is not read.
[ -r $MIBR_ROOT/state/boot/disabled ] && { echo MIBR_KIT_BOOT=DISABLED; exit 0; }

# AUTO-DIRECT
[ -r $A/scripts/direct_ts_auto_start.sh ] && /bin/ksh $A/scripts/direct_ts_auto_start.sh >/tmp/mibr-direct-auto-boot.log 2>&1 || true

# CPVC R5: replay the profile, then start the single supervisor; without the enable marker the supervisor starts alone
if [ -r $MIBR_ROOT/config/features/mibr-cpvc.enabled ] && [ "$(cat $MIBR_ROOT/config/features/mibr-cpvc.enabled 2>/dev/null)" = "1" ]; then
    if /bin/ksh $A/scripts/cpvc_config.sh _boot-replay >/tmp/mibr-cpvc-profile-boot.log 2>&1; then
        /bin/ksh $A/scripts/parity_drive_supervisor.sh >/tmp/mibr-cpvc-runtime-boot.log 2>&1 &
    else
        echo CPVC_BOOT=PROFILE_FAILED_STOCK_ONLY >/tmp/mibr-cpvc-boot.state
    fi
else
    /bin/ksh $A/scripts/parity_drive_supervisor.sh >/tmp/mibr-parity-drive-boot.log 2>&1 &
fi

# V3 BROKER (menu broker + key daemon)
[ -x $MIBR_ROOT/scripts/mibr-v3-boot.ksh ] && /bin/ksh $MIBR_ROOT/scripts/mibr-v3-boot.ksh >/tmp/mibr-v3-boot.log 2>&1
echo MIBR_KIT_BOOT=DONE
exit 0
