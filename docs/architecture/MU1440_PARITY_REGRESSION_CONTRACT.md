# MU1440 parity regression contract

Target: MHI2_ER_SKG13_P4526_MU1440 / AID10. Current implementation:
[harman-f/mhi2_altscreen_carplay#15](https://github.com/harman-f/mhi2_altscreen_carplay/pull/15),
Draft / DO NOT MERGE. Source identity comes from the exact candidate manifest.
Historical review baseline:
`ee82305beae00612755113c387e09270a8905836`,
[harman-f/mhi2_altscreen_carplay#14](https://github.com/harman-f/mhi2_altscreen_carplay/issues/14).
Correction branch: `codex/omonob790-regression-hardening-v1`.
The earlier vehicle-tested artifacts and reviewed source are preserved.

## Candidate identity

Build GEN2, direct-ts-parity, parity-session, alt111-settings and the independent
DisplayManager guard from one exact source commit.
Materialize their complete overlay together with source commit and SHA-256 of
the payload and every generated script. Never update binaries inside an existing
candidate directory. Persist the actual package bytes before handoff; an expiring
Actions artifact is transport, not the durable research copy.

Install requires the recorded ENVFIX2 GEN2/hook and remux hashes, target
libairplay hash, and the frozen vehicle-tested gate hash
`05673010a88c25022145ffb4e75d3715eaf686f4127ac188e91a52f512b9d957`.
The historical gate bytes remain unchanged. writev_gate is the initial backend;
the new independent guard is preloaded first into DisplayManager. GEN2 remains
in smartphone_integrator and cannot certify another process's writes.
Native exclusion requires a fresh request-token acknowledgement, registered
target descriptors, zero in-flight writes and a new positive suppression count.
The owner monitors heartbeat/process/token throughout the run, freezes its
backend, and binds its bridge to the exact SHA built into the owner.

dmdt_reference is selectable as a routing-only probe. It executes dc72/sc4-72,
waits 500 ms and restores dc70-33/sc4-70, with no custom writer. Its result is
OWNERSHIP_UNPROVEN until independent target evidence qualifies a future payload
adapter. There is no automatic fallback or mixed backend.

The guard tracks open/open64, close, dup/dup2, write/writev and QNX devctl.
Inherited handles, fcntl aliases and direct resource-manager calls remain a
target ABI qualification gate. In-process drain is distinct from MOST driver
queue drain and visible cluster recovery.

Stop uses an owner-generation request, never a PID-file signal. Parent and
watchdog retain bound bridge identities and require confirmed writer death
before disabling exclusion or restoring routing. Unknown stop/restore leaves
the session quarantined. The package restores all hashes/ABSENT states,
including original boot script, helper, guard and temporary settings. Its
rollback reader barrier stays until the canonical normal reboot.

## Media invariants

- One complete M1AU record supplies one complete AU. Source ordinal, source
  timestamp and generation are distinct fields. Never rediscover AU identity
  through a generic raw-H.264 parser.
- Canonical AU starts with one AUD. IDR has SPS then PPS before VCL; a partial
  update preserves the other parameter-set type. Generation change clears cache.
- Relative 32.32 time uses fractional borrow and modulo seconds rollover.
  Successive-source rollback and forward jumps inconsistent with elapsed time
  rebase the origin. Preserve legitimate variable cadence and idle intervals.
- PAT/PMT/PCR/video PIDs stay 0/0x10/0x1000/0x11. PAT/PMT CRC, continuity,
  payload integrity and source-clock vectors are independently tested.
- The **transport**, including null fill, is paced from absolute monotonic
  deadlines at 12.288 Mbit/s on every output. There is no fixed **frame** pacer.
  A 64-packet block advances nominal PCR by 705 ticks. A late acceptance beyond
  40 ms or a short block acceptance fails explicitly; a retry never converts a
  short device acceptance into a different-size physical write.
- PTS is guarded again when an AU begins leaving the queue. Its minimum budget
  covers the complete PES, periodic transport slots, block margin and 50 ms.
  The nominal 100 ms origin alone is insufficient for a large IDR.
- Records above the 256-KiB reference transfer budget are consumed within the
  bounded envelope but dropped as whole AUs, followed by IDR recovery.
- Recovery preserves any PES already started. EOF acknowledges the writer-local
  final block only after write completion. Partial header/payload and invalid
  metadata return failure, never a successful EOF.
- Reference every-20-source-frame requests originate in GEN2 before consumer
  and drop decisions. Startup/gap/latency requests remain bridge responsibilities.

## Ownership and reversal

Only one parity owner may start. An exclusive flat lock file plus POSIX record
locks protects the parent, watchdog and manual reconciliation. Live legacy
supervisor/watchdog/bridge reject startup. DMDT release is dc72/sc4-72, then
500 ms, and restore is dc70-33/sc4-70.

The watchdog establishes its lock and publishes readiness before release.
Close-on-exec pipe descriptors expose parent death even while the bridge runs.
The bridge cannot exec until its PID is published. Watchdog death is monitored.
Timeout and SIGKILL reaping paths do not wait indefinitely. Restore failure is
reported as failure and keeps the lock. Emergency restore quarantines the stale
session until explicit stock reconciliation; it never lets a new owner race a
possibly delayed previous restore.

Profiles in this candidate are volatile only. Persistent compatibility-profile
changes are blocked while the overlay or its backup is present. Before persistent
mutation, the standard SD log exporter mounts and write-tests its destination.
Backups are hashed against originals before apply, verified before restoration,
and restored bytes are verified afterwards. Failure of direct apply invokes
rollback. Verified backups are retained; future installation refuses the retained
directory until a separately reviewed archival/retirement action.

## Verification boundary

CI runs the original integration/recovery checks plus actual-C boundary vectors,
large-PES immediate EOF/deadline tests, malformed records, POSIX lifecycle fault
injection, shared-wrapper transactions and sandboxed installer/restore fault injection.
A real moving H.264 source with IDR and predictive pictures is decoded before
and after transport; all 40 decoded frame hashes must match, including motion
between IDRs. This is host evidence, not a vehicle decoder qualification. It builds all five
QNX ARM native components and verifies the complete generated package.

These tests do not prove the physical MOST drain, exact device buffer delay,
loaded in-memory target identities, visible predictive pictures or target DMDT
return. The runtime pacing guards bound software behavior; they are a deliberate
documented difference from relying solely on reference driver backpressure.
An offline-ready build must retain **NOT VEHICLE-READY** until these target
questions are assessed. No CI or counter-only result is a moving-video PASS.

The prior ENVFIX2 failure and new candidate validation are separate findings.
A successful parity run would prove the new combination, not identify the old
single-component root cause. Keep source-clock, transport and recovery evidence
separate from provider/layout comfort changes.
