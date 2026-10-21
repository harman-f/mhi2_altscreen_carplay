> **Historical research snapshot (2026-10-03).** This page is retained to preserve original evidence labels. Start with [current October integration status](../status/INTEGRATION_STATUS_2026-10-21.md), [new research index](../research/README.md) and [October fault/vehicle observations](OCTOBER_2026_VEHICLE_AND_TIMING_EVIDENCE.md). The phrase “newest” below only reflects this snapshot's original date.

# Historical research status — 2026-10-03

> [!NOTE]
> For the newest cross-track findings after this status snapshot, see the [current research preview](../research/CURRENT_RESEARCH_PREVIEW_2026-10-05.md), especially the source-timestamp/keyframe design, DMDT-vs-writev ownership distinction, HMI WidgetFactory seam and steering-wheel input work.

Last major architecture review: **2026-10-03**

This page separates what is proven from what is implemented, inferred, still under test or explicitly
deferred.

## Evidence vocabulary

| Label | Meaning |
| --- | --- |
| **VEHICLE-PROVEN** | directly demonstrated on the real reference vehicle/unit |
| **BINARY-CONFIRMED** | supported by exact binary reverse engineering |
| **BUILD-CONFIRMED** | implementation/toolchain builds and validation passes |
| **IMPLEMENTED** | present in the current engineering implementation |
| **OPEN** | not yet resolved |
| **DEFERRED** | intentionally not part of the current milestone |

---

## End-to-end media path

| Item | Status | Notes |
| --- | --- | --- |
| CarPlay secondary navigation stream exists | **VEHICLE-PROVEN / BINARY-CONFIRMED** | Dedicated Auxiliary/ScreenAlt architecture |
| Stream type 111 used for the secondary nav display | **VEHICLE-PROVEN / BINARY-CONFIRMED** | Independently corroborated beyond the first target corpus |
| MU1440 can receive/decrypt the stream | **VEHICLE-PROVEN** | Current baseline |
| H.264 can be remuxed directly to MPEG-TS | **VEHICLE-PROVEN** | No decode/re-encode required for baseline |
| MPEG-TS -> MOST150 -> VC path works | **VEHICLE-PROVEN** | Apple Maps visibly rendered in the real VC |
| Fundamental MOST redesign needed | **NO CURRENT EVIDENCE** | Do not reopen without contrary trace evidence |

---

## VC transport and native map takeover

| Item | Status | Notes |
| --- | --- | --- |
| `/dev/mlb/isoTX2` is the Kombi map video injection path | **VEHICLE-PROVEN** | Exact MU1440 target |
| Driver/application message contract is 64 × 188 = 12032 bytes | **VEHICLE-PROVEN** | Strict complete writes |
| Native and custom writers compete when both are active | **VEHICLE-PROVEN** | A/B vehicle test |
| Whole DisplayManager `SIGSTOP/SIGCONT` proves takeover concept | **VEHICLE-PROVEN / HISTORICAL** | Coarse first proof only |
| Process-local DisplayManager `writev` gate suppresses native payload | **VEHICLE-PROVEN** | DisplayManager PID remains alive |
| Custom writer remains unaffected by the process-local gate | **VEHICLE-PROVEN** | Separate process |
| Clearing the gate restores the native map | **VEHICLE-PROVEN** | Clean STOCK recovery |
| NavIgnore keeps normal Kombi MAP_VIEW available during smartphone navigation | **VEHICLE-PROVEN** | Required for the proven full visible path |
| Java Rate-0 policy is the current production takeover | **NO** | Separate build-confirmed policy/research line |

See [Direct VC video path](../architecture/DIRECT_VC_VIDEO_PATH.md).

---

## Sender lifecycle

| Item | Status | Notes |
| --- | --- | --- |
| Auxiliary/ScreenAlt is a dedicated sender concept | **BINARY-CONFIRMED** | Dedicated setup path and identity |
| Normal provider change recreates type 111 | **NOT SUPPORTED** | Current exact sender evidence says ordinary ownership/UI changes reuse the existing stream |
| Real endpoint/session topology change can recreate 111 | **BINARY-CONFIRMED** | Genuine SETUP/TEARDOWN path exists |
| SecondDisplayMode applies in-place to existing ScreenStream | **BINARY-CONFIRMED** | Not a stream-generation boundary |
| forceKeyFrame restarts current bitstream | **BINARY-CONFIRMED** | Recovery primitive on existing stream |
| ViewArea update requires new Type-111 stream | **NOT SUPPORTED** | Same-session mechanism |

---

## UI contexts

| Item | Status | Notes |
| --- | --- | --- |
| Base instrument-cluster URL | **BINARY-CONFIRMED** | Generic/root context |
| `/map` URL | **BINARY-CONFIRMED** | Persistent map-oriented context |
| `/instructioncard` URL | **BINARY-CONFIRMED** | Transient maneuver/instruction-card context |
| Fourth classic `maps:/car/instrumentcluster/...` role found | **NO** | Current exact iOS 27.2 pass closes the classic family at base + map + instructioncard |
| Three URLs mean three streams | **FALSE / NOT SUPPORTED** | They are UI roles |
| `suggestUI([])` used on normal trip finish/cancel | **BINARY-CONFIRMED** | UI withdrawal |
| `suggestUI` automatically triggers `showUI` | **NOT SUPPORTED** | Distinct control operations |

---

## MU1440 receiver / control plane

| Item | Status | Notes |
| --- | --- | --- |
| Type-111 receive path | **VEHICLE-PROVEN** | Stable baseline |
| Passive capture of inherited cluster URL capabilities | **IMPLEMENTED** | Used to observe stock values before synthesizing new ones |
| Serialized showUI/stopUI/forceKeyFrame command path | **IMPLEMENTED** | Current GEN2 engineering line |
| Same-session bounded reacquire sequence | **IMPLEMENTED / UNDER TEST** | stopUI -> showUI -> forceKeyFrame |
| Correct receiver-side behavior across every provider handover | **OPEN** | Current primary research target |
| Need to synthesize 111 teardown on provider switch | **NO CURRENT EVIDENCE** | Explicitly avoided |
| HID/Knob required on MU1440 | **OPEN / DEFERRED** | Current profile intentionally no-HID |
| Multi-ViewArea protocol behavior | **BINARY-CONFIRMED / IMPLEMENTED SCAFFOLD / VEHICLE-OPEN** | Same-screen preset selection is understood; current GEN2 advertises only one ViewArea |
| Arbitrary live SafeArea rectangle mutation | **NOT SUPPORTED BY CURRENT EVIDENCE** | SafeArea is negotiated per ViewArea; live change means selecting a predeclared ViewArea |

---

## Consumer synchronization

| Item | Status | Notes |
| --- | --- | --- |
| VideoConfig tracked transactionally | **IMPLEMENTED** | Current GEN2 |
| Complete-AU validation | **IMPLEMENTED / VALIDATION CONTINUES** | Protects consumer contract |
| Consumer waits for config + complete IDR | **IMPLEMENTED** | Generation-safe priming |
| Stream/codec/consumer generation fencing | **IMPLEMENTED** | Rejects stale lifecycle events |
| Bounded queue | **IMPLEMENTED** | Prevents unbounded stale media accumulation |
| Delivered-AU telemetry | **IMPLEMENTED** | Used to classify freezes |
| Current app-handover fix proven on vehicle | **OPEN** | Requires current controlled trace |

---

## Java / Virtual Cockpit ownership

| Item | Status | Notes |
| --- | --- | --- |
| Stock Java display policy identified | **BINARY-CONFIRMED** | DSI/DisplayManagement path |
| Direct-VC policy build island | **BUILD-CONFIRMED** | Small two-source build model |
| Raw DSI state preserved | **IMPLEMENTED** | Policy does not spoof the raw state |
| Java policy can derive an effective producer rate while preserving raw DSI state | **BUILD-CONFIRMED / IMPLEMENTED** | Separate from the vehicle-proven `writev` takeover gate |
| Reboot stock fallback | **DESIGN REQUIREMENT / IMPLEMENTED IN POLICY** | No persistent volatile lease |
| Passive VC view-state probes | **IMPLEMENTED AS SIDE TRACK** | Current compilation validation for latest listener may still be pending |
| Final AID screenshot composition capture | **OPEN** | DMDT/display-manager screenshot lead exists, final coverage not proven |

---

## Cross-firmware corpus

The first six-baseline MHI2 corpus pass is **complete and verified**.

It covers:

- Audi AUG22 K3346 MU1438;
- Škoda SKG13 P4526 MU1440;
- Škoda SKG11 K3343 MU1433;
- Volkswagen VWG11 K3342 MU1427;
- SEAT SEG11 P4709 MU1447;
- Volkswagen VWG13 K4525 MU1367.

Important result: train names do not map one-to-one to implementation profiles.

Examples:

- Audi MU1438 and VWG11 share a byte-identical complete `libairplay.so`;
- MU1440, SEG11 and VWG13 share another byte-identical AirPlay profile;
- SKG11 has a distinct AirPlay file but the 16 project target functions match the Audi profile;
- SKG11 and VWG11 have different JXE containers but exactly the same 25,892 recovered class paths
  and class bytes;
- 97 of 98 `de/vw/mib/asl/internal/mostkombi/` classes are byte-identical across the five
  Škoda/VW/SEAT baselines;
- profile-forming native services split SKG11/VWG11 toward the MU1438 family and SEG11/VWG13 toward
  the MU1440 family.

The completed corpus run passed a 74,574-file independent rehash, 12 targeted Ghidra runs with zero
export failures, and a curated 45-file evidence hash audit.

AU37X P5089/MU1326 has now been processed as a standalone seventh corpus profile. P5153/MU1326
was not found locally, so there is still no same-family P5089↔P5153 equivalence result.

P5089 adds a distinct AirPlay/native profile and Audi `fwhmi` Java ownership. Its static startup
still shows the familiar `devp-iso-mmx-mib2 -S188 -P64 -Q18 ... -MisoTX2` low-level MOST
contract, while `force_kombi_type=lvds` and the fitted-cluster productive route remain separate
runtime questions.

Before another firmware family is admitted, the remaining P5089 evidence-closure items are:

- independent 89,922-row disk rehash;
- exact eight-class NavIgnore compatibility matrix;
- explicit Audi presence/absence gate for Most20FPS / Direct-VC Java classes;
- small native-evidence Git-blob audit;
- supporting-native and prior-art reconciliation.

The canonical AUG22/MU1438 corpus target remains `MHI2_ER_AUG22_K3346_MU1438`.

See [MHI2 cross-firmware implementation profile map](../research/MHI2_FIRMWARE_PROFILE_MAP_2026-09-28.md).

---

## Current leading diagnosis

The project is no longer blocked on basic media feasibility.

The leading open problem is:

> **correct receiver-side CarPlay secondary-display/UI ownership and same-session refresh during
> navigation lifecycle changes.**

In practical terms:

```text
working Apple Maps in VC
        │
        ▼
navigation provider / route state changes
        │
        ▼
same type-111 stream may remain alive
        │
        ├── UI suggestion changes
        ├── navigation ownership changes
        ├── SecondDisplayMode may change
        ├── source may need presentation reacquire
        └── bitstream may need keyframe restart
                │
                ▼
       receiver must keep all states coherent
```

---

## Current trace questions

The next controlled vehicle trace should answer:

1. Does type 111 actually teardown/re-SETUP during the failing handover?
2. If not, do fresh H.264 access units continue?
3. What `suggestUI` sequence is emitted?
4. What `modesChanged` / ownership transition occurs?
5. Does the receiver receive or send `showUI` / `stopUI`?
6. Does a bounded same-session reacquire restore source output?
7. Does a fresh config + complete IDR reach the consumer?
8. If delivered video progresses, does the VC route still remain stale?

Only the last case justifies making downstream MOST/presenter behavior the primary suspect again.

---

## Deferred until lifecycle is stable

- multi-ViewArea layouts;
- Knob/HID integration;
- maneuver-card layout polish;
- speculative type 112;
- local composition;
- additional decoder/encoder pipeline;
- broad RGI/BAP integration;
- cross-brand packaging;
- SD-card end-user installation.

---

## Project rule

A new finding should move between these categories only when there is evidence.

The repository should clearly distinguish:

```text
observed
  !=
inferred
  !=
implemented
  !=
vehicle-proven
```

That distinction is intentional: the goal is to make future work start from a known evidence state
instead of repeating earlier speculation.


---

## 2026-10-03 cluster research closeout

The LIVI/current-iOS/CarPlay-Ultra follow-up is consolidated in
[CARPLAY_CLUSTER_ULTRA_CLOSEOUT_2026-10-03.md](../research/CARPLAY_CLUSTER_ULTRA_CLOSEOUT_2026-10-03.md).

For the current milestone, the static-research questions around classic cluster URL roles,
ViewArea/SafeArea semantics and LIVI's restart behavior are closed. The optional local
CP111-plus-instruments compositor is preserved there as **DEFERRED**, not as a current implementation
requirement.
