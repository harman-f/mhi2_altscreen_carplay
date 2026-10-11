# MU1440/AID10 Final Drive — live evidence checkpoint (2026-10-11)

**Scope:** one exact-target Škoda Octavia III / MHI2_ER_SKG13_P4526_MU1440 / AID10 vehicle. Developer-only, SSH-operated, volatile Final Drive observational proof of concept. This is **not** a new broadly validated release, installer, approved road-use feature or cross-brand compatibility finding. No persistent boot hook is installed by Final Drive.

## Source/build authority and frozen pair

- Source/CI checkpoint: [3a91204b6169eafcc525991fdf10c2aab3fb8d72](https://github.com/harman-f/mhi2_altscreen_carplay/commit/3a91204b6169eafcc525991fdf10c2aab3fb8d72), CI run \`38050224088\`.
- \`direct-ts-parity\` SHA-256: \`10350fb7dc715ec9b99c6b2acadb2a1b3e2ac7342c9281ca57e889fd7d3a4e31\`.
- \`parity-session\` SHA-256: \`232cc5f76feb105230712afd902d0c053339a94051ed8c6910a4e79c388b90ec\`.
- Preserve these native bytes. Experimental \`pollwait-v2\` observed POLLOUT/EAGAIN incompatibility on this target; **legacy EAGAIN wait / original v1 restored**. No PCR, cadence, packet writer, H.264, native owner or boot changes are proposed by this checkpoint.
- Original source and operational scripts remain in \`runtime/parity/\`, \`runtime/master/\`, \`deployment/mu1440-parity-drive-v1/\` and GEN2 source under \`src/native/altscreen111-gen2/\` at the pinned commit. The separately staged SD Final Drive v1.2–v1.4 additions must not be confused with the original CI artifact or claimed as vehicle-tested binaries.

## What was actually observed

- A later parked/stopped 30-fps observational Final Drive run had \`owner_result=STOPPED_AND_HAND_BACK_CONFIRMED\`, \`FINAL_DRIVE=STOCK_CONFIRMED\`, \`complete_stock\`, gate \`M1GATE1 0\`, no session lock, no pending queue and no persistent hook/profile apply.
- That run: \`input_records=45653\` (2293 IDR + 43360 non-IDR), \`output_aus_started=output_aus_completed=45584\`, \`sequence_gaps=0\`, \`write_errors=0\`, \`dropped_wait_idr=27\`, \`safe_recoveries=14\`, \`blocks_written=237684\`, \`bytes_written=2859813888\`. **Do not equate 45653 input with 45653 displayed**: recovery/drop and run boundary accounting differ.
- Earlier run stopped with native stock confirmed but \`failed_stock\` owner classification. The later clean restoration above is a separate, positive data point; neither should be erased.
- Apple Maps and Google Maps Type-111 video visually observed on the actual cluster. Two advertised ViewAreas in new handshake; \`ViewArea[0]\` full \`[0,0,1010,376]\`; \`ViewArea[1]\` full outer canvas with inner SafeArea \`[0,58,1010,248]\`, \`initial=1 source=temp\`. Operator visually confirmed SafeArea behavior.
- An actual GEN2 \`/info ready\` log confirmed URL \`maps:/car/instrumentcluster?showSpeedLimit=yes&showCompass=yes&showETA=yes&maneuverLayout=rightAligned\`. Subsequently \`navigation.maneuver=top\` was confirmed in TEMP settings, and the operator saw the Apple Maps arrival panel move toward the middle. **The precise app layout is iOS/provider-controlled**; this is a specific visual observation, not a separately specified ETA-center API.
- A 60-fps phone recording of the **30-fps-negotiated** vehicle run shows perceived discontinuity during Apple Maps zoom; visible near-static intervals roughly 100–190 ms were noted in some animated sequences. Recording/WhatsApp processing, app cadence, source capture and physical cluster presentation are not independently isolated. The underlying camera videos contain personal vehicle imagery and are **not** included in the public repository.
- The last 30-fps source measurement was roughly 25–27 fps, with occasional source inter-arrival gaps up to ~95 ms. Packet/AU completeness does **not** establish physical display cadence or smoothness.

## 40-fps investigation: configured, not yet negotiated/proven

- After the clean stop, \`alt111-settings set --key maxFPS --value 40\` yielded \`result=RECONNECT_REQUIRED\`, \`maxFPS.value=40 source=temp\`. \`navigation.maneuver.value=top\` and original reduced SafeArea were preserved.
- A subsequent Final Drive launch saw \`stream111_state=streaming\`, \`configured_max_fps=40\` in source-timing/registry, a live native gate and early \`192 input / 191 output\`, zero errors/gaps. Source arrival measured ~26–27 fps.
- **No subsequent \`GEN2 /info ready ... maxFPS=40\` entry was supplied in that trace**. The most recent logged \`/info\` remained \`maxFPS=30\`, because the prior CarPlay session may have survived. Therefore neither renegotiation nor 40 actual displayed fps is proven. \`maxFPS\` is a sender negotiation ceiling, not a frame pacer or measured physical FPS.

## Diagnostic limitations / pending work

1. New-session \`showUI\` type=1 dispatch was logged but no corresponding success completion was captured. Later keyframe type=4 completions succeeded and visual picture was observed; do not infer SHOW acknowledgment from these.
2. \`/tmp/mibr-alt111-gen2.status\` was missing even though GEN2 was running. On this QNX system \`/tmp -> /dev/shmem\`; inspecting the two paths does not provide independent evidence. Current status publisher uses a temporary file/rename; cause of missing status is unknown.
3. The Final Drive v1.2 telemetry supervisor used QNX-unavailable \`tr\` only to format \`gate_raw\`; v1.3 removes that command using \`cat\` alone. This isolated, offline-inspected telemetry-only hotfix has **not** been confirmed in a post-update vehicle run.
4. Optional v1.4 \`safearea-centered\` geometry \`[202,58,606,248]\` is offline-prepared **but not vehicle-tested and not needed for the successful topAligned observation**. Normal default stays \`[0,58,1010,248]\`.
5. \`supervisor_state=starting\` can remain shown during a functioning direct run. Diagnose with owner/bridge PIDs, live source, gate and counters; avoid calling a run fully healthy based on this label alone.
6. No further PCR/timing optimization should be represented as validated by this observation. The 30/40 fps zoom A/B is pending.

### Decision

Retain the frozen original v1 native pair as the vehicle-proven reference; publish the operating switch matrix and observed findings separately. Merge/release of native changes, an end-user installer, HMI buttons or expanded hardware compatibility requires fresh independent validation.