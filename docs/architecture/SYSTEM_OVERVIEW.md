# System overview — CarPlay AltScreen to MHI2 Virtual Cockpit

> **Original system model (2026-09-26):** foundational description of the media/control separation; the exact current component/owner design, HMI and optional vehicle data are defined in [module boundaries](MODULE_BOUNDARIES_AND_PORTABILITY.md) and [the architecture index](README.md). Vehicle-tested results and published-source coverage are separately maintained. This page's historical "trying to reproduce" language is not an assertion that the September PoC is still the current milestone.
>
> This document starts at the system level. The control-plane details are expanded in
> [SCREENALT_CONTROL_PLANE.md](SCREENALT_CONTROL_PLANE.md).

## 1. The problem in one picture

The project is trying to reproduce the complete **CarPlay secondary-display navigation path** on
Volkswagen Group MHI2 systems and present that video in the MQB Virtual Cockpit.

The important word is **complete**.

Getting H.264 pixels from the iPhone into the cluster is only one half of the problem. The receiver
also has to participate in CarPlay's auxiliary-screen lifecycle: advertise the display, expose the
right capabilities, track the active UI context, react to navigation ownership changes, request the
correct presentation and keep the existing stream synchronized.

```text
┌────────────────────────────── iPhone ──────────────────────────────┐
│                                                                   │
│  navigation app / CarPlay scene                                   │
│             │                                                     │
│             ├────────────── UI / ownership state ──────────────┐   │
│             │                                                  │   │
│             └── Auxiliary / ScreenAlt video                    │   │
│                         │                                      │   │
│                         ▼                                      │   │
│                   Type-111 H.264                               │   │
│                                                                │   │
└─────────────────────────┬──────────────────────────────────────┼───┘
                          │                                      │
                     media plane                           control plane
                          │                                      │
                          ▼                                      ▼
┌────────────────────────────── MHI2 ────────────────────────────────┐
│                                                                   │
│  AirPlay / CarPlay receiver                                      │
│       │                                                           │
│       ├── ScreenAlt/Auxiliary display advertisement               │
│       ├── URL/UI context negotiation                              │
│       ├── navigation ownership/mode state                         │
│       ├── ViewArea / display-mode control                         │
│       └── Type-111 receive/decrypt                                │
│                         │                                         │
│                         ▼                                         │
│                 H.264 access units                                │
│                         │                                         │
│                         ▼                                         │
│                  direct TS remux                                  │
│                         │                                         │
│                         ▼                                         │
│                  MPEG-TS / MOST150                                │
│                         │                                         │
│                         ▼                                         │
│               Virtual Cockpit video route                         │
│                         ▲                                         │
│                         │                                         │
│                stock map/video producer                           │
│                         ▲                                         │
│                         │                                         │
│              Java / DSI display policy                            │
│                                                                   │
└─────────────────────────┬─────────────────────────────────────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Virtual Cockpit  │
                 │ map / view area  │
                 └──────────────────┘
```

The media path is already proven end-to-end on the current Škoda MU1440 reference platform: Apple
Maps has been rendered visibly in the real Virtual Cockpit through the direct Type-111 -> H.264 ->
MPEG-TS -> MOST path.

The remaining work is mainly about **lifecycle and ownership correctness**.

---

## 2. Two planes: media and control

The project deliberately separates the system into two planes.

### 2.1 Media plane

The media plane carries the navigation image.

```text
CarPlay Auxiliary / ScreenAlt
        │
        ▼
AirPlay screen stream type 111
        │
        ▼
Screen encryption / session handling
        │
        ▼
H.264 access units
        │
        ▼
direct-ts-remux
        │
        ▼
MPEG-TS
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

On the current target this path is no longer theoretical. It is the proven baseline and should not
be redesigned without contradictory vehicle evidence.

### 2.2 Control plane

The control plane decides **whether the secondary display exists, which UI is intended for it, who
owns it and when the current stream needs to be refreshed**.

Relevant concepts include:

```text
receiver display/capability advertisement
              │
              ├── ScreenAlt / Auxiliary screen
              ├── type 111
              ├── initial URL
              ├── ViewArea(s)
              └── optional input/HID capabilities

iPhone navigation state
              │
              ├── navigation ownership
              ├── modesChanged / app state
              └── suggestUI([...])

receiver-side UI selection
              │
              ├── showUI
              ├── stopUI
              ├── changeModes / SecondDisplayMode
              ├── ViewArea changes
              └── forceKeyFrame
```

A major lesson from the research is:

> **A live Type-111 socket is not the same thing as correct CarPlay UI ownership.**

The stream can still exist while the wrong app/context is selected, while the sender is no longer
producing fresh content for the intended context, or while the receiver needs to refresh the
existing presentation.

---

## 3. CarPlay secondary display lifecycle

Current sender-side reverse engineering supports a persistent Auxiliary/ScreenAlt object that is
created as part of endpoint feature/stream setup.

A normal navigation app change is **not** itself a reason to destroy and recreate Type-111.

```text
CarPlay endpoint/session
        │
        ├── create Auxiliary/ScreenAlt stream
        │      └── Type 111
        │
        ├── navigation starts
        │      ├── UI candidates change
        │      └── ownership/mode state changes
        │
        ├── navigation provider changes
        │      ├── UI candidates may change
        │      ├── ownership changes
        │      └── same Type-111 generation normally remains
        │
        └── actual endpoint topology/session change
               └── only here may 111 really be torn down/recreated
```

### Real Type-111 generation boundaries

The implementation should only treat the stream as a new generation when there is actual transport
or session evidence, for example:

- a partial AirPlay TEARDOWN for type 111;
- a fresh type-111 SETUP;
- changed stream connection identity;
- changed session generation;
- socket/session death;
- another explicitly observed endpoint-topology change.

Normal app ownership, `suggestUI`, SecondDisplayMode or ViewArea transitions should not be converted
into synthetic teardown/SETUP cycles.

---

## 4. Cluster UI contexts

CarPlay exposes multiple logical instrument-cluster contexts.

Current mapping:

| URL | Working interpretation |
| --- | --- |
| `maps:/car/instrumentcluster` | generic/root instrument-cluster context |
| `maps:/car/instrumentcluster/map` | persistent map presentation |
| `maps:/car/instrumentcluster/instructioncard` | transient maneuver/instruction-card presentation |

Typical sender-side state:

```text
navigation active
  -> suggestUI([base, map])

maneuver card visible
  -> suggestUI([instructioncard, map, base])

maneuver card hidden
  -> suggestUI([map, base])

trip finish/cancel
  -> suggestUI([])
```

These are **UI roles inside the existing secondary-display architecture**, not three different
screen streams.

---

## 5. Effective UI capability is an intersection

The iPhone does not blindly assume that every requested cluster context is available.

The effective candidate set is the intersection of:

```text
app/provider requested UI contexts
                ∩
iOS/session cluster contexts
                ∩
receiver-advertised AltScreen contexts
                │
                ▼
          effective URLs
                │
                ▼
             suggestUI
```

This makes receiver advertisement important. A receiver can have a working type-111 media path and
still fail higher-level CarPlay behavior if the UI/capability surface is incomplete or inconsistent.

---

## 6. Current MU1440 receiver profile

The current first-generation GEN2 work deliberately uses a conservative, no-HID single-view
secondary-display profile.

Reference engineering profile:

```text
type=111
maxFPS=30
features=0
primaryInputDevice=<absent>
widthPixels=1010
heightPixels=376
widthPhysical=200
heightPhysical=74
initialURL=maps:/car/instrumentcluster
viewAreas=1
initialViewArea=0
drawUIOutsideSafeArea=false
viewAreaTransitionControl=false
```

This is not claimed to be the final cross-platform profile.

Knob/HID support and multi-ViewArea behavior are deliberately deferred until the exact target
registration contract is proven on the relevant firmware.

---

## 7. Video ownership inside MHI2

Even after CarPlay is correct, the MHI2 side has another ownership problem: the stock DisplayManager
normally writes the native navigation MPEG-TS into the same Kombi channel that the custom path needs.

The vehicle-proven takeover is deliberately narrow:

```text
                         DisplayManager
                              │
                        stock MPEG-TS
                              │
                              ▼
                 process-local isoTX2 write gate
                     │                    │
                   STOCK                DIRECT
                     │                    │
              real writev()        swallow payload,
                     │              report success
                     ▼                    │
              /dev/mlb/isoTX2             │
                     ▲                    │
                     │                    │
              custom direct writer ───────┘
                     │
              CarPlay MPEG-TS
```

The gate affects only DisplayManager's own `isoTX2` writes. DisplayManager stays alive and its
higher-level state machine continues running; the custom writer is a separate process and remains
able to send strict 12032-byte MPEG-TS blocks to the same transport.

Vehicle testing proved both directions:

```text
STOCK  -> native map visible
DIRECT -> native payload suppressed -> custom video visible
STOCK  -> native map returns
```

A separate Java Direct-VC policy line exists for DSI/display-state research, but it is **not** the
current proven video takeover mechanism.

See [DIRECT_VC_VIDEO_PATH.md](DIRECT_VC_VIDEO_PATH.md) for the exact transport, 64×188-byte write
contract, gate behavior, NavIgnore role and stock recovery sequence.

---

## 8. Why the current problem is not "how do we send video?"

That question has already been answered.

The higher-value question is now:

```text
When the navigation provider or UI context changes...

  does iOS keep the same Type-111 stream?        -> normally yes
  does it continue producing new H.264?          -> must be observed
  does suggestUI change?                         -> often yes
  does the receiver select/refresh that UI?      -> current focus
  is a keyframe/restart needed?                  -> possibly
  does VC ownership remain correct?              -> must remain correct
```

The current engineering target is therefore the **same-session handover path**, not another media
transport rewrite.

See [SCREENALT_CONTROL_PLANE.md](SCREENALT_CONTROL_PLANE.md).

---

## 9. Areas intentionally deferred

These are useful later, but are not allowed to distract from the primary lifecycle problem:

- multi-ViewArea layout polish;
- Knob/HID integration;
- speculative maneuver-card "stream 112";
- local map/card composition;
- decoder/re-encoder pipelines;
- wholesale Audi renderer ports;
- broad BAP/HMI replacement;
- MOST redesign without evidence;
- SD-card one-click installation.

The project should first make the standard CarPlay Auxiliary/ScreenAlt path stable across navigation
start/stop and app handover.
