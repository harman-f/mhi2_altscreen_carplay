# October 2026 MU1440 vehicle and timing evidence (sanitized)

**Classification:** October 19–20 observed reference-unit sessions and controlled parked fixtures. Aggregated figures only; no personal drive traces, original iPhone bitstreams, map coordinates, raw vehicle logs or private account references are included. Original test material is not part of the public download. This is a research finding, **not a promotion of a new developer release**.

## Four live parity sessions

| Session class | Usable logged duration | Logged PTS−PCR progression | AU input | Sequence gaps | Write errors | Latency/safe recoveries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | ~31 min | ~0.47 → 10.5 s | 47,775 | 0 | 0 | 1 / 1 |
| B | ~31 min | ~0.54 → 10.2 s | 45,607 | 0 | 0 | 14 / 14 |
| C | ~56 min | ~0.09 → 17.8 s | 83,919 | 0 | 0 | 0 / 0 |
| D | ~37 min | ~0.52 → 12.5 s | 57,509 | 0 | 0 | 0 / 0 |

The logged lead grew around 310–330 ms/min across long sessions. This is consistent with the difference between a nominal 12.288-Mbit/s PCR counter model and the effective accepted driver rate, measured around 12.219 Mbit/s in a controlled fixture. It is **not a growing remux queue** and is **not proof** that the physical VC display accumulates 10–18 seconds of delay. Routine 20–25-minute observation did not show the corresponding obvious accumulating visual lag. Avoid speculative PCR-constant changes based only on this diagnostic number.

The single session with 14 latency recoveries did demonstrate intermittent queue-limit crossings and wait-for-IDR drops; that separate mechanism remains a plausible visible interruption source.

## Parked H.264 motion fixture comparison

Controlled variants used the same 1010x376 presentation geometry with 30-fps/20-frame-IDR fixture policy. Native-like Baseline/CAVLC, original iPhone High/CABAC and re-encoded forms were compared with the current parity writer. Native-like and original-style encoding did not establish a fundamental inability of this VC decoder to consume iPhone High-profile tool features. The original captured iPhone motion content looked acceptable on clean fixture replay; re-encoding to Baseline was worse on the compared motion example.

Conclusions: preserve the direct compressed-bitstream path for now, do not add a decode/re-encode stage as an assumed cure, and separate original source cadence/quality, live socket arrival, IDR requests and actual display behavior. Periodic visible quality pulsing on quiet scenes may follow GOP/keyframe quality, but its exact root cause is not yet proven.

## Two distinct observed failure classes (20 October)

| Condition | What was recorded | Interpretation |
| --- | --- | --- |
| Source/session termination | Type-111 TEARDOWN including reason -6753 in some instances; hook clears the source, bridge sees EOF | Source CarPlay session ends. A USB replug restored service in the reported drives. The precise external cause (USB, phone, software interaction) remains unproven. |
| Native gate proof lost | Custom parity writer stops fail-closed while stream 111 can still be marked streaming | Display/owner interlock problem, not proof that the phone's CarPlay session disconnected. |
| Duplicate supervisor launch | Two instances observed; second encounters existing owner lock | The exclusive lock prevents two writers, but the duplicate startup is itself a defect to fix and investigate. |

There were zero counted writer errors and zero sequence gaps in the inspected sessions; this does not establish full upstream CarPlay/session reliability.

## Next qualification

1. Compare stock CarPlay on the same known-good cable/port/phone separately from GEN2/parity, with accurate operator event times.
2. Remove duplicate supervisor invocation without weakening the one-owner lock.
3. Record the reason for native gate-proof loss and independently verify STOCK restoration.
4. Qualify a new GEN2 handshake/soft-recovery candidate with exact hashes, same-session request/response, new source IDR, streaming video and a visible VC result.
5. Keep release/README claims tied to a **specific installed pair and actual physical observations**, not a source-only CI PASS.

See [known issues](KNOWN_ISSUES.md), [current integration status](../status/INTEGRATION_STATUS_2026-10-21.md), and [module ownership](../architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md).
