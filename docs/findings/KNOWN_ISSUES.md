# Known issues and open work

Last updated: **2026-10-21** (original numbered findings retained as historical context).

## October 2026: additional observed issues

- Stream-111 source/session TEARDOWN/EOF and custom writer shutdown on lost native gate proof are distinct observed failure classes; neither alone proves the cause of reported USB/phone disconnects.
- Two parity supervisor instances were recorded in one installed boot. The owner lock prevented a second writer, but duplicate startup is still a defect.
- An October HMI field test did not establish effective VC application of five stored navigation presentation values. Stored/TEMP is not an owner-correlated ACTIVE acknowledgment.
- Long-session logged PTS-minus-PCR lead is not evidence of equivalent physically accumulating display delay. Clean fixture replay supported retaining the original compressed iPhone bitstream.
- External MU1409/Continental 790 success with an adapted different implementation is compatibility evidence, **not** qualification of this project's runtime on MU1409.

Details: [recovery/fault isolation](../testing/STREAM111_FAULT_ISOLATION_2026-10-21.md), [sanitized October evidence](OCTOBER_2026_VEHICLE_AND_TIMING_EVIDENCE.md) and [current integration status](../status/INTEGRATION_STATUS_2026-10-21.md).

This page describes problems that are real enough to matter but not yet stable enough to hide behind
a "release" label.

## 1. Frozen last frame after navigation/provider changes

### Symptom

The Virtual Cockpit can continue showing the last valid map frame after a route finishes, an app
stops navigating, or the navigation provider changes.

### What we know

A frozen image does not prove that Type 111 was destroyed.

In several relevant lifecycle paths the existing Type-111 session can remain alive while UI
ownership/presentation changes.

### Current suspects

- receiver-side UI selection not being refreshed;
- navigation ownership release/acquire ordering;
- `suggestUI([])` withdrawal followed by the next provider;
- no fresh H.264 access units after ownership transition;
- fresh AUs but no new usable config/IDR boundary;
- consumer generation waiting for re-priming.

### Current diagnostic

Classify in this order:

```text
Did Type 111 actually restart?
      │
      ├─ yes -> new generation / rebind
      │
      └─ no
          │
          ├─ no fresh H.264 -> UI/ownership/source activation
          │
          └─ fresh H.264
               │
               ├─ no config+IDR -> resync/priming
               │
               └─ valid delivered video -> only then revisit VC/MOST presenter
```

## 2. Provider switch is not yet deterministic

Provider switching has worked, including transitions that recover live video without a full
head-unit restart, but behavior is not yet consistent enough to call stable.

The older public experimental snapshot may require:

- CarPlay cable reconnect; or
- explicit same-session reacquire.

Current development is further ahead than the published binary.

## 3. suggestUI is not showUI

The project previously treated some UI events too much like stream lifecycle events.

Current understanding:

```text
suggestUI(candidate URLs)
    !=
showUI(selected URL)
    !=
new Type-111 SETUP
```

The receiver's role between suggestion and actual presentation remains an active area.

## 4. suggestUI([]) / navigation release

A clean route finish can withdraw the suggested cluster UI set.

The difficult case is what happens immediately afterwards:

```text
current provider
  -> suggestUI([])
  -> navigation ownership release
  -> next provider requests navigation
  -> existing secondary display remains
  -> receiver and sender must converge on the new presentation
```

The exact ordering and which receiver action is mandatory are still under vehicle test.

## 5. forceKeyFrame is a recovery primitive, not a new session

A keyframe request can restart the current screen bitstream.

It should not be confused with creating a new Type-111 stream.

Current development uses `forceKeyFrame` as part of bounded same-session recovery testing.

## 6. VideoConfig / IDR ordering

The current implementation has become stricter about codec state because app transitions can expose
race conditions.

Important rule:

```text
consumer must not treat arbitrary video frames as valid
before a usable VideoConfig / codec generation exists
```

The GEN2 work includes stronger:

- VideoConfig tracking;
- complete access-unit validation;
- config + IDR priming;
- generation fencing;
- bounded queues.

These changes are newer than the first published experimental binary.

## 7. Type 110 vs private Type 111 lifecycle

The main CarPlay screen (110) and the project's secondary-display receive path (111) should not be
blindly coupled.

Newer development has explicitly separated parts of the private 111 lifecycle from unrelated stock
110 teardown behavior.

This area is still being validated across real disconnect/reconnect cases.

## 8. ViewArea remains experimental

Current public support should not be interpreted as dynamic VC layout support.

Open questions include:

- exact area definitions for different cluster layouts;
- safe-area interaction;
- response to driver-selected VC view changes;
- cross-brand differences;
- transition timing.

## 9. HID / knob input intentionally deferred

The current target does not require us to claim a complete secondary-display input-device model.

HID/knob support is intentionally deferred until the receiver contract is proven rather than copied
from unrelated implementations.

## 10. Cross-brand support is not yet proven

The project goal includes Škoda, SEAT/CUPRA and Volkswagen MHI2.

The current hard vehicle evidence is still based on the first Škoda MU1440 reference system **with the project's AID10-class 10.x-inch MQB Virtual Cockpit target**.

Do not assume that:

- offsets;
- AirPlay ABI;
- DisplayManager behavior;
- Java classes;
- ViewArea geometry;
- startup scripts;
- instrument-cluster generation, native geometry or MOST/DCIVIDEO behavior

are identical on another train or another AID generation.

Compatibility should be gated by exact firmware/component evidence.

## 11. No public screenshots by design

The project currently avoids publishing vehicle/navigation screenshots.

Navigation imagery can reveal:

- home/work location;
- recent destinations;
- street names;
- route history;
- other identifying context.

Technical proof is therefore documented primarily through hashes, logs, state transitions and
architecture diagrams rather than location-bearing screenshots.

## 12. No finished SD-card installer

This remains deliberate.

The public workflow is currently for developers with existing SSH access.

A future installer should only be built once:

- compatibility gates are clear;
- rollback is reliable;
- lifecycle behavior is stable;
- third-party licensing/provenance is clean;
- the underlying changes no longer need active engineering visibility.
