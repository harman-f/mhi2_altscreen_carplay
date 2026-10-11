# MU1440 30-fps visual zoom observation and 40-fps comparison gate

Evidence level: **operator-observed + external camera review**, NOT measured physical AID panel FPS. Exact vehicle and prior Final Drive status: [2026-10-11 live checkpoint](../status/MU1440_FINAL_DRIVE_LIVE_STATUS_2026-10-11.md).

## 30-fps baseline

The operator recorded two smartphone camera/WhatsApp videos from the **30-fps-negotiated** configuration before changing the registry to 40. Their containers were approximately 60 video frames/s: ~20.33 s / 1219 frames and ~58.02 s / 3479 frames. The user explicitly recorded the zoom-in/zoom-out transitions because some appeared jerky.

Frame-domain inspection of the first recording indicated repeated animated zoom-change phases, including approximately 4.5–6.0, 8.2–9.6, 12.1–13.5 and 16–17.6 seconds. Some visually near-static subsequences during transitions were estimated around 100–190 ms, followed by larger map-content changes. This supports reporting **perceptible discontinuity**, not declaring that any particular stage dropped N source frames. The file is phone-recorded and WhatsApp-processed; movement of UI overlays, camera exposure and compression can confound simple pixel metrics.

Contemporaneous GEN2 source-timing snapshots showed actual source arrival roughly **25–27 fps** at \`maxFPS=30\`, and sampled maximum source gaps of approximately 95 ms. These source samples were **not synchronized frame-for-frame** with the camera recordings; do not equate a 95-ms source gap to an observed ~190-ms video hold. The longer 30-fps Final Drive run also had 14 \`safe_recoveries\`, 27 \`dropped_wait_idr\`, zero TS sequence gaps and zero writer errors, but its cumulative totals do not identify the exact camera-visible zoom intervals.

**Public-media handling:** no raw personal footage, identifying VC images, vehicle metadata or raw logs are committed here. Only the sanitized aggregate observation is published.

## Distinct timing domains (do not collapse them)

1. \`maxFPS\`: advertised CarPlay sender negotiation upper bound (\`apply=reconnect\`).
2. Source cadence: AU arrival interval and preserved Apple 32.32 source timestamp.
3. Presentation clock: source timestamp-derived 90-kHz PTS in parity mode.
4. Keyframe/recovery: independent predictive-chain/decoder resynchronization.
5. Writer/physical transport: continuous TS, exact 12032-byte MOST writes, PCR, EAGAIN/backpressure.
6. VC decoded/displayed cadence: cannot be inferred from \`output_aus_completed\` alone.
7. External 60-fps camera recording: samples visible pixels subject to capture/transcode effects.

Zero \`sequence_gaps\` and zero \`write_errors\` establish transport correctness for the observed run, **not** smooth 30-fps physical presentation. 40 negotiated fps, if proved, is likewise not automatically 40 output fps or a remedy for repeated zoom/reframing actions by the app.

## A/B comparison gate (do not introduce a new timing patch)

Freeze native bridge/owner pair, SafeArea \`[0,58,1010,248]\`, \`mibr_legacy\`, keyframe mode/interval, \`topAligned\`, content/app and settings. Compare only \`maxFPS=30\` vs TEMP \`40\` in controlled parked/driver-passenger observation:

1. Clean Final Drive \`stop\`; require \`STOPPED_AND_HAND_BACK_CONFIRMED\`, \`STOCK_CONFIRMED\` and empty session lock. Disconnect CarPlay.
2. Set \`maxFPS\` TEMP while disconnected, then reconnect for a fresh \`GEN2 /info ready\` handshake and explicitly verify \`maxFPS=40\`.
3. Confirm stream state, view area count/initial geometry, active nav URL, no unexpected preset/profile override, original pair hashes and native gate state.
4. Record comparable zoom operations with the 60-fps camera, preferably retaining original capture before messaging-app transcoding.
5. Compare **motion intervals and longest visible still runs during a continuous animation** rather than average visual FPS alone; log source arrival distribution, AU/IDR counters, \`dropped_wait_idr\`, \`safe_recoveries\`, output completion, queue, writes and stop/stock classification.
6. If \`/info maxFPS=40\` is not logged, label the sample **configured only, no proven A/B**.
7. Stop while unit remains on; never interact with SSH while driving. Report visual judgement separately from transport counters.

No further \`pollwait-v2\`, PCR/PLL or synthetic-cadence changes should be interpreted as approved by this visual observation.