# MU1440 parity path: first visible AID10 image and transport findings — 2026-10-07

Target:

- Skoda Octavia III / MHI2 ER SKG13 P4526 MU1440
- AID10 Virtual Cockpit
- CarPlay AlternateScreen type 111
- ownership backend: process-local DisplayManager writev gate
- parity transport: complete M1AU -> PES -> MPEG-TS -> `/dev/mlb/isoTX2`

## Result

The clean-room Omonob790-functional-parity path has now produced a visible CarPlay navigation image
on the real AID10 through the complete custom media chain.

This is the first exact-vehicle positive result for:

```text
CarPlay Stream111
 -> GEN2 complete-AU/M1AU source
 -> direct-ts-parity
 -> writev-gate ownership
 -> /dev/mlb/isoTX2
 -> MOST
 -> AID10 visible image
```

The user reported that motion may still have been jerky. The run was too short to establish stable
motion quality because a local transport-deadline guard aborted the bridge shortly after visible
output began.

## Exact target evidence

The paired session/bridge build reached the QNX driver contract with:

```text
PARITY_PROCESS_IDENTITY_SELFTEST=PASS inherited_handle_signal_and_exit no_most_io
PARITY_DRIVER interface status=0 value=131073
PARITY_DRIVER packet_size status=0 value=188
PARITY_DRIVER block_count status=0 value=64
PARITY_DRIVER queue_flush status=25
PARITY_DRIVER start status=0 packets=64
PARITY_DRIVER queue_flush unsupported=ENOTTY continue=YES
PARITY_START input=tcp://127.0.0.1:19820 output=/dev/mlb/isoTX2 transport_bps=12288000 block=12032 pids=pat:0x0,pmt:0x10,pcr:0x1000,video:0x11
PARITY_RECOVERY_REQUEST_FAILED sequence=1 reasons=8
ERROR driver acceptance exceeded transport deadline
PARITY_DONE rc=1
```

A CarPlay image was visibly present in the AID10 before the local deadline abort.

## Driver FLUSH finding

On this exact MU1440:

```text
DRIVER_DCMD_FLUSH -> 25 (ENOTTY)
DRIVER_DCMD_START -> 0
```

Therefore FLUSH is not a mandatory supported operation for this target. The implementation now
tolerates only ENOTTY for the optional FLUSH operation while keeping interface, packet-size,
block-count and START failures fatal.

## Device pacing finding

The failing guard assumed that acceptance of each 12032-byte block should remain inside nominal
7.833-ms transport duration plus a fixed 40-ms lateness allowance.

The vehicle disproved that assumption as a safe fatal criterion: the driver path had already
produced a visible VC image when a block exceeded that software deadline.

The real QNX device path is therefore returned to the model used by the earlier parity design:

- exact 12032-byte physical writes;
- nonblocking device;
- bounded EAGAIN/write timeout;
- QNX driver backpressure owns device pacing;
- no invented fatal physical-drain deadline.

Regular-file test output may retain application pacing. Accepted-write time still does not prove
physical MOST drain time.

## Recovery-request finding

`reasons=8` is `ALT111_KF_BRIDGE_READY`, the startup IDR request.

The reason-aware recovery helper still uses POSIX `F_SETLK` and temp-file + `rename()`.
Both primitives are already target-qualified as unsuitable for the MU1440 `/tmp` /
`/dev/shmem` environment:

- `F_SETLK` -> ENOSYS
- native rename across the observed `/tmp` / `/dev/shmem` spelling boundary -> EXDEV

A compatibility fallback therefore uses the already-supported one-shot
`/tmp/mibr-alt111-keyframe-only` marker until the reason-aware helper is rewritten using the
qualified flat-shmem transaction primitives.

## Ownership and recovery

No stock infotainment process needs to be terminated for the writev-gate path.

The session owner temporarily suppresses the native DisplayManager payload writes and owns only its
own custom bridge process. Bound-process signalling exists solely so the session/watchdog can stop
that exact bridge before releasing the native route.

Observed failed-run recovery returned to:

```text
native gate state = 0
session state      = failed_stock
session pid        = none
bridge pid         = none
watchdog pid       = none
session lock       = none
M1AU marker         = absent
```

This is positive evidence for the current restore path.

## Long-run diagnostics

The next candidate adds guarded until-stop drive operation and switchable diagnostics.

Persistent drive evidence is SD-only:

```text
/net/mmx/fs/sda0/esd/carplay-test/logs/omonob790-parity-drive/
```

The supervisor must make the SD writable and verify a real write before starting a parity session.
It records source/GEN2 cadence, IDR counts, parity IDR/non-IDR AU progress, queue state, exact MOST
block counters and QNX write/backpressure timing. Raw status snapshots and compact statistics are
independently switchable for future use.

## What is proven / still open

Proven:

- complete custom path can reach the real AID10 with a visible CarPlay image;
- exact QNX driver readbacks and START contract above;
- FLUSH ENOTTY is non-fatal on this target;
- writev-gate/session ownership can reach custom payload and recover to stock after the observed
  failures.

Still open:

- sustained smooth motion;
- exact P/B/I slice-class presentation at the cluster;
- physical MOST drain timing versus write acceptance;
- decoder-side frame presentation telemetry;
- long-run reconnect/provider/view lifecycle behavior.
