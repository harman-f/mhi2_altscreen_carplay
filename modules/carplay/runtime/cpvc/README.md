# CPVC profile replay

`cpvc_config.sh` is the single configuration CLI for the persistent CPVC profile
(`/mnt/app/root/mibr/config/cockpit/cpvc-r5.profile`) and its boot replay mode.

- `_boot-replay` is called synchronously by `modules/broker/runtime/mibr-control/boot.ksh` before the HMI starts. It
  validates the profile through the native settings helper (`alt111-settings batch --layer temp`) and loads it into the
  TEMP layer. If the profile is missing, unreadable or rejected, it falls back to the last verified copy
  (`cpvc-r5.profile.lastgood`) and keeps the broken file as `.corrupt`. A failure leaves the stock boot running.
- `status`, `enable`, `disable`, `set KEY VALUE` and `zoom ...` are operator commands. `set` only accepts a fixed
  key list and a restricted value alphabet; the native validator has the final say.
- The script writes to `/mnt/app` only inside a short read-write window and restores read-only on exit.

Status: the host fallback test `tests/mibr-control/test_cpvc_lastgood_fallback.py` runs the script in a sandbox with a
stub helper. No new vehicle evidence is claimed by publishing this source.

Source lineage: the installed MU1440 script differs from this source only in one help-text line (maxFPS list now
includes 60).
