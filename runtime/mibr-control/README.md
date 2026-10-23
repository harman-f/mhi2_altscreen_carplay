# MIBR/3 reference runtime scripts

These source files are retained for review and host-side development. They are
not a supported installation package.

- `mibr-engine.ksh` reads or changes the `engine=` field inside `[vehicle]` in
  `iap2.cfg`. It preserves line count, uses a same-directory temporary file,
  and remounts the system filesystem read-only after a write path. The running
  announcement is captured separately, so a changed value can be reported as
  pending until the consumer restarts.
- `mibr-v3-boot.ksh` is the historical service startup helper. It can start the
  broker and optional key-event daemon from the existing source. Its presence does not establish
  that a service process is authorized, a secret is correctly provisioned, or
  the persistent settings path is qualified on another unit.
- `mibr-view.ksh` maintains the cockpit-view position and configured resync
  target, and optionally applies the existing `viewarea.selected` TEMP setting
  for the three map views. KEY40 long press records the view after the selected
  resync target because the OEM view advances once on that press. Its persistent
  state defaults to `/mnt/app/root/mibr-view`; fixed-view mode defaults OFF,
  Sporttacho-present defaults ON, and the resync target defaults to Voll.

The scripts do not make external `printf`, `sed`, or `tr` dependencies. Their
remaining QNX command and mount behavior has not been requalified by this
source publication. Host tests use temporary files and a no-mount test switch;
they are not QNX compatibility or vehicle tests. Do not copy these scripts to a
unit as a standalone runtime change.

The physical input port, dispatch path, and independent route visibility/ACTIVE
result remain unqualified. The R57 source mapping itself uses KEY40 short for
view step, KEY40 long for resync, and KEY44 long for the route toggle; it does
not establish that the target input path is qualified. The controller's boot
lifecycle and persistent-storage gate must be reviewed as one exact-target
integration before either script is used operationally.
Current source status and evidence boundaries are documented in
[`docs/architecture/mibr-control/BUILD_AND_EVIDENCE.md`](../../docs/architecture/mibr-control/BUILD_AND_EVIDENCE.md).
