# MU1440 vs LuKa MHI2Q — deep-audit decisions and implementation (2026-10-15)

Status: **isolated GEN2 source candidate, NOT a vehicle installer or a claim of QNX/car validation**. Parent: `work/mu1440-tcp-nodelay-ab-v1` @ `da65e405eb5be4f4ab0840188af62415c5746bdc`. Reference: LuKa `MHI2Q-2026-10-14`. These are design comparisons, not a wholesale MHI2Q port.

## Decisions from review

| Topic | Decision | Implementation |
| --- | --- | --- |
| A1 control SETUP enabledFeatures | Preserve the **receiver's stock accepted** array and append only actually implemented `altScreen`, `viewAreas` (plus classic `iAPChannel` where configured). Never copy the iPhone's proposed `features`. | `merge_reference_features`; typed array guard and duplicate guard; control SETUP only, not media SETUP |
| A2 stock/main display | Real stock `display[0].uuid` controls stream 110. Never fabricate or change its UUID; cluster UUID must differ. | Stock-display clone with identity check; stock-only fallback on failed preflight |
| A3 incomplete 111 setup | Advertise `dataPort`/111 only after listener and local projection setup and full descriptor build. A failed optional 111 never destroys stock 110. | `append_alt_setup_response` returns success; on failure release private projection/receiver while returning the original stock response. **Mixed stream SETUP can still return stock success**; no fake private descriptor is appended |
| A4 complete display schema | Keep two independent displays and two parser-facing identities. Do not transplant an Audi UUID/geometry. | `displays` and `displayPanels`, `uuid` and `uid`, non-empty `initialVideoStreams` with true main UUID / configured cluster UUID, cluster `properties:["Instrument Cluster"]`; full or stock fallback |
| U1/U2 upstream receiver, crypto and 128-byte ScreenStream header | Existing MU1440 receiver and stock per-screen key derivation are retained; no blind binary/code port from MHI2Q. | No change |
| V1 asynchronous forwarding and bounded queue | Keep source TCP draining / AES-CTR independent from local nonblocking output. | Existing workers retained; queue loss policy below |
| V2/V4 backpressure, overflow and recovery | No hard consumer reset for a merely full AU queue. Discard unsent dependent tail, retain an AU that has put **any M1AU header/payload bytes on TCP**, drain it, then require new complete IDR with current SPS/PPS. Preserve source AES continuity, consumer generation and M1AU framing. | `alt111_video.c`: `ALT111_SOFT_RESYNC`, `recovery_wait_idr`, `recovery_draining`, wire pin and post-drain keyframe request through existing serialized control worker |
| V3 TCP_NODELAY | A/B switch only on GEN2 -> local consumer TCP socket, not iPhone/MOST. Default = off. | Inherited `/tmp/mibr-alt111-tcp-nodelay.enabled`, 250 ms poll, readback and log |
| Renderer HELLO_EX/STATUS | LuKa's renderer is OMX/EGL, ours is M1AU -> TS -> MOST. No blind port to iPhone/VC or speculative presentation feedback. | Deferred |
| Source timestamps / T1 | Preserve exact source timestamp bytes and ordinal; do not treat remote timestamps as local queue age or alter PTS/PCR/writer pacing. | No changes to 56-byte M1AU schema or downstream clock constants |
| T3 status overhead | No extra per-MOST-packet or per-AU log writes. Overflow event logging only. | Existing status cadence retained |
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
