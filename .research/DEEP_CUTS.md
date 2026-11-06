# Deep cuts

> If you found this file by reading the tree instead of only the README: good.
>
> This is the less-polished engineering notebook: useful search directions, exact public comparator
> projects, decompilation/reconstruction tips, and a few conclusions that took much longer to prove
> than they look in hindsight.
>
> Nothing here changes the project's evidence rule: **a good hypothesis is not vehicle proof**.

## 0. The shortest useful mental model

Do not collapse the whole problem into "CarPlay sends video to the cluster".

There are at least four independent layers:

```text
navigation/app ownership
        │
        ▼
CarPlay / AirPlay control plane
suggestUI / showUI / modes / ViewArea
        │
        ▼
Auxiliary Screen transport
Type 111 / ScreenAlt / H.264
        │
        ▼
MHI2 producer arbitration
DisplayManager vs custom producer
        │
        ▼
MPEG-TS -> isoTX2 -> MOST150 -> cluster
```

A bug in one layer can leave all other layers alive.

The most misleading symptom in this project has been:

```text
"the last map frame is still visible"
```

That alone tells you almost nothing about which layer failed.

---

## 1. Public projects worth reading before reinventing anything

### Luka — CarPlay/RGI architecture

https://github.com/luka-dev/mib2q-carplay-rgi

Useful for:

- route-guidance / RGI architecture;
- Java/HMI patching lineage;
- native hook patterns;
- MHI2Q cluster integration concepts;
- issue history describing classic MHI2/MHI2Q differences.

Particularly useful historical discussion lives in the repository issues, not only current source.

The important conceptual lesson from Luka's work was to keep **metadata/RGI**, **video**, and
**HMI policy** separate rather than trying to solve all three in one native hook.

### Luka — QNX 6.5 ARMv7 toolchain

https://github.com/luka-dev/qnx65-armv7-toolchain

Pinned by this project at:

```text
56a66557245af14077678cd28a83ce3a337d9e2d
```

This was the key to getting away from old opaque SDK images and making small MHI2 native components
publicly rebuildable.

### Luka — JXE reconstruction

https://github.com/luka-dev/jxe2jar

Useful pinned revision:

```text
3bae6e82177c7084a008c42373042e6eebf5653e
```

For IBM J9/MHI2 work, a very practical pipeline is:

```text
lsd.jxe
  -> jxe2jar
  -> standard JAR/class tree
  -> CFR
  -> compare exact class bytes + reconstructed Java
```

CFR version used successfully in related MHI2 work:

```text
CFR 0.152
SHA-256:
f686e8f3ded377d7bc87d216a90e9e9512df4156e75b06c655a16648ae8765b2
```

Do not trust decompiler output as bytecode truth. Always keep:

- original class;
- reconstructed class;
- `javap`/bytecode view where possible;
- class SHA;
- exact JXE baseline.

### OneB1t — Virtual Cockpit / MOST rendering

https://github.com/OneB1t/VcMOSTRenderMqb

Pinned reference used during this research:

```text
27ea74abfcd77c16b5a5bdad3a0bfee24f707ab9
```

This project is extremely useful because it demonstrates that the cluster video problem is not magic:
there is a normal QNX-side rendering/DisplayManager/MOST path you can reason about.

Useful mental bridge:

```text
decoded/rendered video
  -> MHI2 display stack
  -> MOST video path
  -> Virtual Cockpit
```

Our later direct MPEG-TS route bypasses part of that stack, but this project helped identify the
important endpoints and cluster/display context.

### Lanye — MHI2Q CarPlay/MMI mirror family

https://github.com/Lanye-z/MHI2Q-CarPlay-MMI-Mirror

Useful as a comparator for:

- MHI2Q hook structure;
- runtime watchdog/recovery;
- cluster/MMI presentation;
- Luka-derived Java/RGI lineage.

Do not assume Qualcomm-side offsets or rendering APIs transfer directly to Harman MU1440.

### yuedizhibo/MHI2Q-CarPlay-AltScreen (owner: yuedizhibo)

https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen

This one is worth disassembling, not just reading the shell scripts.

High-value public binary:

```text
Toolbox/carplay_alt_screen/universal/libcarplay_altscreen.so
```

Interesting symbol/string families include:

- `AirPlayReceiverSessionPlatformControl`
- `AirPlayReceiverSessionSetup`
- `AirPlayReceiverSessionTearDown`
- `ScreenStreamCreate`
- `suggestUI`
- native Type-111 attach/config lifecycle
- explicit control-command classification

The useful lesson is architectural, not "copy this binary":

> A real AltScreen implementation has to understand both the media path **and** the control/lifecycle path.

### Other useful public lineage

Also worth searching:

- `chefranov/mhi2-au37x-carplay`
- `JeniCzech92/lsdtool`
- `grajen3/mib2-lsd-patching`
- `adi961/mib2-android-auto-vc`

Different platform generations solve adjacent parts of the same problem.

---

## 2. QNX / ELF reversing: practical notes

For MHI2 ARM binaries, start boring:

```sh
file target.so
readelf -h target.so
readelf -S target.so
readelf -Ws target.so
readelf -d target.so
readelf -r target.so
strings -a target.so
```

Then use Ghidra.

Do not strip research builds unless you have a second unstripped copy.

For interposers/hook libraries, explicitly inspect:

- exported hook symbols;
- undefined stock-library dependencies;
- relocations;
- PLT/GOT usage;
- ARM/Thumb function boundaries;
- string-to-xref chains around control commands.

Useful pattern:

```text
interesting string
  -> xref
  -> command classifier
  -> state mutation
  -> stock call forwarding
  -> error/return behavior
```

That pattern was more productive than blindly decompiling every function.

### ABI rule

Never assume "same function name == same ABI".

For every target firmware:

- hash the stock binary;
- inspect symbol availability;
- verify argument types from actual call sites;
- check ARM EABI calling convention;
- fail closed on a hash mismatch.

---

## 3. MHI2 Java/J9 reversing

The most useful lesson here: **compile the smallest possible patch island**.

Do not rebuild a gigantic decompiled LSD tree if two classes are the only changed dependency cycle.

Better:

```text
exact stock JXE
  -> reconstruct JAR
  -> identify two/three target classes
  -> compile those classes together
     against exact compatible stock classpath
  -> prepend patch JAR to bootclasspath
```

Why "compile together" matters:

If class A is patched but javac resolves class B from stock while B is also supposed to be patched,
you can get a build that looks valid but contains an ABI/logic mismatch.

Also inspect the actual boot command. On the tested stack the running IBM J9 command line is often a
better truth source than whatever an install script claims it changed.

---

## 4. iOS 27.2 sender-side reversing

Exact research target used here:

```text
device: iPhone14,2
iOS: 27.2 beta 2
build: 24B5089g
```

Official IPSW SHA-256:

```text
17a161307efffbad74ec6f7045af555ea30c61c565724029dbd8a71b8756139d
```

Useful extracted binary hashes:

The AirPlaySender hash below specifically refers to the historical `ipsw dyld extract --objc --slide`
standalone-Mach-O materialization. Plain or slide-only reconstructions from the same exact cache have
different whole-file hashes; see `docs/research/carplay/IOS27_SENDER_LIFECYCLE.md` for the reproduction
matrix. The executable `__TEXT,__text` payload is identical across those materializations.

```text
AirPlaySender
ef5daa0e0e0058448e83642a3fecfaa1746877f203b5b04fca95153416406e8d

CarKit
a45a2e9f4745fefa5e64e036915311d53649c7d95edf886a2c3f571c9f32bd69

CarPlayServices
568ab7b18afc06010c63d2e60dd10c46dc9a661aa5581cadbd0f122efb1e7c6e

CarPlayDisplayUtils
1dd8e479f1555be78d91ab038f7a04e006231e49702a33ee8c3f16cf4a47db7b

CarPlaySupport
8c6b77e48f79063080859183aee46922bd15478fb1e558b467b88c373f13a4a3

CarPlay.framework / CarPlay
fb5b588570465f9137243853a8445c224bc972529b8b7259e641de3e46606b60
```

Tool used successfully:

```text
blacktop/ipsw v3.1.724
```

Do not publish the extracted Apple Mach-O files. Publish hashes, extraction instructions and derived
findings.

---

## 5. The iOS finding that changed the implementation

The biggest correction was this:

> An ordinary navigation-provider switch is **not** a Type-111 generation boundary.

The earlier tempting model was:

```text
Apple Maps stops
  -> tearDownStreams(111)
Google/Waze starts
  -> setUpStreams(111)
```

The stronger iOS-27.2 model is:

```text
Type 111 stays established
      │
      ├─ navigation owner changes
      ├─ suggestUI changes
      ├─ app/resource/turn state changes
      ├─ second-display mode changes
      └─ video may need same-session reacquire / fresh IDR
```

Only actual endpoint topology/session events should create a new stream generation.

This one rule eliminates a huge amount of wrong recovery logic.

---

## 6. Cluster URLs: the useful three

The important URL family is:

```text
maps:/car/instrumentcluster
maps:/car/instrumentcluster/map
maps:/car/instrumentcluster/instructioncard
```

Current sender-side interpretation:

| URL | Role |
| --- | --- |
| base | generic/root instrument-cluster context |
| `/map` | persistent map presentation |
| `/instructioncard` | transient maneuver/turn-card presentation |

These are **UI-context roles**, not three different AirPlay streams.

For normal navigation, iOS offers approximately:

```text
[ base, map ]
```

During maneuver-card presentation it can offer:

```text
[ instructioncard, map, base ]
```

The word `maps:` is not proof that the mechanism is Apple-Maps-only. The system frameworks also use
the default cluster URL family for eligible third-party instrument-cluster scenes.

---

## 7. suggestUI is more important than it first looks

Sender-side flow:

```text
provider/app suggestion
       +
current session URLs
       +
receiver-advertised altScreenSuggestUIURLs
       │
       ▼
intersection / sanitization
       │
       ▼
suggestUI { urls:[...] }
       │
       ▼
vehicle
```

An empty list is meaningful:

```text
suggestUI([])
```

means "withdraw the current cluster UI suggestion".

It does **not** mean "tear down Type 111".

### Subtle but important

`suggestUI` does not automatically imply a sender-side `showUI` call.

There is a receiver-selection concept between:

```text
candidate UI contexts
```

and:

```text
the UI context actually shown
```

That gap is one of the current MU1440 lifecycle questions.

---

## 8. showUI direction: do not oversimplify

One early shorthand was "showUI is HU -> phone".

That is too simple.

The exact framework contains:

- incoming handling of `showUI` / `stopUI`;
- a `CARSession showUIForStreamUUID:url:` sender path that logs sending `showUI` to the vehicle.

Therefore:

> Command names alone do not define direction. Follow the exact call path.

This matters a lot when interpreting PlatformControl traces.

---

## 9. forceKeyFrame is a recovery primitive, not a new stream

Treat:

```text
forceKeyFrame
```

as:

```text
please restart/resynchronize the current screen bitstream
```

not:

```text
create a new Type-111 session
```

The working same-session recovery hypothesis is:

```text
stopUI
  -> showUI(selected cluster URL)
  -> forceKeyFrame
```

Whether all three are necessary in every transition is still under vehicle test.

---

## 10. VideoConfig and IDR: do not cheat the generation model

A consumer attaching to an already-running screen must not accept arbitrary H.264 frames as a valid
new generation.

Useful invariant:

```text
new consumer
  -> wait for usable codec configuration
  -> wait for compatible IDR
  -> then declare generation primed
```

This avoids a class of "it worked once, then froze after app switch" bugs caused by stale SPS/PPS or
joining mid-GOP.

The later GEN2 work therefore tracks separately:

- stream/session generation;
- codec/config generation;
- consumer generation.

That separation is worth keeping even if the implementation is rewritten.

---

## 11. Static screen != dead stream

Another expensive lesson:

CarPlay is allowed to stop emitting visually redundant frames for a static secondary display.

Therefore:

```text
video heartbeat stopped advancing
```

does not prove:

```text
navigation ended
```

The Auto-Direct supervisor deliberately:

1. requires fresh post-connect activity when establishing DIRECT;
2. then tolerates a quiet source while the logical Type-111 state remains valid.

Do not use "no new frame for one second" as route-end logic.

---

## 12. The direct VC path in one line

The currently proven downstream path is:

```text
Annex-B H.264
 -> direct-ts-remux
 -> MPEG-TS
 -> exactly 64 * 188 = 12032 byte write units
 -> /dev/mlb/isoTX2
 -> devp-iso-mmx-mib2
 -> MOST150
 -> Virtual Cockpit
```

The 12032-byte application write boundary matters.

If you are debugging the MOST side, use the published `most-ts-writer` source to isolate it from
CarPlay completely.

---

## 13. Why the writev gate works

The stock DisplayManager remains alive.

Instead of stopping it, the interposer tracks the file descriptor associated with:

```text
/dev/mlb/isoTX2
```

In STOCK:

```text
DisplayManager writev -> real writev
```

In DIRECT:

```text
DisplayManager writev
  -> report success to caller
  -> swallow only the target payload bytes
```

The process remains healthy while a custom producer writes the alternate TS.

This is cleaner than repeatedly killing/restarting DisplayManager and it makes STOCK recovery fast.

---

## 14. NavIgnore is a separate problem

Do not confuse:

```text
video producer ownership
```

with:

```text
which logical cluster map presentation is active
```

The `isoTX2` gate handles the first.

NavIgnore-style Java/HMI policy keeps the normal Kombi map presentation available while smartphone
navigation is active.

Both were required for the visible vehicle proof.

---

## 15. ViewArea is probably worth more attention than another renderer rewrite

Exact iOS-side code contains a real:

```text
requestViewArea
```

flow on an existing screen.

That means dynamic cluster layout support should be investigated as an in-session presentation
problem before inventing new Type-111 streams for each cluster view.

On MU1440, useful stock HMI state leads include:

- model 402521 / `ChoiceModelGUI`;
- `IViewSizeManager.getCurrentViewSize()`;
- current cluster context;
- visible KDK state;
- composition/background state.

The right long-term architecture may be:

```text
stock VC layout state
  -> project layout abstraction
  -> matching CarPlay ViewArea / SafeArea
  -> existing Type-111 session
```

rather than hard-coded geometry per boot.

---

## 16. External/commercial comparators: how to use them responsibly

If you have lawful access to another implementation:

Do not start by copying code.

Build a role map:

```text
what binary hooks AirPlay?
what handles Type 111?
what creates/presents the surface?
what handles showUI/suggestUI?
what handles lifecycle?
what handles watchdog/recovery?
```

Then compare:

- exported/imported symbols;
- strings;
- protocol command vocabulary;
- state-machine transitions;
- hashes / binary identity;
- public-source lineage.

This was much more useful than treating any package as an oracle.

The public yuedizhibo/MHI2Q-CarPlay-AltScreen implementation is especially valuable because it provides a legally inspectable
comparator for many of these roles.

No proprietary/commercial payload is mirrored in this repository.

---

## 17. A good next trace

If you want to contribute one high-value trace, capture one controlled sequence:

```text
Apple Maps active
 -> finish trip
 -> wait
 -> start Google Maps or Waze
 -> wait
 -> stop
 -> restart
```

Correlate timestamps across:

- `suggestUI`;
- `showUI` / `stopUI`;
- `modesChanged`;
- Type-111 connection/generation;
- VideoConfig generation;
- SPS/PPS/IDR counters;
- delivered access units;
- local tee consumer;
- direct-ts-remux blocks;
- gate STOCK/DIRECT state.

That trace is more useful than another screenshot of a map in the cluster.

---

## 18. Last note

If an implementation change makes the picture appear but cannot explain:

- why the stream is considered alive;
- why a generation changed;
- why STOCK can be restored;
- what happens when the provider changes;

it is probably not ready to become the new baseline.

The boring state machine is the product.
