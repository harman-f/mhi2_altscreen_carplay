# MIBR/3 reference runtime scripts

These source files are retained for review and host-side development. They are
not a supported installation package.

- `mibr-engine.ksh` reads or changes the `engine=` field inside `[vehicle]` in
  `iap2.cfg`. It preserves line count, uses a same-directory temporary file,
  and remounts the system filesystem read-only after a write path. The running
  announcement is captured separately, so a changed value can be reported as
  pending until the consumer restarts.
- `mibr-v3-boot.ksh` is the historical service startup helper. It can start the
  broker and optional KEY40 route-toggle daemon from the existing source. Its presence does not establish
  that a service process is authorized, a secret is correctly provisioned, or
  the persistent settings path is qualified on another unit.

The scripts do not make external `printf`, `sed`, or `tr` dependencies. Their
remaining QNX command and mount behavior has not been requalified by this
source publication. Host tests use temporary files and a no-mount test switch;
they are not QNX compatibility or vehicle tests. Do not copy these scripts to a
unit as a standalone runtime change.

The physical gesture mapping and independent route visibility/ACTIVE result
remain unqualified. The controller's boot lifecycle and persistent-storage
gate must be reviewed as one exact-target integration before either script is
used operationally.
Current source status and evidence boundaries are documented in
[`docs/architecture/mibr-control/BUILD_AND_EVIDENCE.md`](../../docs/architecture/mibr-control/BUILD_AND_EVIDENCE.md).
