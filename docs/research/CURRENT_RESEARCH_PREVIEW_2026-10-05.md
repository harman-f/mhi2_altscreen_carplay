# Historical research preview — 2026-10-05

> **Archived dated preview.** More recent [integration status](../status/INTEGRATION_STATUS_2026-10-21.md), [HMI/control](../architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md), [vehicle evidence](../findings/OCTOBER_2026_VEHICLE_AND_TIMING_EVIDENCE.md), and [R12–R16 research index](README.md) supersede the relevant cross-track status. Historical implementation proposals below do not establish the current installed state.

**Status:** public research preview / mixed evidence levels  
**Reference target:** `MHI2_ER_SKG13_P4526_MU1440` / AID10-class Virtual Cockpit

> [!IMPORTANT]
> This page intentionally publishes useful research **before the next implementation is vehicle-validated**.
> It distinguishes vehicle-proven behavior from exact-target static analysis, offline/build results and design work.
> No new binary described here should be assumed vehicle-ready unless the relevant document explicitly says so.

## Evidence labels

| Label | Meaning |
| --- | --- |
| **VEHICLE-PROVEN** | observed on the exact MU1440/AID10 reference vehicle |
| **EXACT-TARGET STATIC** | recovered from the exact MU1440 software/J9/JXE/binary baseline, but not exercised in the vehicle |
| **OFFLINE / BUILD-PROVEN** | compiled, parsed or regression-tested off-target |
| **DESIGN** | reviewed implementation contract, not yet implemented/validated end-to-end |
| **OPEN** | still requires target evidence |

The main purpose of this page is to keep the current research reusable without making contributors repeat the same reverse engineering.

---

## 1. Media/timing: next-generation Classic111 path

### What remains vehicle-proven

The basic direct path is already proven:

```text
CarPlay Type-111 H.264
 -> MPEG-TS
 -> exact 64 x 188-byte / 12032-byte writes
 -> /dev/mlb/isoTX2
 -> MOST150
 -> Virtual Cockpit
```

Live moving Apple Maps, Google Maps and Waze have all been shown through this family of paths.

The process-local DisplayManager `writev` gate is also vehicle-proven as a reversible way to stop stock
`isoTX2` payload from mixing with the custom writer while keeping DisplayManager alive.

### New media architecture under review

Recent comparator work and exact-target telemetry led to a stricter media model:

```text
complete CarPlay AU
  + source ordinal
  + exact 32.32 source timestamp
        |
        v
one complete AU -> one PES
        |
        v
source timestamp -> 90-kHz PTS
        |
        v
continuous null-filled MPEG-TS
        |
        v
12.288-Mbit/s physical transport model
        |
        v
12032-byte writes
```

Key design points:

- complete AU identity must survive; do not throw it back into a generic raw-H.264 parser;
- presentation timing comes from the preserved source timestamp, not `frame_no / configured_fps`;
- negotiated `maxFPS`, observed source FPS, source timestamp, keyframe recovery and physical TS/PCR timing are separate domains;
- the proposed transport topology uses PAT `0x0000`, PMT `0x0010`, PCR `0x1000`, H.264 `0x0011`;
- predictive-chain recovery must never truncate a PES that already started leaving the queue;
- the new design intentionally does not reproduce a comparator's packet-level mid-PES flush behavior.

The current hardened implementation work lives in draft PR #15. Its host/QNX regression suite has passed,
but the extended design below is **not yet fully implemented and is not vehicle-ready**.

### Keyframe policy — now treated as a runtime policy

The public Free790-style comparator behavior remains useful as an exact reference:

```text
every 20 source AUs -> request fresh keyframe
```

The project no longer treats that as the only possible production policy.

The reviewed design calls for runtime-selectable behavior:

```text
source_frames
  interval_frames = configurable
  exact reference start = 20

source_time
  interval_ms = configurable
  measured from the preserved source timestamp

event_only
  no periodic request

off
  no periodic request
```

Independent event-driven reasons remain available, including:

```text
bridge_ready
showui
source_gap
latency_recovery
lifecycle_reset
manual
periodic_frames
periodic_time
```

A successful/current `showUI` completion should request a fresh keyframe. That behavior is also present in the
public comparator lineage.

Important distinction:

```text
20 source frames != fixed time
```

If CarPlay reduces the real AU cadence on a quiet map, a frame-count policy naturally stretches in wall time.
The `source_time` policy exists specifically so a two-second request remains a two-second source-time policy.

### Ownership: routing is not the same thing as payload arbitration

A second recent correction is important for contributors.

The comparator reference uses DMDT routing equivalent to:

```text
dc 72
sc 4 72
...
dc 70 33
sc 4 70
```

On the exact MU1440, however, static analysis proves DMDT context/displayable routing but does **not** by itself
prove that the native DisplayManager encoder/TX path has stopped writing to `isoTX2`.

Therefore the planned vehicle A/B keeps two distinct backends:

- `writev_gate` — vehicle-proven payload arbitration baseline;
- `dmdt_reference` — comparator-compatible routing experiment, not yet accepted as exclusive payload ownership.

A DMDT run must first prove native TX quiescence before custom payload is allowed. A successful command exit or
a 500-ms delay is not enough.

No design should permit native and custom MPEG-TS to mix.

---

## 2. ViewArea/SafeArea and source persona

The next settings contract carries two advertised ViewArea/SafeArea pairs so the active area can be changed
inside an existing Stream-111 session.

Current direction:

```text
advertise area 0 + safe area 0
advertise area 1 + safe area 1
        |
        v
select one area at runtime
```

Automatic coupling to the actual Virtual Cockpit layout/steering-wheel view is deliberately deferred until
both layouts are calibrated and stable.

The CarPlay `sourceVersion` / compatibility persona is also intended to become runtime-configurable.
The public Free790-compatible `950.7.1` persona remains an exact named reference. Changing sourceVersion
requires CarPlay renegotiation/reconnect; it is not a live keyframe/FPS setting.

---

## 3. Settings/HMI contract

The intended source of truth remains file-backed and deliberately simple:

```text
/tmp/<basename>           temporary override
/mnt/app/root/<basename> persistent override
profile/default           fallback
```

Precedence:

```text
temporary > persistent > profile/default
```

The HMI should sit above one validated settings/apply layer rather than directly editing arbitrary files,
remounting filesystems or restarting projection processes.

A future local IPC helper can be useful for atomic HMI requests and status/ack handling, but it should remain
a frontend to the same registry — not a second configuration store.

No general active TCP/UDP settings daemon exists in the current Classic111 implementation. Historical local
TCP control found in unrelated/older implementations is not treated as the current project contract.

---

## 4. MU1440 HMI/menu research

Detailed public write-up:

[Updated native HMI and single-authority controller architecture](../architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md)

### Main menu vs local settings

The stock HMI uses two different mechanisms:

```text
top-level main menu:
CIO intents -> GridMenuAction -> persisted CIO order -> Sgm -> dispatch

application-local settings:
state machine -> showView(name) -> ViewHandler -> widgets/events/backend
```

That matters because a stock-looking AltScreen settings UI does **not** need a new top-level application.

### Exact target views

Exact-target static analysis identified:

- `Cmc` — Car/CarComputer view containing the Cockpit/FPK path;
- `Ssm_5458` — Smartphone Integration / App-Connect setup;
- `Cm_0409` — active CarPlay canvas/bridge view.

Configuration and active projection are therefore already separate stock HMI concerns.

### Strongest current injection seam

The exact `Ssm_5458` ViewHandler contains:

```text
View "SMI_SETUP_MAIN"
  targetId 24786208
  |
  +-- Container
      targetId 81171177
      |
      +-- WidgetList
          targetId 47234883
```

Classification:

`EXACT-TARGET STATIC`

The same host pair was independently useful in a compatible public VW implementation, which makes it an
especially useful first PoC anchor.

### WidgetFactory approach

A lower-complexity HMI approach is now preferred before generating a new JXE:

```text
stock ViewHandler JXE
 -> stock tree builder
 -> bootclasspath-overridden WidgetFactoryImpl
 -> strictly guarded project widget subclass
 -> small project-owned subtree made from stock widgets
```

The exact MU1440 factory/tree/pooling seam has been checked statically and a two-class compile-only PoC has
built against the retained target Java/J9 classpath.

Classification:

`OFFLINE / BUILD-PROVEN, NOT VEHICLE-PROVEN`

Safety requirement: the factory seam is global, so the replacement subclass must be completely stock-compatible
outside the exact target view/targetId guard and its constructor must remain side-effect free.

Preferred proof order:

1. harmless/dummy injection into the exact App-Connect setup host;
2. validate pooling/back/leave/re-enter behavior;
3. then decide whether final UX remains under App-Connect or moves to the Cockpit/FPK path;
4. only after that consider a dedicated sibling ViewHandler.

A new sibling ViewHandler is structurally plausible but remains less proven than the existing-view factory seam.

---

## 5. Steering-wheel / hardkey research

Detailed public write-up:

[MU1440 steering-wheel / hardkey API audit](MU1440_BUTTON_INPUT_API.md)

Exact-target Java analysis confirms the substrate needed for passive/additive input handling:

```text
ASLSystemAPI.addKeyListener(...)
ASLSystemAPI.createAndSubmitHardkeyEvent(...)

KeyAdapter.onPressed(...)
KeyAdapter.onReleased(...)
KeyAdapter.onLongPressed(...)

DoublePressKeyAdapter.onDoublePressed(...)
DoublePressKeyAdapter.onSingleReleased(...)
```

The exact MU1440 double-press helper contains a 500-ms single/double classifier.

Known target mappings include examples such as PTT/voice key ID 15, mute 88 and smartphone/App-Connect 114.

What this does **not** prove yet is the final steering-wheel control chosen for AltScreen.

Preferred order:

```text
passive/additive listener
 -> capture the real physical button/key tuple
 -> verify short/long/double behavior
 -> bind a project action
 -> only then consider synthetic remapping
```

Potential project actions include:

- ViewArea/SafeArea preset selection;
- navigation composition/profile selection;
- diagnostics;
- later HMI-configured action mapping.

Do not infer a VIEW/JOKER key from a symbolic name without target traces.

---

## 6. What is intentionally not published as "working" yet

The following remain research/design items:

- the new source-timestamp parity transport as a vehicle-approved replacement;
- DMDT-only ownership on the exact MU1440;
- runtime-configurable frame/time keyframe policy implementation;
- the two-ViewArea production profile;
- HMI WidgetFactory injection on the actual unit;
- final steering-wheel button binding/remapping;
- new binaries built from the extended master design.

The public vehicle-proven checkpoints remain the appropriate binaries until those items pass their own target tests.

---

## 7. Public prior art / thanks

Useful public work that materially reduced duplicated research includes:

- [omonob/MHI2-Carplay-Maps](https://github.com/omonob/MHI2-Carplay-Maps) — public MU1440/790/791 AltScreen comparator behavior;
- [y-batsianouski/mib2-voicecontrol-button-patch](https://github.com/y-batsianouski/mib2-voicecontrol-button-patch) — MIB2 ASL steering-wheel/hardkey implementation lead;
- [luka-dev/mib2q-carplay-rgi](https://github.com/luka-dev/mib2q-carplay-rgi) — CarPlay/RGI and MIB2 Java/JXE groundwork;
- [luka-dev/jxe2jar](https://github.com/luka-dev/jxe2jar) — J9/JXE reconstruction tooling;
- [luka-dev/qnx65-armv7-toolchain](https://github.com/luka-dev/qnx65-armv7-toolchain) — reproducible QNX ARMv7 build environment;
- [OneB1t/VcMOSTRenderMqb](https://github.com/OneB1t/VcMOSTRenderMqb) — MQB Virtual Cockpit / MOST rendering groundwork;
- [jilleb/mib2-toolbox](https://github.com/jilleb/mib2-toolbox) — public MIB2 Java/HMI/runtime precedent;
- the additional projects catalogued in [Public references](PUBLIC_REFERENCES.md) and [Acknowledgements](../../ACKNOWLEDGEMENTS.md).

These references support architecture and comparison. Exact MU1440 claims in this repository remain separately
classified and are not promoted to vehicle proof merely because a similar public implementation exists.
