# Current development status

Last updated: **2026-10-07**

> The downloadable experimental GEN2 binary is intentionally **not the newest development build**.
>
> The public binary is a known, understandable vehicle-tested snapshot. Development has already moved
> several steps beyond it, but those newer changes are still being used to isolate lifecycle edge
> cases and are not published as the recommended binary yet.

## MU1440 parity-drive vehicle milestone — 2026-10-07

The current draft branch has now produced a **visible CarPlay image in the real AID10 through the
clean-room parity path** after native ownership takeover. The matched owner/bridge pair passed the
QNX bound-process identity self-test, exact driver readbacks and START. The exact MU1440 reports
`ENOTTY (25)` for the optional queue-FLUSH command while START succeeds; only this exact FLUSH
result is tolerated.

The first visible run then exposed an application-side regression rather than a driver failure: an
artificial 40-ms transport-lateness deadline aborted a valid driver-backpressured `isoTX2` path.
The device path now trusts bounded QNX backpressure (500-ms write/EAGAIN limit) and records real
write latency instead of inventing a physical-drain deadline.

The new guarded parity-drive runtime supports true until-stop operation, boot autostart, token-bound
stop and independent watchdog recovery without terminating stock DisplayManager,
`smartphone_integrator` or `dio_manager`. Native DisplayManager payload is suppressed only by the
qualified writev gate and is restored on every normal/error exit.

Drive evidence is SD-only and fail-closed: the supervisor must successfully remount
`/net/mmx/fs/sda0` writable and pass a write test before it starts custom ownership. Live status and
persistent statistics are independently switchable with temp/persistent/default layering. Persistent
telemetry includes measured/derived source FPS, IDR/non-IDR counts, P/B/I slice classification,
post-write AU completion, MOST blocks, EAGAIN and write-latency metrics.

See [the exact 2026-10-07 vehicle/runtime contract](../testing/MU1440_PARITY_DRIVE_VEHICLE_CONTRACT_2026-10-07.md).
That document is the regression authority for MU1440 shell/process-control, SHMEM and matched-binary
rules. Older Auto-Direct and MHI1Q command examples must not override it.

## MU1440 master candidate — 2026-10-05

The current development line is draft [harman-f/mhi2_altscreen_carplay#15](https://github.com/harman-f/mhi2_altscreen_carplay/pull/15), branch `codex/omonob790-regression-hardening-v1`. Keep it unmerged. Its exact source identity is recorded in each generated candidate manifest; the historical vehicle PoC below does not qualify this new combination.

The code now includes a shared settings registry, target-qualified SHMEM transactions and crash reconciliation, source-frame/source-time keyframe policy, generation-bound recovery, frozen negotiated geometry/UUID/source version, and a native owner with bound process handles and an independent watchdog. On the exact MU1440, `/tmp` aliases `/dev/shmem`; `F_SETLK` and native temp+rename publication are not valid runtime primitives there, so current owner/status paths use O_EXCL inode ownership plus direct truncate/write where appropriate. The separate native guard runs in DisplayManager; GEN2 runs in smartphone_integrator. Initial ownership is `writev_gate`. The DMDT backend is a routing probe that starts no custom payload until independently qualified on the target.

Master-specific shell adapters use the same native settings helper. SafeArea, display and navigation batches commit together; stored values are not reported as runtime completion. The master installer backs up the exact boot command, all affected native components and scripts, and all 13 temporary configuration files, including absence. A rollback barrier prevents GEN2 from consuming a partially restored set until normal reboot. SD vehicle wrappers use the existing M.I.B. media bootstrap and MU1440 `tee` logger; every entry point establishes the proven target environment itself.

Host regressions now include real moving H.264 with predictive pictures, comparing all 40 decoded frame hashes before and after TS transport. This establishes codec continuity on the host. Physical MOST ownership/drain, loaded ABI coverage, QNX process identity self-test and visible predictive frames remain hardware acceptance gates. See [the exact runtime and regression contract](../architecture/MU1440_PARITY_REGRESSION_CONTRACT.md).

The earlier ENVFIX2 keyframe/standstill observation remains a separate, unmeasured hardware failure. The candidate does not retrospectively establish its cause. Java FPS-policy work remains deferred for the first media/ownership proof.

## Where the project is now

### 2026-09-29 vehicle PoC milestone

The Škoda MU1440 reference vehicle has now shown **live moving CarPlay auxiliary-navigation video**
in the Virtual Cockpit with all three tested providers: **Apple Maps, Google Maps and Waze**.

The working media path is the real Type-111 H.264 -> direct MPEG-TS -> `isoTX2` -> MOST path.
Public photos/videos are linked from
[MU1440 CarPlay Stream-111 vehicle PoC](../findings/MU1440_CARPLAY_STREAM111_POC_2026-09-29.md).

This closes the basic end-to-end visual PoC for the reference target. It does **not** close SafeArea /
ViewArea geometry, reduced-view composition, lifecycle hardening or the observed real-stream cadence/jitter question.

### 2026-09-29: end-to-end MU1440 visual PoC confirmed

The Škoda MU1440 reference vehicle now has direct visual proof of the complete experimental path with
three independent CarPlay navigation providers:

- **Apple Maps**
- **Google Maps**
- **Waze**

All three produce live, moving auxiliary-navigation imagery in the Virtual Cockpit through the current
Stream-111 -> H.264 -> MPEG-TS -> MOST route. The providers visibly render different cluster-native
layouts, which is useful evidence that the result is not a static injected bitmap or synthetic test
pattern.

Public, privacy-reduced photo/video evidence is documented in
[MU1440_CARPLAY_NAVIGATION_POC_2026-09-29.md](../findings/MU1440_CARPLAY_NAVIGATION_POC_2026-09-29.md).

The remaining work is now predominantly integration and polish: SafeArea/ViewArea behavior, a runtime
switch between full-map and reduced/tacho layouts, provider/lifecycle edge cases, and frame-pacing
analysis. The public MP4 files are re-encoded proof derivatives and must not be used for timing or
frame-rate measurements.

The project has progressed beyond the initial proof-of-concept stages.

The following architecture is established on the Škoda MU1440 reference system:

```text
CarPlay navigation
      │
      ▼
Auxiliary / ScreenAlt
      │
      ▼
Stream type 111
      │
      ▼
H.264
      │
      ▼
direct MPEG-TS remux
      │
      ▼
/dev/mlb/isoTX2
      │
      ▼
MOST150
      │
      ▼
Virtual Cockpit
```

The native map producer can be suppressed and restored without killing the whole DisplayManager
process, and the stock map can be recovered.

## What already works in the current development line

These points are beyond the earliest public PoCs:

- live CarPlay navigation video has been shown in the real Virtual Cockpit;
- the secondary Type-111 stream can be received and converted to the direct VC transport path;
- native-map takeover and STOCK recovery work;
- navigation start/stop can be handled automatically in the current development line;
- the Direct-VC bridge can be started/stopped by supervisor/watchdog logic rather than by a manual
  one-shot command;
- navigation-provider switching is no longer purely theoretical and has worked in vehicle testing;
- at least some provider transitions have completed without requiring a full head-unit reboot;
- a cable reconnect is a known recovery path for the older published snapshot;
- newer development builds include explicit same-session reacquire logic and stronger stream/config/
  IDR generation handling.

This does **not** mean all lifecycle transitions are solved.

## The current engineering problem

The main remaining problem is not the MOST video path.

It is the interaction between:

```text
CarPlay navigation ownership
        +
suggestUI / showUI / stopUI
        +
SecondDisplayMode
        +
existing Type-111 stream lifetime
        +
H.264 config / IDR refresh
        +
receiver-side VC ownership
```

A provider change can occur while the existing Type-111 transport remains alive.

That means this visual symptom:

```text
last navigation frame remains frozen in the VC
```

does **not** automatically mean:

```text
Type 111 has been torn down
```

The current work is classifying exactly which layer failed.

## Important lifecycle finding

Current reverse engineering strongly indicates that normal navigation/provider changes should usually
reuse the existing secondary-screen stream.

The expected model is closer to:

```text
existing Type-111 session
       │
       ├── navigation owner changes
       ├── suggestUI changes
       ├── display mode changes
       ├── ViewArea may change
       └── sender presentation may need reacquire/keyframe
```

rather than:

```text
provider changed
    -> destroy Type 111
    -> build a completely new Type 111 session
```

This distinction is now driving the current test strategy.

## Current recovery / diagnostic direction

The newer development line can explicitly test a bounded same-session recovery sequence:

```text
stopUI
   ↓
showUI(selected cluster URL)
   ↓
forceKeyFrame
```

The goal is to determine whether the sender is merely waiting for presentation/UI ownership to be
reasserted, or whether a deeper stream/consumer generation change occurred.

## Current instrumentation

Recent development work has added instrumentation for:

- `suggestUI` lifecycle;
- PlatformControl commands;
- ScreenAlt URL roles;
- Type-111 stream/session generations;
- VideoConfig arrival;
- SPS/PPS/IDR state;
- consumer priming;
- delivered access-unit counters;
- source heartbeat;
- receiver command completion;
- STOCK/DIRECT ownership state.

The purpose is to stop debugging a frozen VC image as a single symptom and instead identify the exact
layer at which progress stopped.

## Provider switching

Current status should be described as:

**works in some tested transitions, not yet deterministic enough for a stable release.**

Observed useful behavior includes:

- live Apple Maps in the VC;
- switching away from one navigation provider and obtaining live video again after reconnect/reacquire;
- at least one successful Apple Maps -> another provider transition without unplugging;
- improved current development behavior around automatic navigation start/stop and provider changes.

Still under investigation:

- stale last-frame cases after navigation app termination or ownership change;
- whether the receiver must explicitly reselect UI in every relevant transition;
- exact ordering of `suggestUI([])`, ownership release and the next provider's presentation;
- provider-specific differences between Apple Maps, Google Maps and Waze;
- when `forceKeyFrame` is sufficient and when a stronger consumer reset is needed.

## ViewArea / cluster layout

ViewArea work exists, but it is intentionally not considered finished.

The project already has evidence that ViewArea belongs to the existing secondary-display session and
does not require a new Type-111 stream.

Remaining work includes:

- mapping actual VC presentation areas;
- reacting to VC layout/view changes;
- defining safe-area behavior;
- deciding whether receiver-driven or vehicle-state-driven selection is the better abstraction;
- testing across different clusters/brands.

## Why the published binary is older than this document

The project intentionally separates:

```text
current research HEAD
        !=
recommended experimental binary
```

A binary is promoted only when it represents a useful, explainable checkpoint.

The current downloadable GEN2 snapshot was chosen because:

- live secondary-screen video was proven;
- its failure mode is known;
- its source is published;
- it is unstripped and inspectable;
- it provides a useful baseline for other developers.

Newer internal development may be functionally ahead while still being a worse public reference
because several variables are changing at once.

## What help is most useful

The project is especially interested in developers/testers who can contribute one of these:

- another SSH-accessible Škoda/SEAT/VW MHI2 system;
- another digital-cluster/Virtual-Cockpit variant;
- CarPlay/AirPlay receiver knowledge;
- QNX/MOST/DisplayManager expertise;
- repeatable traces of Apple Maps / Google Maps / Waze provider transitions;
- additional reverse engineering of ScreenAlt UI-control semantics;
- safe ViewArea/layout observations.

A useful contribution does not require solving the whole stack. A precise trace that closes one
state transition is valuable.


## 2026-09-27 vehicle milestone

A controlled vehicle run materially narrowed the lifecycle problem.

The failure was reproduced in this form:

```text
Stream 111        still streaming
source AUs        still increasing
direct remux      still running
MOST blocks       still increasing
write errors      0
VC                frozen on an old frame
```

Two independent manual same-session recoveries then produced a fresh source IDR and immediately
restored moving VC video without changing the stream, codec or consumer generation.

After enabling the D2 automatic keyframe policy, the tested Apple Maps / Google Maps / Waze
navigation start/stop/provider transitions remained usable without another manual recovery.

This changes the leading diagnosis from "provider switch may require stream rebuild" to:

> **the sender can keep the existing Stream-111 transport alive while the downstream VC presentation
> still needs a fresh decodable random-access point after lifecycle/composition transitions.**

The current D2 watchdog deliberately forces an IDR after one second without a newer source IDR.
That behavior is functionally useful but too aggressive for a final policy: the next tuning step is
to make watchdog activity event-scoped rather than permanently periodic.
