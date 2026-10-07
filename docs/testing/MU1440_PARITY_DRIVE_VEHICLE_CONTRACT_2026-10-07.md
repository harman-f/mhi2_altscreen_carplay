# MU1440 parity-drive vehicle findings and runtime contract — 2026-10-07

Status: **development / vehicle evidence exists / soak test pending**.

Target vehicle and unit:

- Škoda Octavia III (2016)
- MHI2 ER SKG13 P4526 MU1440
- AID10 Virtual Cockpit
- AlternateScreen / CarPlay type 111

This document freezes the decisions made after the first visible AID10 output through the
clean-room parity-drive path. It is also a regression guard for future implementation and
handoffs.

## 1. Positive vehicle evidence

The exact MU1440 has now reached the full custom media path:

```text
CarPlay Stream-111
  -> GEN2 complete AU / M1AU
  -> parity-session ownership
  -> direct-ts-parity
  -> /dev/mlb/isoTX2
  -> MOST
  -> visible CarPlay image in AID10
```

The first visible run used the matched `5c9767a0` owner/bridge pair. Exact target output included:

```text
PARITY_PROCESS_IDENTITY_SELFTEST=PASS inherited_handle_signal_and_exit no_most_io
PARITY_DRIVER interface status=0 value=131073
PARITY_DRIVER packet_size status=0 value=188
PARITY_DRIVER block_count status=0 value=64
PARITY_DRIVER queue_flush status=25
PARITY_DRIVER start status=0 packets=64
PARITY_DRIVER queue_flush unsupported=ENOTTY continue=YES
PARITY_START input=tcp://127.0.0.1:19820 output=/dev/mlb/isoTX2 transport_bps=12288000 block=12032 ...
```

A CarPlay navigation image was visible in the VC. Smoothness was not yet proven because the run
was terminated by an application-side transport deadline shortly afterward.

That failure was not a driver START failure and not an ownership failure.

## 2. Exact driver findings

On the exact MU1440:

- interface readback succeeds and returns `131073`;
- packet size readback succeeds and returns `188`;
- block count readback succeeds and returns `64`;
- queue FLUSH returns QNX `ENOTTY (25)`;
- START succeeds with status `0` and 64 packets.

Therefore only `ENOTTY` is tolerated for the optional FLUSH command. Other FLUSH errors remain
fatal. All required readbacks and START remain fail-closed.

## 3. Device pacing decision

The 40-ms application-side fatal lateness check was disproven by the vehicle.

A valid `12032`-byte `isoTX2` write can be accepted late enough to violate the former synthetic
deadline while still producing a visible AID10 image.

Current contract:

- regular-file fixture output may use application pacing;
- real `/dev/mlb/isoTX2` output is paced by QNX driver backpressure;
- physical writes remain exactly `64 * 188 = 12032` bytes;
- device output stays `O_NONBLOCK`;
- EAGAIN/backpressure handling remains bounded by the existing 500-ms write timeout;
- observed write latency is measured as `last_write_us` and `max_write_us`;
- no arbitrary larger replacement for the rejected 40-ms deadline is introduced.

This proves accepted-block behavior, not physical MOST drain timing. Hardware drain remains a
separate evidence gate.

## 4. IDR, non-IDR and slice telemetry

The runtime now records both source/input and post-write output evidence.

Source / GEN2:

- `source_aus`
- `source_idrs`
- `delivered_aus`
- `dropped_aus`
- measured source-arrival FPS where timing diagnostics are enabled.

Parity input:

- `input_records`
- `input_idrs`
- `input_non_idr_aus`
- H.264 slice classification counts for P/B/I/unknown where parseable.

Parity output:

- AU start/completion counters;
- IDR/non-IDR start/completion counters;
- P/B/I/unknown slice start/completion counters.

Output counters are committed only after successful acceptance of the complete 12032-byte MOST
block containing the corresponding AU event. They are not incremented merely because a packet was
removed from the software queue.

This can prove that non-IDR/P/B/I material reached the accepted TS output boundary. It does **not**
by itself prove that the AID decoder presented every corresponding picture.

## 5. Recovery request compatibility

The reason-aware recovery helper still contained POSIX primitives already disproven on this exact
MU1440 `/tmp == /dev/shmem` implementation. The bridge therefore uses the reason-aware recovery
request first and falls back to the existing one-shot:

```text
/tmp/mibr-alt111-keyframe-only
```

The installed GEN2 path consumes this marker through its serialized `forceKeyFrame` control path.

## 6. Exact /tmp and /dev/shmem rules

Do not regress these target-proven rules:

- `/tmp` is a symlink/alias to `/dev/shmem` on this target;
- flat regular-file create/write/read/unlink works;
- direct truncate/rewrite works;
- `O_CREAT|O_EXCL` works and is used for owner-lock creation;
- `fcntl(F_SETLK)` is not implemented on this shmem path;
- native `rename()` across the `/tmp` / `/dev/shmem` spelling boundary can return `EXDEV`;
- shell `mv` is not evidence that native `rename()` works;
- owner identity is bound by the held lock inode, not by pathname contents alone.

Parity live-status publication therefore uses direct truncate/write rather than temp+rename.

## 7. Process termination: shell kill, slay and SignalKill

This distinction is mandatory and is a previous regression source.

### Stock processes

The parity-drive path does **not** terminate or restart stock media processes for normal operation.
In particular it does not kill:

- DisplayManager;
- `smartphone_integrator`;
- `dio_manager`.

The writev-gate temporarily suppresses the native `isoTX2` payload while the stock process remains
alive. Releasing the gate returns ownership to stock.

### Shell command contract

Do not copy a bare shell `kill` command into MU1440/MHI2 operating instructions.

Stock MHI2 evidence uses the QNX administrative command `slay`. Historical MHI1Q command examples
must not be imported into this target without proof.

The new parity-drive supervisor deliberately does not use shell `kill` as process authority.
PID files are diagnostic only.

### Owned parity bridge

The owner must still be able to stop **its own temporary bridge child** before returning the gate
to stock. This is not a stock-process kill.

The qualified owner mechanism is:

1. fork the bridge;
2. open and retain `/proc/<pid>/as`;
3. use the bound process object to pin identity / PID reuse;
4. use native QNX `SignalKill` through `bound_process_signal()`;
5. prove TERMINATED on the bound procfs object;
6. close the final procfs handle and reap;
7. only then restore the stock route.

Exact vehicle self-test:

```text
PARITY_PROCESS_IDENTITY_SELFTEST=PASS inherited_handle_signal_and_exit no_most_io
```

No PID-file value alone authorizes a termination signal.

C-library `kill()` calls that exist in bounded helper/self-test/direct-child code are not a shell
command contract and must not be generalized into operator instructions. Production bridge
termination prefers the bound `SignalKill` adapter.

## 8. Long-run / autostart decision

The parity owner now supports:

```text
MAX_SECONDS=0
```

meaning **until-stop operation**.

This does not disable fail-safe recovery. In until-stop mode:

- the owner still verifies the native gate continuously;
- bridge exit stops the session;
- gate-proof loss stops the session;
- an explicit token-bound `--stop` stops the session;
- the independent watchdog remains active;
- parent/watchdog failure still triggers emergency stock restore.

Finite diagnostic sessions remain available from 60 to 7200 seconds.

The new parity-drive supervisor defaults to until-stop operation and waits for a valid Stream-111
session before starting.

## 9. Boot/autostart behavior

The parity-drive enable path installs a guarded `lsd.sh` hook.

Important properties:

- no enable marker -> hook is inert;
- enabling parity-drive makes legacy Auto-Direct persistent config `0`;
- the supervisor does not disturb an already-present parity owner;
- temporary `mibr_dual_view` profile is applied before the drive session;
- if that profile was applied while Stream-111 was active, the supervisor waits for a reconnect
  before ownership;
- no stock app restart is required by this path.

## 10. Diagnostics controls

Live status and persistent statistics are independently user-switchable for future use.

Control script:

```text
/mnt/app/root/altscreen-u2/scripts/parity_drive_status.sh
```

Supported controls:

```text
status
status-on [temp|persistent]
status-off [temp|persistent]
statistics-on [temp|persistent]
statistics-off [temp|persistent]
all-on [temp|persistent]
all-off [temp|persistent]
clear-temp
```

Layer priority is:

```text
temp -> persistent -> default
```

Defaults are ON.

Statistics require live status counters, so `statistics-on` also enables status and a contradictory
manual configuration is reduced fail-safe to statistics OFF.

Changes apply to the next parity session.

## 11. SD-only drive evidence

Drive evidence must not silently fall back to volatile `/tmp`.

Exact root:

```text
/net/mmx/fs/sda0/esd/carplay-test/logs/parity-drive
```

Before a drive session the supervisor must successfully execute and verify:

```sh
mount -uw /net/mmx/fs/sda0
```

If the SD cannot be made writable and a write-test cannot be completed, parity-drive remains in
`waiting_log_media` and no custom ownership session is started.

The SD is synced periodically and remounted read-only on supervisor cleanup:

```sh
sync
mount -ur /net/mmx/fs/sda0
```

Persistent evidence includes:

```text
drive-supervisor.log
current.status
current.statistics
<timestamp>-session-N/
    session.log
    telemetry.tsv
    status-snapshots.log
    parity-final.status
    gen2-final.status
    source-timing-final.status
    altscreen111.log
    gate-final.status
    summary.txt
```

`current.status` and `current.statistics` are intentionally separate so status snapshots can stay
enabled while high-rate statistical logging is disabled.

## 12. Matched owner/bridge binaries are mandatory

`parity-session` contains the exact SHA-256 identity of the bridge built with it.

Never mix a new owner with an older installed `direct-ts-parity`. A mismatch must fail before
ownership mutation with:

```text
ERROR bridge does not match this owner build; no ownership mutation
```

Vehicle tests must use the two binaries from the same successful CI artifact.

## 13. Operator command regression guards

Do not invent generic Linux commands for this unit.

In particular:

- do not use bare shell `reboot`;
- do not use `fastReboot`;
- do not use shell `kill` as the documented MU1440/MHI2 process-control command;
- do not infer native-QNX semantics from shell `mv`;
- do not reintroduce `F_SETLK` on target shmem;
- do not restart `smartphone_integrator` or `dio_manager` as part of normal parity-drive;
- do not manually stop DisplayManager for the writev-gate path.

Canonical IOC reboot when needed:

```sh
sync; sync; sync; on -f rcc /usr/apps/mib2_ioc_flash reboot
```

When returning the SD read-only first:

```sh
sync; sync; sync; mount -ur /net/mmx/fs/sda0 2>/dev/null || true; on -f rcc /usr/apps/mib2_ioc_flash reboot
```

## 14. Next vehicle gate

The next useful vehicle run is the guarded parity-drive candidate after current CI succeeds.

The drive test should answer:

1. Does CarPlay Maps remain visible for a sustained route?
2. Is motion smooth or still visibly low-cadence?
3. What are GEN2 source FPS and parity input FPS?
4. Are IDRs and non-IDR AUs both arriving?
5. Are P/B/I slice classes reaching successful MOST-block acceptance?
6. Are sequence gaps or recovery loops occurring?
7. What are `write_eagain`, `last_write_us` and `max_write_us`?
8. Does the route remain stable across static map periods, navigation start/stop and normal app
   transitions?
9. Does disconnect/stop/error always restore stock cleanly?

Do not claim AID presentation of every P/B-frame solely from accepted-output counters. Correlate the
telemetry with visible VC behavior.

## 15. Handoff rule

A future chat or contributor must start from this document plus the current branch HEAD and CI
artifact. Do not reconstruct the operating contract from older Auto-Direct scripts, MHI1Q notes, or
stale handoffs.

Before giving any vehicle command:

1. resolve current branch HEAD;
2. verify relevant parity CI success;
3. verify owner and bridge are the matched artifact pair;
4. verify exact MU1440 command/runtime rules in this document;
5. check live vehicle status before mutation;
6. use one bounded or until-stop step at a time;
7. preserve SD logging and rollback semantics.
