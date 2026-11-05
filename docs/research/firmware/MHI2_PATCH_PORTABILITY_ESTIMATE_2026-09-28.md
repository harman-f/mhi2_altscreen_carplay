# MHI2 patch-portability estimate

> **Research status · 2026-11-05:** **FIRMWARE RESEARCH REFERENCE.** Static comparison is not a supported vehicle or installer claim. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


Date: **2026-09-28**

Status: **engineering triage hypothesis from static firmware-corpus evidence — not a support matrix**

This document answers:

> Which parts of the current Škoda MU1440 AltScreen solution are likely to transfer to another MHI2
> firmware unchanged, which need a target profile, and which need a different patch/transport path?

The estimates are intended to prioritize vehicle tests. They are not measured probabilities and do
not authorize installing the MU1440 release on another train.

The only vehicle-proven complete stack remains:

```text
MHI2_ER_SKG13_P4526_MU1440
Škoda / AID10-class reference cluster
```

The current MU1440 installer is deliberately exact-hash gated. **Every non-reference train will be
rejected by the current installer even where an individual patch is judged portable below.**
Patch portability and installer admission are separate questions.

---

## Rating vocabulary

| Rating | Heuristic confidence | Meaning |
| --- | ---: | --- |
| **PROVEN** | vehicle evidence | demonstrated on the exact reference vehicle |
| **VERY LIKELY DIRECT** | about 85–95% | relevant stock code/ABI/path is exact or unusually strong static match; first bounded test may use the existing patch unchanged |
| **LIKELY / VERIFY FIRST** | about 65–85% | strong structural evidence; exact read-only preflight and target test required |
| **PROFILE ADAPTATION** | about 35–65% direct reuse | concept/source is reusable, but the MU1440 binary should not be used unchanged |
| **NEW PATCH / PATH** | below about 20% direct reuse | known architecture/transport mismatch makes the current implementation the wrong target patch |
| **UNKNOWN** | not estimated | evidence is not sufficient yet |

These bands are engineering estimates, not statistical failure rates.

---

# 1. What is actually being ported?

The reference solution consists of independent layers:

```text
iPhone / CarPlay
      │
      ▼
AirPlay / Stream-111 receiver
      │
      ▼
libaltscreen111.so
      │  decrypted Annex-B H.264
      ▼
direct-ts-remux
      │  MPEG-TS, 64 × 188 B
      ▼
DisplayManager-local writev gate
      │
      ▼
/dev/mlb/isoTX2
      │
      ▼
MOST150 -> VC decoder
```

Separate Java/HMI policy:

```text
NavIgnore
   -> keep normal cluster MAP_VIEW available during smartphone navigation

Most20FPS
   -> one-class ChangeDataRateSequence override

Direct-VC Java policy
   -> ChangeDataRate + ChangeDataRateSequence
      higher-level producer-policy research
```

A train can therefore be compatible with one layer and incompatible with another.

---

# 2. Executive portability matrix

| Firmware | GEN2 / Stream-111 receiver | `direct-ts-remux` | `isoTX2` write gate | Cluster video path | NavIgnore | Most20FPS | Direct-VC Java policy | First-port assessment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **SKG13 P4526 MU1440** | **PROVEN** | **PROVEN** | **PROVEN** | **PROVEN** MOST/`isoTX2` | **PROVEN** | exact stock-class baseline | exact stock-class baseline; policy remains research | reference |
| **VWG13 K4525 MU1367** | **VERY LIKELY DIRECT** | **VERY LIKELY DIRECT** | **LIKELY / VERIFY FIRST** | **VERY LIKELY same MOST family** | **LIKELY / VERIFY FIRST** | **VERY LIKELY DIRECT** | **VERY LIKELY DIRECT** | strongest non-reference reuse candidate |
| **SEG11 P4709 MU1447** | **VERY LIKELY DIRECT** | **VERY LIKELY DIRECT** | **LIKELY / VERIFY FIRST** | **LIKELY same MOST family; geometry/profile differs** | **LIKELY / VERIFY FIRST** | **VERY LIKELY DIRECT** | **VERY LIKELY DIRECT** | high reuse; geometry and ownership test required |
| **SKG11 K3343 MU1433** | **PROFILE ADAPTATION** | **VERY LIKELY DIRECT** | **LIKELY / VERIFY FIRST** | **LIKELY same MOST family; geometry differs** | **LIKELY / VERIFY FIRST** | **VERY LIKELY DIRECT** | **VERY LIKELY DIRECT** | downstream stack mostly reusable; AirPlay target profile required |
| **VWG11 K3342 MU1427** | **PROFILE ADAPTATION** | **VERY LIKELY DIRECT** | **LIKELY / VERIFY FIRST** | **LIKELY same MOST family; geometry differs** | **LIKELY / VERIFY FIRST** | **VERY LIKELY DIRECT** | **VERY LIKELY DIRECT** | downstream stack mostly reusable; use MU1438-like AirPlay profile, not MU1440 assumptions |
| **AU37X P5089 MU1326** | **PROFILE ADAPTATION** | **LIKELY / VERIFY FIRST** | **LIKELY / VERIFY FIRST** | **strong low-level MOST/isoTX2 contract; productive VC map route still unproven, LVDS selector present** | **NEW PATCH / PATH** | **NEW PATCH / PATH** | **NEW PATCH / PATH** | new AirPlay profile + Audi fwhmi; verify sink/ownership before live takeover |
| **Audi AUG22 K3346 MU1438** | **PROFILE ADAPTATION** | **NEW PATCH / PATH as current sink** | **NEW PATCH / PATH** | **known architecture mismatch: Audi B9 large map is LVDS J794 -> J285** | **NEW PATCH / PATH** | **NEW PATCH / PATH** | **NEW PATCH / PATH** | source-side AirPlay work is reusable; complete MU1440 MOST stack is not |

The matrix now includes the six closed Wave-1 baselines plus the processed AU37X P5089/MU1326
candidate. AU37X P5153/MU1326 remains `SOURCE_MISSING`; no P5089↔P5153 equivalence is inferred.

---

# 3. Why VWG13 is currently the strongest direct-reuse candidate

For:

```text
MHI2_ER_VWG13_K4525_MU1367
```

the corpus shows:

- complete `libairplay.so` is byte-identical to MU1440;
- `displaymanager`, `dio_manager` and `smartphone_integrator` are functionally closest to the
  MU1440 family;
- the production routing config retains MOST and `/dev/mlb/isoTX2`;
- 26,194 of 26,291 common recovered Java classes are byte-identical to MU1440;
- the important `mostkombi` classes used by the rate-control path are byte-identical.

Therefore the **existing patch concepts and several exact patch bytes are strong first-test
candidates**.

What is *not* proven:

- actual cluster hardware/revision;
- productive context/display geometry;
- runtime loader/preload behavior;
- that the DisplayManager write path reaches `isoTX2` through exactly the same libc call sequence;
- complete NavIgnore eight-class compatibility;
- real vehicle STOCK -> DIRECT -> STOCK recovery.

---

# 4. SEG11: high software reuse, geometry still matters

For:

```text
MHI2_ER_SEG11_P4709_MU1447
```

the complete `libairplay.so` is also byte-identical to MU1440 and the native service layer is
MU1440-nearest.

The direct output path is a strong MOST/`isoTX2` candidate, but the production display configuration
belongs to the 800×480-style routing/config group rather than the exact MU1440 geometry group.

Therefore:

- source-side GEN2: **very strong direct candidate**;
- remux framing: **very strong direct candidate**;
- gate mechanism: **strong candidate, runtime-probe first**;
- geometry/ViewArea: **target-specific test mandatory**;
- Java Most20FPS/Direct-VC owned classes: **exact stock class ABI match**.

---

# 5. SKG11 / VWG11: downstream reuse is stronger than AirPlay reuse

The G11 pair shares one exact recovered Java profile:

```text
25,892 / 25,892 class paths and class bytes identical
```

and several downstream services cluster together.

However their AirPlay layer does not equal MU1440.

## SKG11

SKG11 has its own complete `libairplay.so` hash. The fixed set of 16 project AirPlay target
functions is byte-identical to the Audi-MU1438 target functions, not to the full MU1440 library
profile.

The safe conclusion is:

> **reuse the GEN2 source/design, but generate and verify an SKG11 target profile before loading it.**

Do not bypass the current MU1440 hash gate.

## VWG11

VWG11's complete `libairplay.so` is byte-identical to Audi AUG22 MU1438.

That makes it a strong candidate for an eventual **MU1438-like AirPlay target profile**, not for
blindly declaring the existing MU1440 receiver binary compatible.

The downstream MOST/`isoTX2` architecture is nevertheless much closer to the MQB reference than the
Audi B9 output path is.

---

# 6. Most20FPS: unusually strong portability evidence

The existing Most20FPS patch owns exactly:

```text
de/vw/mib/asl/internal/mostkombi/streamsink/usecases/ChangeDataRateSequence.class
```

Across all five Škoda/VW/SEAT corpus baselines:

```text
MU1440
SKG11 MU1433
VWG11 MU1427
SEG11 MU1447
VWG13 MU1367
```

the **stock target class is byte-identical**:

```text
bytes:
11852

SHA-256:
cce0e89c50ba363e33f5b88474041cffc659723a13e41f92d6dbd818140bcc64
```

That is substantially stronger evidence than package-name similarity.

### Estimate

For those five MQB/SEAT targets:

**Most20FPS JAR bytecode: VERY LIKELY DIRECT**

But installation still requires verifying:

- the target J9 bootclasspath mechanism;
- the exact `lsd.sh` insertion point;
- no competing class override;
- the actual running J9 command line after reboot.

Audi AUG22 uses a different HMI/display-ownership architecture and this exact `mostkombi`
override is not the right direct patch there.

---

# 7. Direct-VC two-class Java policy

The experimental Direct-VC policy owns:

```text
de/vw/mib/asl/internal/mostkombi/streamsink/usecases/ChangeDataRate.class
de/vw/mib/asl/internal/mostkombi/streamsink/usecases/ChangeDataRateSequence.class
```

Both stock classes are byte-identical across all five Škoda/VW/SEAT baselines.

`ChangeDataRate.class`:

```text
bytes:
14152

SHA-256:
3c5a437772f7cbab1a348060215758cb05fcfcf668b47eddc66d5d98f6dac338
```

`ChangeDataRateSequence.class`:

```text
SHA-256:
cce0e89c50ba363e33f5b88474041cffc659723a13e41f92d6dbd818140bcc64
```

The immediate service adapters are also byte-identical across those five targets:

```text
DisplayManagementAdapter.class
SHA-256 62218e804842f4ed44d77967ba9b6892455eeab73952089b9407885be82e9dd7

NavigationMapAdapter.class
SHA-256 46c1829ed6ba9b8e6e339fb697402033f6eb962f25267a3b9d3c1ffba092cd55
```

Therefore the **class ABI seam used by this policy is currently the strongest cross-brand Java
portability result in the corpus**.

This does not make the Direct-VC policy the preferred production takeover. The vehicle-proven
production path remains the native DisplayManager write gate.

---

# 8. NavIgnore: promising, but do not overclaim it yet

The published NavIgnore JAR owns the eight navigation/CarPlay/Android-Auto arbitration classes left
after `ChangeDataRateSequence.class` is split out.

The five Škoda/VW/SEAT JXEs show very high overall Java reuse and an almost completely identical
`mostkombi` island, so direct NavIgnore reuse is a reasonable first hypothesis.

However, the completed corpus closure did **not** yet publish an exact eight-class stock-target
compatibility gate for every NavIgnore-owned class.

Therefore the current rating is:

```text
VWG13 / SEG11 / SKG11 / VWG11:
LIKELY / VERIFY FIRST
```

Before enabling NavIgnore on another train, compare all eight owned class paths against that target's
converted JXE:

```text
class present?
stock bytecode SHA?
method/signature compatibility?
dependencies present?
```

If all eight stock target classes match the reference ABI/bytes, this rating can be promoted to
**VERY LIKELY DIRECT**.

For Audi AUG22 the known Java/HMI ownership architecture is different. A new Audi-specific
navigation-arbitration patch should be assumed.

---

# 9. Direct-TS remux portability

`direct-ts-remux` is project-owned and sits downstream of the stock AirPlay receiver.

It does not depend on private OEM function addresses. Its important target contract is:

```text
Annex-B H.264
 -> MPEG-TS
 -> 64 × 188 B
 -> 12032-byte application writes
 -> productive cluster-video endpoint
```

For the five Škoda/VW/SEAT baselines, static routing evidence consistently includes:

- MOST encoder infrastructure;
- `/dev/mlb/isoTX2`;
- the same broad QNX/Harman video stack;
- very stable `devp-iso-mmx-mib2` code.

Therefore the **remux binary itself is a very strong reuse candidate**.

The part that still has to be proven per vehicle is the sink contract:

- is `isoTX2` the productive cluster-map endpoint on this fitted cluster?
- does it retain the same 64×188/P64 message contract?
- what encoded geometry should be used?

Do not infer those three facts solely from the presence of the device/config entry.

---

# 10. DisplayManager `isoTX2` gate portability

The gate is a process-local libc interposer. It does not patch a hard-coded DisplayManager address.

It tracks:

```text
open/open64("/dev/mlb/isoTX2")
writev(tracked_fd, ...)
close(tracked_fd)
```

and in DIRECT mode swallows only the tracked stock payload while reporting successful writes.

That design is intrinsically more portable than an offset patch.

For SKG11/VWG11/SEG11/VWG13 the static corpus supports the same MOST/`isoTX2` family, but their
DisplayManager executables are not identical.

Therefore the rating is **LIKELY / VERIFY FIRST**.

The minimum target proof is read-only/stock-safe:

1. preload the gate while remaining in STOCK;
2. prove `loaded=1`;
3. prove the expected `isoTX2` fd is tracked;
4. observe normal stock `writev` traffic and block size;
5. do not enter DIRECT yet;
6. only then perform a bounded known-video takeover test.

If the target DisplayManager uses another syscall/path/endpoint, build a new gate profile rather than
forcing the existing one.

For Audi AUG22 the known large-map presentation path is LVDS J794 -> J285, so an `isoTX2`
DisplayManager gate is the wrong output-ownership mechanism.

---

# 11. Audi AUG22: reuse the source side, redesign the sink side

For:

```text
MHI2_ER_AUG22_K3346_MU1438
```

the corpus found strong classic Harman/AirPlay structural similarity, including lifecycle gate
similarities.

But it also found:

- different `libairplay.so` implementation and object-layout offsets;
- Audi-specific HMI/Kombi ownership classes;
- a different display/presentation architecture;
- OEM evidence that the B9 Virtual Cockpit's large navigation map travels over **LVDS from J794 to
  J285**, not the reference MQB MOST Direct-TS path.

Therefore split the Audi port into:

### Reusable concept/source

- ScreenAlt / stream-111 interception;
- key/config/IDR handling;
- much of the AirPlay integration architecture;
- diagnostics and state machine.

### Target profile required

- exact Audi AirPlay ABI/object offsets;
- target-specific lifecycle hooks and validation.

### New path required

- final video presentation/output;
- ownership/gating on the Audi LVDS/display path;
- navigation arbitration;
- Java rate-control policy if needed.

The existing `direct-ts-remux -> /dev/mlb/isoTX2` path should **not** be used as the default Audi B9
port plan.

---

# 12. AU37X P5089: native source side is reusable, Java ownership is not

For:

```text
MHI2_ER_AU37X_P5089_MU1326
```

the new corpus pass shows a mixed but useful portability picture.

## AirPlay / GEN2

P5089 introduces a new complete `libairplay.so` executable profile.

Against the existing six profiles, the fixed 16 target functions are not byte-compatible as a
drop-in MU1440 hook set:

- only `AES_CTR_Final` is byte-identical in every pairwise comparison;
- 11/16 target functions share mnemonic shape with the MU1440/SEG11/VWG13 family;
- `AirPlayReceiverSessionSetSecurityInfo` has a different function hash;
- the observed session/security fields are shifted by +8 bytes relative to AUG22 MU1438.

Therefore:

```text
existing MU1440 GEN2 binary: DO NOT REUSE
GEN2 architecture/source:   REUSE WITH NEW AU37X TARGET PROFILE
```

## Low-level video transport

P5089 provides unusually strong static evidence for the same low-level MOST transport contract:

```text
devp-iso-mmx-mib2:
  exact full-file match to SEG11/MU1447

startup.sh isoTX2:
  -T -S188 -i3 -B3 -P64 -Q18 -m/dev/mlb -MisoTX2

displaymanager config:
  MOST present
  isoTX2 referenced
```

That is strong evidence for the same basic 188-byte MPEG-TS / P64 transport substrate used by the
MQB targets.

However the same configuration also contains:

```text
force_kombi_type=lvds
secondary output = Tegra:HDMI0 / display ID 4
RVC geometry = 528x384 at (0,54)
topview = 800x480
```

and the HMI ownership line is Audi `de.audi.tghu.fwhmi.*`.

Therefore keep two questions separate:

```text
LOW_LEVEL_MOST_CONTRACT
  -> strong static match

PRODUCTIVE_CLUSTER_MAP_ROUTE
  -> still needs vehicle/runtime proof
```

The project-owned `direct-ts-remux` remains a strong reusable component, but its current
`/dev/mlb/isoTX2` sink must not be assumed productive until stock-safe observation confirms it.

The libc-based `isoTX2` gate is also a promising mechanism because it does not contain a hard-coded
DisplayManager function offset, but P5089's DisplayManager is a new RX/code profile. First test must
remain STOCK-only and prove that DisplayManager actually opens/writes the tracked endpoint.

## Java/HMI patches

P5089 and AUG22 MU1438 follow the Audi `fwhmi` ownership line.

P5089 has no:

```text
de.vw.mib.asl.internal.mostkombi.streamsink
NavigationMapAdapter
DisplayManagementAdapter
```

class architecture used by the current MQB patches.

Therefore:

```text
Most20FPS:       NEW PATCH / PATH
Direct-VC Java:  NEW PATCH / PATH
NavIgnore:       NEW AUDI-SPECIFIC ARBITRATION PATCH
```

Do not attempt to load the MQB class-replacement JARs on AU37X.

## Independent P5089 prior art

The research corpus already tracks `chefranov/mhi2-au37x-carplay`, whose documented tested target
is this same P5089/MU1326 family. That work independently validates a HARMAN native/J9 environment
around `dio_manager`, `mm-ipod` and `libiap2client.so.1` for other CarPlay features.

It is useful corroboration of the source-side platform, but it does **not** prove AltScreen map-video
routing.

---

# 13. Recommended first vehicle test by firmware

## VWG13 MU1367

Highest-value next MQB test:

```text
compatibility-report
 -> exact component/class check
 -> gate loaded in STOCK only
 -> observe isoTX2/writev contract
 -> bounded known MPEG-TS test
 -> stock recovery
 -> GEN2 Stream-111 test
 -> NavIgnore separately
```

## SEG11 MU1447

Same sequence, but resolve target cluster geometry before judging rendering quality.

## SKG11 / VWG11

Do the downstream gate/route proof independently, but **do not start live GEN2 with the MU1440
AirPlay assumptions**. Build/verify the appropriate AirPlay profile first.

## AU37X P5089 MU1326

Start with:

```text
compatibility-report
 -> confirm exact P5089 component hashes
 -> preload isoTX2 gate in STOCK only
 -> observe open/writev target and block contract
 -> determine whether isoTX2 is the productive fitted-cluster map route
 -> build/verify the AU37X AirPlay target profile
 -> only then attempt bounded Stream-111 + sink takeover
```

Do not load MQB NavIgnore/Most20FPS/Direct-VC Java JARs: the required MQB class ownership architecture
is absent.

## Audi AUG22 MU1438

Do not start with the MU1440 Direct-TS takeover.

Start with:

```text
read-only compatibility collection
 -> Audi AirPlay profile validation
 -> identify exact LVDS display/context/geometry
 -> identify stock owner and controllable arbitration seam
 -> build bounded Audi sink/ownership experiment
```

---

# 14. How this estimate was produced

The ratings are based on the completed six-baseline firmware corpus, not train-name guessing.

## Exact source extraction

The generic MHI2/MHI2Q firmware toolkit extracted normalized firmware trees from exact update
archives and recorded source/member hashes.

## Full corpus rehash

Wave 1 independently rehashed:

```text
74,574 / 74,574 materialized regular files
```

with no unexplained mismatch in the closure gate.

## Native comparison

A fixed native set was compared using:

- full-file SHA-256;
- executable PT_LOAD / RX identity;
- real `.text` identity where applicable;
- dynamic imports/exports;
- `DT_NEEDED`;
- function-level hashes;
- focused Ghidra decompilation for genuinely new profile-forming code.

Wave-1 closure included:

```text
12 targeted new Ghidra inputs
0 export failures
```

## Java/JXE comparison

Each distinct `lsd.jxe` was reconstructed with the current internal JXE comparison workflow.

Classes were compared by:

- exact class path;
- class byte length;
- class SHA-256.

This is what allows statements such as:

```text
ChangeDataRateSequence.class is byte-identical across all five MQB/SEAT baselines
```

rather than merely “the decompiled source looks similar”.

## Config/routing comparison

Production JSON and startup evidence were compared both by raw bytes and normalized semantics,
including:

- DisplayManager routing;
- MOST/`isoTX2`;
- queue/frame values;
- LVDS/HDMI markers;
- smartphone/AirPlay preload;
- J9 bootclasspath/startup.

## Evidence limitations

This corpus is static firmware evidence.

It cannot by itself prove:

- the fitted cluster revision;
- the active runtime display route;
- QNX loader precedence;
- exact vehicle-state arbitration;
- recovery behavior;
- decoder acceptance of an untested geometry.

Those are vehicle-test gates.

---

# 15. Practical interpretation

The current evidence suggests three broad porting classes:

```text
Class 1 — near-direct MQB reuse
  VWG13
  SEG11

Class 2 — same downstream architecture, AirPlay-profile adaptation
  SKG11
  VWG11

Class 3 — Audi HMI ownership, target-specific source/output validation
  AU37X P5089

Class 4 — shared source-side concepts, known different cluster-output architecture
  Audi AUG22
```

This is the useful outcome of the corpus: we do **not** need to assume one completely new solution per
firmware train, but neither should we flatten distinct display/ownership architectures into one
unsafe universal patch.

See also:

- [MHI2 cross-firmware profile map](MHI2_FIRMWARE_PROFILE_MAP_2026-09-28.md)
- [compatibility matrix](../../testing/COMPATIBILITY_MATRIX.md)
- [Direct VC video path](../../architecture/DIRECT_VC_VIDEO_PATH.md)
- [NavIgnore architecture](../../architecture/NAVIGNORE.md)
