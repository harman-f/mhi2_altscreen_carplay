> **Historical public implementation snapshot (last maintained 2026-10-02).** This file records the original reference-binary checkpoint; statements here such as “no HMI patch deployed” are dated, not the live October status. For current cross-module build/vehicle distinctions see [Integration status (2026-10-21)](INTEGRATION_STATUS_2026-10-21.md), [HMI/control architecture](../architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md), and [dated Final Drive evidence](MU1440_FINAL_DRIVE_LIVE_STATUS_2026-10-11.md). The released ZIP has **not** been silently promoted to newer branch artifacts.

# Historical public implementation status — 2026-10-02

> [!IMPORTANT]
> This page primarily tracks the **vehicle-proven/public implementation line**. Newer design-only work on source-timestamp transport, configurable keyframe policy, ownership A/B, HMI integration and steering-wheel control is summarized separately in the [current research preview](../research/CURRENT_RESEARCH_PREVIEW_2026-10-05.md). Those newer items are not vehicle-approved binaries yet.

Historical snapshot: **2026-10-02**

> The downloadable experimental GEN2 binary is intentionally **not the newest development build**.
>
> The public binary is a known, understandable vehicle-tested snapshot. Development has already moved
> several steps beyond it, but those newer changes are still being used to isolate lifecycle edge
> cases and are not published as the recommended binary yet.

## Where the project is now


### 2026-10-02 HMI / settings architecture

The MU1440 menu and ViewHandler architecture has now been mapped far enough to define a low-coupling
settings integration path.

Key result:

```text
top-level main menu
    = dynamic CIO / GridMenu system

application-local settings
    = generated state machine
      -> showView()
      -> LocalViewHandlerFactory
      -> JXE/ViewHandler
```

The preferred AltScreen UI direction is therefore **not** a new top-level application and not a
replacement of the large stock `Cmc` ViewHandler. The current design is a dedicated sibling settings
view entered from the existing FPK / Virtual Cockpit area.

The remaining HMI gate is additive loading, not menu discovery:

- verify exact MU1440 J9/XIP loader behavior;
- test the hypothesis that a new generated-package ViewHandler may be supplied through bootclasspath
  without first generating a new JXE;
- fall back to a small custom XIP/JXE overlay only if the bootclasspath path is not valid.

No vehicle HMI patch has been deployed yet. The first future HMI test is intentionally UI-only with a
dummy backend.

For the subsequent UI/controller direction see [current native HMI architecture](../architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md). This dated test report is historical.


#### HMI integration path update: WidgetFactory seam

A compatible VW implementation has clarified that a new HMI feature does not necessarily require a
new ViewHandler JXE at all. Its approach keeps stock view JXEs unchanged and overrides the generated
global `WidgetFactoryImpl` through a prepended boot JAR. Selected widget types are instantiated as
project subclasses which add their UI inside an existing stock view.

##### Exact MU1440 compile checkpoint

The externally reported App-Connect guard has now been recovered exactly from the MU1440
`Ssm_5458.jxe`: `SMI_SETUP_MAIN` contains the main content Container with target ID
`81171177`.

The relevant retained MU1440 factory/tree/pooling sources are byte-identical to the readable donor,
and a private compile-only two-class PoC now builds successfully against the exact retained MU1440
classpath with the target IBM J9 toolchain (classfile major 46).

No HMI vehicle patch has been run yet. Exact lifecycle analysis now shows that directly allocated project widgets can be owned by the guarded host Container when their controller/UI links and init/deInit sequence are handled explicitly.

A lower-risk staged vehicle proof is prepared before any child-tree mutation:

```text
P0 factory/guard compile                 complete
P1 existing-widget visible marker        built; not vehicle-run
P2 owned Button/TextArea subtree          next
P3 semantic AltScreen action              later
```


P1 is now minimized to one existing stock TextArea substitution only. The previously researched
Container subclass is **not** part of the first vehicle candidate. CI verifies that the candidate
factory differs from the normalized exact MU1440 stock factory only by
`TextArea -> MibrTextArea`, guarded to `SMI_SETUP_MAIN / targetId 92192369`.

No HMI vehicle test has been performed yet.

P1 uses a guarded stock TextArea subclass in the existing CarPlay row and changes only its visible
label. It does not change CarPlay transport or AltScreen state.


That path now has priority for the first MU1440 HMI experiment.

The key safety requirement is that the factory seam is global and pooled, so any custom widget
subclass must behave exactly like stock everywhere except one strictly identified host
(view + target/widget identity).

The first planned HMI vehicle PoC is therefore one guarded, UI-only injected control in an existing
stock settings view, with no CarPlay/runtime mutation and no new JXE.


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


### 2026-10-03: Omonob 790/791 artifact-path audit

A fresh function-level audit of the public Omonob/QCDWJ 790 and 791 producers shows that their hot media paths are effectively shared: AVCC/AES handling, CPRG ring publication, periodic/recovery keyframe logic and the downstream MOST bridge are not separate 791 implementations.

Both public profiles request a forced keyframe every 20 video frames. At a 40-fps source ceiling that is roughly a 0.5-second request cadence.

The most important static transport finding is in the shared `altscreen-most-bridge`: its low-latency recovery flushes a queue of individual TS packets when backlog exceeds roughly 1024 packets. That flush is not explicitly aligned to a PES/access-unit boundary, while the MOST writer independently drains 64-packet blocks. A recovery event can therefore theoretically discard the queued tail of a PES whose prefix has already moved toward the cluster.

This is a concrete mechanism for `corrupted/blocky picture -> fresh IDR -> clean picture`, but it is not yet proven to be the cause of any specific vehicle report.

Recommended discriminators are: disable permanent every-20-frame IDRs first, then test the same 791 geometry at 20 fps, and correlate visible artifacts with bridge `idr_max`, `queue_hi`, `latency-reset`, write-latency and `latency-resume-idr` telemetry.

See [Omonob/QCDWJ 790 vs 791 artifact-path audit](../research/OMONOB_790_791_ARTIFACT_AUDIT_2026-10-03.md).


### 2026-10-03: Minimal AID12 30-fps candidate plan

The Omonob/QCDWJ 790/791 audit is now followed by a deliberately minimal AID12 test strategy.

The first candidate should **not** rebuild the producer. It should patch the public 791 `core.so` in place so the ELF/ABI remains unchanged, with only:

```text
maxFPS: 40 -> 30
periodic forceKeyFrame divisor: 20 -> 30
```

At a 30-fps source ceiling this changes the periodic request cadence from roughly 0.5 s to roughly 1.0 s while leaving all startup/recovery-triggered keyframes intact.

The AID12 geometry remains `800x480`; the shared bridge/supervisor remain untouched.

Before any tester receives a binary, the exact instruction/file offsets must be pinned and a post-patch decompile must prove that the only semantic deltas are the intended `40->30` and periodic `20->30` changes. Original/patched hashes and a reversible patch manifest must accompany the candidate.

See [Omonob/QCDWJ 791 AID12 minimal 30-fps test plan](../research/OMONOB_791_30FPS_1S_IDR_TEST_PLAN_2026-10-03.md).
