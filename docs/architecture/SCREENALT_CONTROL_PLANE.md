# ScreenAlt control plane — handshake, ownership and presentation refresh

> **Original September 2026 lifecycle/reference model.** Its control command roles remain useful; references to "our current problem" or the "next vehicle experiment" reflect the original dated session. Use [current integration status](../status/INTEGRATION_STATUS_2026-10-21.md) and [recovery/fault-isolation acceptance](../testing/STREAM111_FAULT_ISOLATION_2026-10-21.md) for newer work, and [architecture index](README.md) for module ownership.
>
> This is the detailed protocol and lifecycle reference; the current recovery checklist lives in the linked fault-isolation guide.

## 1. What "handshake" means here

There is no single magic packet that can be called *the* CarPlay AltScreen handshake.

The practical handshake is a sequence of layers:

```text
A. receiver advertises a secondary display
B. AirPlay/CarPlay establishes the Auxiliary/ScreenAlt stream
C. iOS decides which cluster UI contexts are valid
D. navigation/app ownership changes
E. iOS suggests candidate UI contexts
F. receiver may select/request a concrete presentation
G. existing stream continues or is refreshed
H. receiver routes the resulting video to the VC
```

In the original September engineering phase, the primary gaps were **C–F**, with **G** as recovery/synchronization. Later vehicle findings identified additional source-session teardown and separate native writer-gate failures.

The media route in H is already proven.

---

## 2. Layer A — receiver advertisement

The head unit has to expose a coherent secondary-display capability.

At minimum the receiver-side model contains concepts such as:

```text
display identity / UUID
screen type = 111
geometry
frame rate
initial URL
ViewArea definitions
UI-context capability
optional input/HID device binding
```

An important rule is **coherence**.

Do not advertise an input device merely because another implementation does. Do not expose
multi-ViewArea support unless the receiver can actually honor it. A capability that exists in a
dictionary but is not backed by working receiver behavior can move failure later into the lifecycle
and make diagnosis harder.

The current MU1440 engineering profile is therefore intentionally no-HID and single-ViewArea.

---

## 3. Layer B — Auxiliary/ScreenAlt stream creation

Sender-side reverse engineering shows a dedicated Auxiliary/ScreenAlt path.

Conceptually:

```text
endpoint feature setup
      │
      ▼
setup auxiliary screen
      │
      ├── secondDisplayID
      ├── ScreenAlt / AuxiliaryScreen identity
      └── screen-stream options
              │
              ▼
        Type-111 ScreenStream
```

This is a real secondary screen, not merely a renamed main CarPlay screen.

The current project already receives this stream on the reference MU1440.

---

## 4. Layer C — which UI contexts are available?

CarPlay maintains a set of possible instrument-cluster UI contexts.

The sender-side candidate set is filtered before `suggestUI` is emitted.

```text
navigation app wants:
    [base, map]

iOS/session allows:
    [base, map, instructioncard]

receiver advertises:
    [base, map]
            │
            ▼
effective:
    [base, map]
            │
            ▼
suggestUI([base, map])
```

The receiver's inherited/advertised values therefore matter.

Current vehicle instrumentation explicitly observes fields such as:

- `altScreenSuggestUIURLs`;
- `altScreenURLs`;
- `uiContextURLs`.

The project intentionally observes stock behavior before synthesizing new capability arrays.

---

## 5. Layer D — navigation ownership is not stream ownership

CarPlay has a separate navigation ownership model.

Typical startup ordering observed on the sender side:

```text
navigator created/configured
        │
        ├── instrument-cluster support active
        │       └── suggestUI([base,map])
        │
        └── request navigation ownership
                │
                ▼
        ownership callback later
```

Trip finish/cancel:

```text
finish/cancel
    │
    ├── reset route guidance
    ├── request release of navigation ownership
    ├── suggestUI([])
    └── display/trip cleanup
             │
             ▼
    owner callback may arrive later
```

This is one of the reasons app handover is subtle: UI suggestion, trip state and asynchronous
ownership state do not all change at exactly the same instant.

---

## 6. Layer E — suggestUI

`suggestUI` is best understood as:

> "These are the cluster UI contexts currently meaningful to the navigation provider/session."

It is **not** equivalent to:

> "Immediately switch the physical cluster to this exact screen."

Normal map state:

```text
iPhone -> HU

suggestUI({
    urls: [
        maps:/car/instrumentcluster,
        maps:/car/instrumentcluster/map
    ]
})
```

Trip finish/cancel:

```text
iPhone -> HU

suggestUI({
    urls: []
})
```

### Important error behavior

The current sender-side path does not register a receiver completion/reply callback for
`CARSession suggestUI:`.

Therefore a receiver-side result such as:

```text
-6714 / kNotHandledErr
```

does **not** imply that iOS will automatically:

- retry;
- choose a different URL;
- send `showUI`;
- tear down Type-111;
- create a new Type-111 stream.

This is a central reason the receiver implementation matters.

---

## 7. Layer F — showUI / stopUI

`showUI` is a separate operation.

A useful conceptual model is:

```text
iPhone:
    suggestUI([candidate contexts])
             │
             ▼
head unit:
    evaluate capability + current vehicle/UI state
             │
             ├── keep current presentation
             │
             ├── stopUI(...)
             │
             └── showUI(screen UUID, selected URL)
                         │
                         ▼
iPhone:
    render/request selected secondary UI
```

Protocol direction must always be determined from the concrete code path. The command name alone is
not enough; current CarPlay code contains both incoming receiver-command handling and outgoing
sender paths involving `showUI`.

For the project, the practical question is:

> Which receiver-side sequence reproduces the behavior expected by the current CarPlay navigation
> lifecycle on MU1440?

---

## 8. Layer G — presentation refresh without rebuilding the stream

The sender exposes an explicit bitstream restart operation.

```text
head unit -> iPhone:
    forceKeyFrame
          │
          ▼
iOS:
    ScreenRestartBitstream
          │
          ▼
existing ScreenStream / VirtualDisplay
```

This is **recovery on the existing stream**.

It is not evidence of a new session.

The current GEN2 engineering model therefore separates:

```text
UI ownership reacquire:
    stopUI
      -> showUI(selected URL)
      -> forceKeyFrame

from

real stream generation change:
    TEARDOWN 111
      -> fresh SETUP 111
```

The former can be a bounded same-session diagnostic. The latter should only happen when the
transport/session actually changes.

---

## 9. SecondDisplayMode

Another sender-side concept is SecondDisplayMode.

Current reverse engineering shows:

```text
SecondDisplayMode change
        │
        ▼
SetMode({mode})
        │
        ▼
existing ScreenStream
        │
        ▼
VirtualDisplay activation options updated in place
```

Presentation/client process death can drive the mode back to 0 without directly destroying the
Auxiliary stream.

Again:

> presentation mode transition != Type-111 recreation.

---

## 10. ViewArea

ViewArea is yet another same-session mechanism.

```text
iPhone requestViewArea(screen UUID, index)
        │
        ▼
receiver applies/selects area
        │
        ▼
receiver reports/updates ViewArea
        │
        ▼
existing VirtualDisplay / ScreenStream adapts
```

The current first target uses only one ViewArea. Multi-area behavior is deferred until the exact
receiver contract is better proven.

---

## 11. Failure classes (foundational model; see later October evidence)

The interesting handover case is:

```text
Apple Maps active
      │
      ▼
Type-111 alive + VC displaying Apple Maps
      │
      ▼
navigation state changes
      │
      ├── clean Apple route finish
      │        or
      └── direct switch to Waze/Google
               │
               ▼
        ownership/UI context changes
               │
               ▼
     what exactly happens next?
```

There are several very different failure classes that can look similar from the driver's seat.

### Case 1 — actual new stream generation

```text
111 TEARDOWN
 -> new 111 SETUP
 -> new connection/session identity
```

**Meaning:** rebuild/rebind consumer state.

### Case 2 — same stream, source goes quiet

```text
same 111
 -> no fresh H.264 access units
```

**Meaning:** UI/ownership/presentation activation is the leading suspect.

This is the strongest use case for a bounded same-session:

```text
stopUI -> showUI -> forceKeyFrame
```

diagnostic.

### Case 3 — source continues but no usable IDR/config arrives

```text
same 111
 -> packets/AUs continue
 -> decoder/consumer never receives a valid new config+IDR boundary
```

**Meaning:** resynchronization/consumer priming problem.

### Case 4 — consumer receives valid new frames but VC stays stale

```text
fresh config/IDR
 -> delivered AUs progress
 -> VC image remains stale
```

**Meaning:** only here should downstream presenter/MOST ownership be reopened as the primary suspect.

---

## 12. Why current GEN2 has more lifecycle state

The current generation is designed so that transient or stale asynchronous activity cannot silently
corrupt the active stream.

Relevant concepts include:

- explicit session/request generations;
- stale completion rejection;
- serialized `showUI`, `stopUI`, `forceKeyFrame`;
- bounded reacquire;
- transactional VideoConfig handling;
- complete-access-unit validation;
- config + complete-IDR consumer priming;
- stream/codec/consumer generations;
- bounded queueing;
- delivered-AU telemetry;
- fail-closed partial initialization.

This is less about adding features and more about making **ownership changes observable and
deterministic**.

---

## 13. Historical September vehicle experiment

The next useful test is not "try random CarPlay patches".

It is a controlled same-session trace.

### A — clean finish

```text
Apple Maps active
 -> mark
 -> finish/cancel Apple route
 -> wait
 -> start Waze or another navigation provider
 -> mark
```

Expected sender-side signal includes the clean `suggestUI([])` withdrawal.

### B — direct handover

```text
Apple Maps active
 -> mark
 -> start/switch to Waze or another provider
   without explicitly finishing Apple first
 -> mark
```

The difference between A and B can identify whether the stale state is tied to explicit UI
withdrawal, ownership handover, resync or a true stream topology transition.

### Observe in this order

1. `suggestUI`;
2. `modesChanged`;
3. `showUI` / `stopUI` / `changeModes`;
4. actual type-111 SETUP/TEARDOWN;
5. receiver command return/error;
6. stream connection/session identity;
7. source access units;
8. VideoConfig / SPS / PPS / IDR;
9. consumer priming;
10. delivered output.

---

## 14. Decision tree

```text
                navigation handover
                        │
                        ▼
          did type 111 really restart?
                 /             \
               yes              no
               │                │
               ▼                ▼
       bind new generation   are fresh source AUs arriving?
                                /              \
                              no                yes
                              │                 │
                              ▼                 ▼
                     UI/control-plane       valid config+IDR?
                     reacquire suspect       /           \
                                           no            yes
                                           │             │
                                           ▼             ▼
                                     resync/priming   delivered output?
                                                       /          \
                                                     no            yes
                                                     │             │
                                                     ▼             ▼
                                                consumer path   VC still stale?
                                                                    │
                                                                    ▼
                                                         reopen presenter/MOST
```

This decision tree is the current engineering center of gravity.

---

## 15. What not to infer

Do not infer any of these solely from a frozen cluster image:

- that Type-111 died;
- that iOS rebuilt the stream;
- that the H.264 path is broken;
- that Waze/Google need a different stream number;
- that a second decoder is required;
- that MOST is the problem;
- that HID is mandatory;
- that `suggestUI` automatically failed on the sender.

The purpose of the Flight Recorder work is to turn those visual symptoms into a classified lifecycle
event.
