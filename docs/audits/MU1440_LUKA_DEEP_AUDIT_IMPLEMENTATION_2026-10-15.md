# MU1440 vs LuKa MHI2Q — deep-audit decisions and implementation (2026-10-15)

Status: **isolated GEN2 source candidate, NOT a vehicle installer or a claim of QNX/car validation**. Parent: `work/mu1440-tcp-nodelay-ab-v1` @ `da65e405eb5be4f4ab0840188af62415c5746bdc`. Reference: LuKa `MHI2Q-2026-10-14`. These are design comparisons, not a wholesale MHI2Q port.

## Decisions from review

| Topic | Decision | Implementation |
| --- | --- | --- |
| A1 control SETUP enabledFeatures | Preserve the **receiver's stock accepted** array and append only actually implemented `altScreen`, `viewAreas` (plus classic `iAPChannel` where configured). Never copy the iPhone's proposed `features`. | `merge_reference_features`; typed array guard and duplicate guard; control SETUP only, not media SETUP |
| A2 stock/main display | Real stock `display[0].uuid` controls stream 110. Never fabricate or change its UUID; cluster UUID must differ. | Stock-display clone with identity check; stock-only fallback on failed preflight |
| A3 incomplete 111 setup | Advertise `dataPort`/111 only after listener, local projection and full descriptor build; read back the descriptor. A pure 111 failure returns a real setup error (-6700). A failed optional 111 in a mixed 110/111 request preserves stock 110 success. | GEN2 same-session cold preflight plus transactional response publication |
| A4 complete display schema | Keep two independent displays and two parser-facing identities. Do not transplant an Audi UUID/geometry. | `displays` and `displayPanels`, `uuid` and `uid`, non-empty `initialVideoStreams` with true main UUID / configured cluster UUID, cluster `properties:["Instrument Cluster"]`; full or stock fallback |
| U1/U2 upstream receiver, crypto and 128-byte ScreenStream header | Existing MU1440 receiver and stock per-screen key derivation are retained; no blind binary/code port from MHI2Q. | No change |
| V1 asynchronous forwarding and bounded queue | Keep source TCP draining / AES-CTR independent from local nonblocking output. | Existing workers retained; queue now 32 complete AUs / 8 MiB |
| V2/V4 backpressure, overflow and recovery | No hard consumer reset for a merely full/stale queue. Detect >1000ms **local monotonic** age only if at least two AUs are queued; never infer queue age from source 32.32 and never drop a static single AU. Discard unsent tail, retain an AU that has put **any M1AU header/payload bytes on TCP**, drain it, then require a fresh IDR with current SPS/PPS. Preserve AES continuity, consumer generation and framing. | `alt111_video_submit_timed_at`, 32 AUs / 8 MiB, `ALT111_SOFT_RESYNC`, wire pin, single post-drain keyframe intent |
| V3 TCP_NODELAY | A/B switch only on GEN2 -> local consumer TCP socket, not iPhone/MOST. Default = off. | Inherited `/tmp/mibr-alt111-tcp-nodelay.enabled`, 250 ms poll, readback and log |
| R1 bridge evidence / renderer STATUS | Do not port LuKa's OMX/EGL renderer into M1AU -> TS -> MOST. Separate a locally delivered IDR from a **writer-accepted** IDR of the same stream/codec/consumer/ordinal. Demand >1s and a new status sample with newly accepted output blocks before declaring BRIDGE_RECOVERED. Neither marker proves physical VC presentation. | Passive parity writer `output_last_idr_completed_*` telemetry, `alt111_bridge_status.h` freshness parser, resync states `SOURCE_RECOVERED` -> `BRIDGE_PENDING` -> `BRIDGE_RECOVERED`. Optional OMX HELLO_EX/STATUS remains deferred |
| Source timestamps / T1 | Preserve exact source timestamp bytes and ordinal; do not treat remote timestamps as local queue age or alter PTS/PCR/writer pacing. | No changes to 56-byte M1AU schema or downstream clock constants |
| T3 status overhead | Existing parity status remains <=1 Hz plus state changes. We explicitly decided not to refactor status/output hot paths for this vehicle test. | Unrelated source-interval cache experiment reverted; only passive exact-IDR telemetry added to existing parity status publication |
| Keyframe cadence / FPS | Keep current tested maxFPS=30 profile (not raising to 40); producer-frame policy default 20 frames, configured settings remain authoritative. At 30 fps, 20 frames are ~0.67 s, **not 0.5 s**. Do not use lack of IDR alone as a 1-Hz watchdog. | No unrelated cadence/decoder experiment |
| I1 installer hardening | Full public installer/staging/preflight/rollback remains a separate publication milestone. Do not slow the present development iteration by rebuilding frozen R5 or modifying a vehicle. | Not changed |

### Queue overflow invariant

The output path already serializes its final peek, socket send and advance under `g2_core_lock`. On overflow the queue core drops *only* unsent entries. A head is pinned if either its M1AU header has started (`alt111_video_mark_wire_started`) or payload `offset>0`. A pinned head is allowed to finish; new arrivals continue being read/decrypted but are discarded until that head drains. Then one post-drain keyframe intent is queued, and the **next** complete IDR is emitted with config prefix. If no head was started, the whole queue is discarded immediately and the next complete IDR can prime. Consumer/socket generations do not change on this soft failure. Real bad codec configuration, invalid AU, memory failure and TCP disconnect remain separate fault classes and may still detach.

The A/B knob does not prove or fix the VC striping artifact; QNX MOST/VC decoding is downstream, untouched. This batch is intentionally limited to GEN2/111. `writev_gate`, parity ownership, /dev/mlb/isoTX2 and direct remux are out of scope.

### Host acceptance

`Fast MU1440 Luka audit regression` is a small push-triggered workflow (no target install and no public-release preflight). It syntax-checks the actual GEN2 adapter, runs `tests/alt111_video_queue_recovery_test.c` under ASan/UBSan (pinned partial M1AU header, raw partial payload, unsent head, stale ticket and post-drain IDR), and runs the V3 off/on/off socket smoke test. Confirm final run status before calling it passed.

### Target validation still needed

1. Produce a QNX 6.5 ARMv7 developer binary from this exact branch and inspect compiler/link diagnostics.
2. Parked vehicle test: ordinary stock 110 first; then 111 from /info -> control SETUP -> media SETUP, one-/two-view settings, fast disconnect/reconnect; no fake main UUID and no blank main display.
3. Controlled backpressure/recovery pilot; ensure no truncated M1AU header/payload, exactly one owner, a fresh priming IDR, no permanent disappearance. Measure source and local consumer progression, not inferred VC presentation.
4. A/B `TCP_NODELAY` with same route, FPS, policy and source; compare logs and visible behavior.
5. Public installer transaction/rollback **later**, not in this test candidate.

No QNX target build, package, flashing or car-side change is implied by the source/host CI result.


## Final targeted acceptance / parked-vehicle protocol

**Source candidate:** `work/mu1440-luka-audit-complete-20261015`. Draft target-build PR: https://github.com/harman-f/mhi2_altscreen_carplay/pull/48 . Do NOT use old R5 installer with these unqualified binaries; it is intentionally not repackaged here.

1. Developer build: `build-altscreen111-gen2.yml` and `build-direct-ts-parity.yml` must each complete successfully for the **same HEAD source SHA**. Host syntax/ASan tests do not substitute for QNX build.
2. While parked, preserve/record the current deployed GEN2/parity SHA and the normal stock 110 baseline first. Test standalone 111 and mixed 110/111; main `uuid` must remain the real stock UUID. Include 1-view and 2-view profiles, disconnect/reconnect.
3. Keep parity status enabled (default `MIBR_PARITY_STATUS=1` unless overridden) to allow a **bridge-evidence** recovery verdict. Check `/tmp/mibr-alt111-gen2.status` for queue and recovery stages, and `/tmp/mibr-parity-ts.status` for `output_last_idr_completed_sequence/stream/codec/consumer`, `blocks_written` and `clock_snapshot_mono_us`. `SOURCE_RECOVERED` alone is not success.
4. Generate controlled local backpressure only when safe, verify that an already-begun M1AU header/body finishes and that the next priming IDR is fresh. Confirm stock handback/one writer and no physical VC presentation claim from internal counters.
5. V3 local TCP A/B after installation: `rm -f /tmp/mibr-alt111-tcp-nodelay.enabled` = OFF, `: > /tmp/mibr-alt111-tcp-nodelay.enabled` = ON. Compare like-for-like sessions; this does not toggle the phone's socket or MOST.
6. A disabled/missing/stale parity status file must produce **BRIDGE_PENDING**, not a fabricated `BRIDGE_RECOVERED`. Disable/rollback the test separately if status or projection deviates. Public transactional installer/rollback remains a later publication milestone.

No modified PTS/PCR constants, no ownership changes, no 40-FPS or decoder-striping fix, and no automatic vehicle installation.
