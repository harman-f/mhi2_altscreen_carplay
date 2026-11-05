# MU1440 GEN2 AirPlay hook / ABI map

> **Research status · 2026-11-05:** **MEDIA / COMPARATOR RESEARCH.** Findings or proposals are not automatically qualified runtime capabilities. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


Reference stock component:

```text
/mnt/app/eso/lib/libairplay.so
SHA-256:
193a4fd9101ec2aa05e7159cfa307b96500810d379ca74a194f172adc13a46b5
```

This hash is the compatibility gate for the current reference implementation.

## Hook strategy

The current GEN2 development source keeps the stock AirPlay implementation and resolves key receiver
functions from the next object in the dynamic-link chain.

Primary stock symbols:

```text
AirPlayReceiverSessionSetup
AirPlayReceiverSessionStart
AirPlayReceiverSessionTearDown
AirPlayReceiverSessionPlatformControl
AirPlayReceiverSessionControl
AirPlayReceiverSessionMakeModeStateFromDictionary
AirPlayReceiverSessionSetSecurityInfo
AES_CBCFrame_Init
```

The project does **not** replace the whole stock AirPlay library.

## Why plain LD_PRELOAD interposition was not enough

On the tested MU1440 runtime, ordinary symbol interposition did not provide the
required internal lifecycle coverage. This is runtime-derived evidence, not a
claim that the ELF contains no lifecycle PLT entries.

For the required session lifecycle functions, GEN2 therefore installs a small ARM prologue hook and
keeps a trampoline to the stock implementation.

If hook installation fails, the implementation disables itself **fail-closed** instead of continuing
with a partially installed lifecycle.

The [2026-09-28 exact MU1438/MU1440 audit](../firmware/MU1438_MU1440_OFFLINE_COMPARISON_2026-09-28.md)
finds GLOBAL/DEFAULT Setup/Start/TearDown definitions and JUMP_SLOT/PLT routes on
**both** stock libraries. Static PLT/visibility flags alone do not prove QNX
loader resolution, preload precedence or complete callback coverage. Retain the
proven MU1440 inline strategy; audit another target's runtime separately.

## Prologue validation

Generic Setup/Start/TearDown hook validation expects the target function to begin with the proven
ARM prologue shape used by the target build.

Current helper default:

```text
word0: 0xe92d4ff0
word1: 0xed2d8b02
```

PlatformControl is validated against:

```text
word0: 0xe92d4ff0
word1: 0xed2d8b04
```

SessionControl is validated against:

```text
word0: 0xe92d4ff0
word1: 0xe1a06002
```

These values are **target evidence**, not portable API.

If they differ on another firmware, stop and re-audit the function. Do not weaken the check until the
new ABI/prologue has been understood.

## Hooked semantic roles

### SessionSetup

- call stock first with the original request;
- preserve stock response;
- advertise AltScreen/ViewArea capability;
- detect requested stream type 111;
- append the project-owned Type-111 data port/stream response;
- keep unknown peer fields by cloning descriptors rather than rebuilding them from assumptions.

### SessionStart

Binds the project Type-111 control/media state to the stock session after the normal stock start
succeeds.

### SessionTearDown

Clears project-owned stream/session generation state while respecting stock teardown.

### PlatformControl

Current development:

- records bounded/redacted command payloads;
- forwards to stock;
- treats most commands as stock-authoritative;
- special-cases the private Type-111 `suggestUI` ownership contract when stock returns its
  no-auxiliary-presenter result.

### SessionControl

Used for control/session observations and serialized UI/keyframe operations in the current
development line.

## Stock mode parser

The implementation also resolves:

```text
AirPlayReceiverSessionMakeModeStateFromDictionary
```

so mode-state observations can be interpreted with the stock parser rather than reimplementing the
entire structure from guesses.

## CarPlay key derivation / AES observation

The project reuses the stock per-screen crypto behavior.

A narrow `AES_CBCFrame_Init` observation path captures the relevant stock CarPlay master AES key
only when the call originates from the proven `AirPlayReceiverSessionSetSecurityInfo` caller range.

The key is used in-process to derive/decrypt the private Type-111 screen stream.

This is an interoperability mechanism on the running stock CarPlay session, not a replacement of
CarPlay authentication.

Do not persist or log session key material.

## Network boundaries

Two listeners have deliberately different exposure:

```text
Type-111 receiver:
  iPhone-facing
  dataPort returned through SETUP
  reachable on CarPlay link

local H.264 tee:
  127.0.0.1 only
  default port 19820
  never intended to leave the head unit
```

This distinction matters for both security and debugging.

## Reference defaults

```text
Type-111 data port preference: 6031
local H.264 tee:               19820
geometry:                      1010 x 376
max fps:                       30
default UI URL:                maps:/car/instrumentcluster
```

## Porting checklist

For another firmware:

1. hash stock `libairplay.so`;
2. verify all required symbols exist;
3. inspect each target prologue/calling convention;
4. verify CoreFoundation object ABI assumptions;
5. verify screen-header framing;
6. verify stock security/key derivation call path;
7. verify stream 111 SETUP descriptor shape;
8. only then enable inline hooks.

"Same MU family" is not sufficient evidence.
