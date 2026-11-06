# Comparator findings — what to copy conceptually, what not to copy

> **Research status · 2026-11-05:** **MEDIA / COMPARATOR RESEARCH.** This is a research finding or candidate, not automatically a validated MIB Runtime implementation. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


This page collects **derived architectural findings** from public prior art and lawfully inspected
third-party/commercial implementations.

No proprietary/commercial payloads are redistributed here.

The purpose is to prevent contributors from repeating old reverse-engineering work or porting
platform-specific behavior that looks relevant but is not.

## 1. OneB1t: output path proof, not a CarPlay source

Reference:

```text
OneB1t/VcMOSTRenderMqb
27ea74abfcd77c16b5a5bdad3a0bfee24f707ab9
```

The useful proof is that MQB MHI2 can render custom video into the cluster path through the QNX /
DisplayManager / DMDT / MOST stack.

Relevant public route model:

```text
custom video source
  -> custom render displayable
  -> cluster map context
  -> DMDT display
  -> stock MOST video transport
  -> Virtual Cockpit
```

The classic OneB1t renderer is a VNC/RFB client.

Its later stream-player is source-agnostic and therefore much more relevant to AltScreen work.

Important lesson:

> OneB1t solves a **VC output problem**. It does not by itself solve Apple Type-111 acquisition.

The current project eventually proved an even lower-level direct transport route using MPEG-TS on
`/dev/mlb/isoTX2`, but OneB1t was critical evidence that the destination path was real and reusable.

## 2. Luka: RGI / metadata is a different layer from projected video

Luka's public CarPlay/RGI work is valuable for:

- route-guidance metadata;
- navigation/HMI policy;
- JXE/J9 patch lineage;
- native/QNX integration patterns.

Do not assume that RGI/maneuver support and full projected cluster video are the same problem.

A useful separation is:

```text
navigation metadata / arrows
        !=
projected map video
        !=
cluster/HMI arbitration
```

The public project may eventually support all of them, but they should remain independently
testable.

## 3. Public MHI2Q AltScreen: control plane matters as much as media

The public Yuedi AltScreen implementation exposes useful comparator behavior around:

- `AirPlayReceiverSessionPlatformControl`;
- `AirPlayReceiverSessionSetup`;
- `AirPlayReceiverSessionTearDown`;
- Type-111 attach/config lifecycle;
- ScreenStream creation;
- `suggestUI`;
- control-command classification.

The most useful conceptual lesson is:

> A real secondary-display implementation cannot be only an H.264 socket.

Media/session generation and UI/control lifecycle must both be understood.

License note:

The public Yuedi repository uses PolyForm Noncommercial 1.0.0. It is therefore a **comparator**, not a
code donor for this GPL project.

## 4. Commercial/recovered MHI2Q implementation: minimum Type-111 responsibilities

Static analysis of a recovered MHI2Q implementation gave strong architectural evidence for this
iPhone-facing minimum:

1. preserve stock primary screen 110;
2. identify stream type 111;
3. handle 111 outside the stock unsupported path;
4. expose a dedicated receiver data port;
5. reuse the stock CarPlay session/security context;
6. derive/use the per-screen crypto material;
7. receive ScreenStream framing;
8. accept VideoConfig + H.264;
9. hand video to a separate presenter/consumer;
10. own reconnect/teardown separately from unrelated streams.

The current MU1440 implementation independently implements the same **roles** around the stock
AirPlay core.

This is role-level parity, not copied source.

## 5. Commercial MHI2Q binary identifiers

For researchers who lawfully possess the same historical package, these hashes can help identify
whether the comparison is against the same material.

| Component | SHA-256 | Observed role |
| --- | --- | --- |
| patched/full `libairplay.so` | `b85deac575f335e0d096cf2280e7c57bdfd68dc8d33d950fedacba428715808c` | AirPlay / Type-111 integration |
| `libirc_mmx_svc.so` | `e1a4792b6eea2e4fcafc71c19db442915108d5cf8d7f6e88c652eee586bb441f` | AirPlay-side glue/config |
| `esovpd` | `3540e5891b1e79b4e5c2b6d464eb01dae5ffae13dc909db47906a8e8c0c7ec97` | Qualcomm H.264 presenter |
| `gal` | `fe9eeba447a119df5b3e8b0a132542e984d298ba4cc48cce2eaf67ef5ed9c17f` | GAL companion/host |
| `libsdisproxy.so` | `271171b92e5ae26ec8a2e0f5601ff68ccf6570c08c3370431c48bca2c5a8f94a` | graphics-side glue |
| `nvvmpd` | `3540e5891b1e79b4e5c2b6d464eb01dae5ffae13dc909db47906a8e8c0c7ec97` | byte-identical presenter slot |

Historical HMI JAR observed in the same analysis:

```text
xTcpLog.jar
e975200f142fbc6ba783b8f5c6ef24ddb4325b22ffff5be4d2eb4ca5b895c747
```

These files are **not distributed by this repository**.

## 6. ViewArea/SafeArea strings: presence is not execution proof

The recovered MHI2Q glue binary contained literals such as:

- `viewAreas`
- `originXPixels`
- `originYPixels`
- `safeArea`
- `drawUIOutsideSafeArea`
- `initialViewArea`

A deeper xref pass did **not** prove executable references to those literals in that sample.

Classification:

```text
literal present
!=
runtime use proven
```

This mattered because blindly copying those keys would have created false confidence.

Independent iOS/public protocol evidence proves ViewArea/SafeArea are real CarPlay features. That is a
different evidence chain.

## 7. Qualcomm presenter crop/geometry is downstream vehicle rendering

The recovered Qualcomm presenter actively referenced:

- `OMX_W`
- `OMX_H`
- `OMX_CODEC_W`
- `OMX_CODEC_H`
- `OMX_CROP_W`
- `OMX_CROP_H`
- `OMX_CROP_X`
- `OMX_CROP_Y`
- `OMX_PRESENT`
- `OMX_LISTEN`

These are real **post-reception presenter controls**.

They are not proof that the same crop/geometry values are part of the iPhone-side AltScreen
negotiation.

The MU1440 direct MPEG-TS/MOST route replaces this Qualcomm presenter layer, so these controls should
not be ported mechanically.

## 8. The famous 1920×1080 -> 1440×450 crop was Android Auto

One historical HMI patch contained an active crop:

```text
source: 1920 x 1080
origin: 240,315
crop:   1440 x 450
```

A deeper call-site audit showed the crop flag was gated by:

```text
showProjection && androidAutoConnected
```

For CarPlay projection, that crop remained disabled.

Therefore:

> Do **not** import the 1440×450 crop into the CarPlay Type-111 path.

This is exactly the kind of attractive-but-wrong comparator detail that should be documented.

## 9. Audi displayable 46: real, but downstream/platform-specific

The recovered HMI integration used:

- smartphone projection displayable **46**;
- native map displayable **33**;
- KDK/display composition surfaces;
- cluster contexts in an Audi-specific HMI layout.

It also aligned the smartphone projection plane to the native map X/Y position.

This proves a useful concept:

> a commercial integration deliberately aligned its projected plane with the stock map region.

It does **not** prove MU1440/Škoda should reproduce Audi displayable 46.

The current direct MOST route already targets the video path used by the native cluster map and
therefore avoids recreating that Audi presentation plane.

## 10. Commercial local zoom control: TCP 19822

The historical HMI patch contained a local projection zoom client:

```text
host: 127.0.0.1
port: 19822
commands: "in" / "out"
```

The same implementation's data block placed values associated with:

- stream type 111;
- port 6031;
- port 19822

near each other, strongly supporting ownership by the custom AltScreen shim.

What this **does not** prove:

- that iOS receives a CarPlay zoom command;
- that the zoom modifies sender-side rendering;
- the exact downstream effect of the server.

Classification:

```text
local projection control proven
exact effect still open
```

This remains out of scope for the first stable MU1440 solution.

## 11. Commercial smartphone-navigation state was not video-only

The recovered HMI layer also observed whether navigation was running on the smartphone and forwarded
that state into cluster/HMI logic.

Architectural lesson:

> Mature integrations can use both media validity and high-level app/navigation state.

For current MU1440 takeover, valid Type-111 media remains the stronger proof that an alternate video
source exists. High-level state is useful as a lifecycle/diagnostic signal, not as a substitute for
media readiness.

## 12. What not to port

Do **not** import these merely because they exist in another package:

- Audi-specific displayables/contexts;
- Qualcomm OMX presenter;
- Android-Auto-specific 1440×450 crop;
- license/unit-binding degradation logic;
- SSH/Telnet/tripwire/protection logic;
- unknown ViewArea strings with no executable xref;
- commercial installer assumptions.

## 13. What is worth preserving conceptually

The useful cross-implementation common denominator is much smaller:

```text
stock primary CarPlay stays stock
       │
secondary Type 111 is independently negotiated
       │
stock session/security is reused
       │
secondary H.264 is independently consumed
       │
UI/control lifecycle is tracked
       │
vehicle-side presenter/takeover is reversible
```

That architecture is portable even when the exact Qualcomm/Audi/Harman implementation details are
not.

## 14. Evidence discipline for future comparators

When someone brings another solution, record:

- exact file/hash;
- platform generation;
- source vs binary evidence;
- active xref vs inert string;
- media-plane role;
- control-plane role;
- HMI/presenter role;
- whether the behavior is platform-specific;
- licensing/redistribution status.

The goal is to learn everything useful without turning this repository into a mirror of other
people's binaries.
