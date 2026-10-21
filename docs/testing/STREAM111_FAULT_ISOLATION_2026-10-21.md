# Stream-111 fault isolation and same-owner recovery test plan

**Reference:** experimental MU1440 wired CarPlay/Direct-TS setup. This is a read-only first diagnostic method, not an automatic recovery script or a claim that recent source candidates are an approved public release.

## Keep the layers separate

```text
CarPlay / iPhone connection
  -> authenticated original session and SETUP
  -> source-111 TCP connection (advertised negotiated endpoint)
  -> GEN2 codec config / complete H.264 AUs / source timestamps
  -> bounded local M1AU/Annex-B consumer
  -> exclusive direct/parity writer and native gate proof
  -> actual MOST / fitted Virtual Cockpit picture
```

A displayed last frame may remain after the sender stops producing. Conversely, source 111 may still be delivering while the safe owner gate ends the custom writer. The phone connection, private video and stock 110 are not interchangeable status indicators.

## Diagnostic decision table

| Observed state | Next independent evidence | Do not infer |
| --- | --- | --- |
| No source-111 TCP accepted | Check actual SETUP-advertised port, bound receiver and **effective loaded** firewall rule on the correct interface | A successful SETUP alone proves network reachability |
| TCP accepted, no codec/IDR | Observe original GEN2 current session, VideoConfig and new source-delivered IDR separately | A prior IDR from the previous generation can reprime a new session |
| Complete new source AUs, local consumer stalled | Compare source-to-tee AU counters and consumer progress/age, bounded recovery thresholds | Changing PCR or physical MOST ownership will repair missing local input |
| Stream source idle/EOF after TEARDOWN | Distinguish intentional teardown, loss of underlying CarPlay session and independent 110 health | The parity writer caused the upstream disconnect |
| Source 111 still streaming but writer stopped | Check native gate proof, owner lock, current route/generation and stop/STOCK observation | The iPhone disconnected |
| Source and remux advancing but no live picture | Verify accepted output, new config/IDR, actual VC screen route and fitted cluster | A log marked SHOW is physical presentation proof |

The reference default source listener is TCP 6031 on `carplay0` with an existing narrow inbound PF exception. Actual negotiated port is authoritative. The local 19820 tee is separate from inbound phone transport. [Installation prerequisite](../INSTALLATION.md) and [protocol](../research/STREAM111_PROTOCOL.md) retain the complete verified operator notes.

## Reproducible current problems

- Observed sessions include source-session TEARDOWN (reason -6753 in some cases) and **independent** fail-closed writer stop from native gate-proof loss. Neither event establishes an upstream root cause on its own.
- Two supervisor instances were present in one inspected installed state. The owner lock prevented double writing, but a repeated launch should be eliminated without removing the lock.
- Longer sessions reported roughly 25-fps average source cadence and intermittent larger frame intervals. One session had latency recoveries; zero output write errors did not mean the upstream/VC experience was flawless.
- A draft GEN2 candidate studies strict same-session SETUP, bounded backlog, source-delivered versus bridge-accepted IDR and resync. The existence of this source/host evidence is **not** proof of current full vehicle qualification.

## Acceptance for any future recovery candidate

1. Pin the exact original firmware, new binary pair, public source revision and reversible existing backup; no generic cross-firmware installer.
2. Independently show stock 110 and mixed SETUP remain unaffected.
3. Validate bad source packet/codec/config, stale backlog, normal teardown and reconnect without reusing wrong-session AUs.
4. Validate real physical video progression after a fresh IDR (not only source delivery or a writer acceptance counter).
5. Exercise source-side loss and gate-proof loss as **different** failure injections. For gate loss, preserve the one-owner interlock and prove STOCK handback.
6. Measure repeated-boot supervisor count, rollback and reconnect without relying on USB replug as the sole success criterion.
7. Label the result by exact evidence: HOST, QNX BUILD, parked VEHICLE, longer DRIVE and RELEASE are independent states.

See [October aggregated vehicle findings](../findings/OCTOBER_2026_VEHICLE_AND_TIMING_EVIDENCE.md), [known issues](../findings/KNOWN_ISSUES.md), and [current status](../status/INTEGRATION_STATUS_2026-10-21.md).
