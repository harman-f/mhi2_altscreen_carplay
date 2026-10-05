# BEGIN_TARGET_ENV -- proven installed MU1440 runtime paths
export PATH=/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/media/gracenote/bin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin:/mnt/app/armle/usr/sbin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1
# END_TARGET_ENV
# SPDX-License-Identifier: GPL-3.0-or-later
# Sourced by installed compatibility wrappers; all mutations use the registry.
HELPER="$MASTER_SCRIPT_ROOT/../bin/alt111-settings"
[ -x "$HELPER" ] || { echo "result=APPLY_FAILED missing_settings_helper"; exit 10; }
usage(){ echo "result=INVALID_VALUE arguments"; exit 2; }
# Reject line injection before constructing a native stdin batch.
for MASTER_ARG in "$@"; do
  case "$MASTER_ARG" in *'
'*) usage ;; esac
done
blocked(){ echo "result=POLICY_BLOCKED persistent_backup_powerloss_gate"; exit 24; }
set_key(){ "$HELPER" set --key "$1" --value "$2"; }
clear_key(){ "$HELPER" clear --key "$1"; }
batch(){ "$HELPER" batch --input -; }
apply_presentation(){
  "$HELPER" status || return $?
  # This diagnostic requests SHOW through the serialized current-session
  # controller. Consuming a marker is not a completion acknowledgement.
  echo request > /tmp/mibr-alt111-gen2-reacquire || return 10
  echo "runtime_result=QUEUED completion=see_current_gen2_session_request_status"
}
