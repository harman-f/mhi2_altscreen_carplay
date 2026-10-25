# v1.4 design: optional parked-only CarPlay GPS demo location

**Status:** design-only / research-qualified at sender symbol; **NOT implemented, NOT vehicle-validated, NOT enabled in any installer**. Tracking: [#76](https://github.com/harman-f/mhi2_altscreen_carplay/issues/76). This document is the v1.4 design contract, not authorization to deploy an iAP2 hook to a vehicle.

## Product problem and scope

An owner wants to take CarPlay auxiliary-map screenshots/video without disclosing the
physical location of the test vehicle. The feature is a *CarPlay accessory-location
simulation* (not GPS buffering). It supplies one curated scenic European **static**
demo location during a short, explicit, parked test session, if the phone accepts the
accessory-supplied position. It must never affect the car's real receiver, OEM native
navigation, emergency location, telematics, vehicle speed, timestamps of unrelated
services, or normal ScreenAlt/video logic.

Target for initial qualification: **Skoda MU1440 / exact supported firmware / AID10**.
Generic/VW/SEAT are model values, not authorization for other vehicles. Their per-target
iAP2 hook/park-state provenance remains unqualified. Nothing here changes the frozen
1.3.2 kit or the source-promotion, versioning and installer PRs #73/#74/#75.

A real privacy property is **NOT established by replacing the outbound NMEA**:
iOS can independently use phone GNSS/cellular/Wi-Fi. The demo must not claim that
the map or phone has adopted the test location until independently observed.
For guaranteed privacy, a pre-composed/offline demo or cropping/redaction is safer
than relying solely on accessory GPS simulation.

## Source-backed architecture / proof limits

The stock MU1440 DIO manager has an NMEA output path through
\`libiap2client.so.1:iap2_gps_data_send(void *handle, const char *nmea)\`.
Our source interposer in
[\`src/native/vehicle-data/mibr_vdata_hook.c\`](../../src/native/vehicle-data/mibr_vdata_hook.c)
already resolves this symbol and **always forwards the original NMEA** before
optional project-origin speed/status data. In
[\`mibr_vdata.c\`](../../src/native/vehicle-data/mibr_vdata.c), the observer
recognizes GGA/RMC and stock $PASCD, but this does **not** prove complete live
location-sentence coverage nor that the hook is active on the owner's vehicle.

The stock GAL fallback option \`navigation.defaultLocation\` is an OEM *native
navigation* no-fix fallback; it is **not** a CarPlay accessory override and
must not be modified for this feature.

Apple states that CarPlay uses vehicle GNSS **in addition to** iPhone sensors and
that location-information exchange is requested by the phone over iAP2:
- [Developing CarPlay Systems, Part 1](https://developer.apple.com/videos/play/wwdc2016/722/)
- [Developing CarPlay Systems, Part 2](https://developer.apple.com/videos/play/wwdc2016/723/)
- [Core Location source information](https://developer.apple.com/documentation/corelocation/cllocationsourceinformation/isproducedbyaccessory)

Apple does not document an unconditional priority rule under large disagreement.
Do not interpret "iAP2 send succeeded" as "iOS positioning changed".

Data-flow proposal (only after qualification):

    STOCK OEM GNSS/GAL -> DIO stock NMEA production
                                    |
                         existing iAP2 sender seam
                                    |
                 [optional versioned local transformer]
                 OFF: original bytes, no other activity
                 SHADOW: inspect/redact counters only; original bytes
                 DEMO: qualified/parked/session-scoped NMEA substitution
                                    |
                    original iap2_gps_data_send handle
                                    |
                               iOS fusion
                                    |
                           CarPlay maps UI
    HMI Advanced -> GPS Demo -> owner ACTION/ACK -> ephemeral gate

Do not add a second iAP2 owner, independent GPS sender thread, additional AirPlay
connection, competing MOST video pipeline, persistent GAL/DIO configuration change,
or direct Java file writes. The coordinator is a separate **typed runtime action**
and state machine, not a 49th canonical settings key.

## UI / functional contract

Proposed menu path: **CarPlay settings → Advanced → GPS Demo Location**
(DE: **CarPlay-Einstellungen → Erweitert → GPS-Teststandort**).

- Initial state is \`AUS / OFF\`; all system restarts/disconnects return to OFF.
- \`Teststandort\`: one chosen *curated* preset, explicitly labeled public landmark.
  Initial fixture: **Munich / Marienplatz**, independently documented coordinates
  WGS84 \`48.1372222222 N, 11.5752777778 E\` (must still be checked during fixture
  implementation). Additional curated candidates for separate coordinate review:
  Prague / Charles Bridge, Lucerne / Chapel Bridge, Lisbon / Praça do Comércio.
- \`Zufällig / Random\`: choose **once** per activation from the vetted list
  using a locally available secure/adequate random source. Not a wandering random
  point, not a new position every NMEA sentence; keep the same location and
  activation ID throughout the session. All demo fixtures are public-space
  points and must not encode a user/home location.
- \`Dauer / Duration\`: default **10 minutes**, hard maximum 10 minutes;
  do not automatically renew. This is a product design value, not measured.
- \`Starten\` must show an explicit warning:
  **TESTSTANDORT – NUR IM PARKENDEN FAHRZEUG – NICHT ZUR NAVIGATION**.
  Active indicator remains prominently visible in OEM HMI when viewing this menu.
- \`Sofort beenden\` must always be accessible when the UI can operate.
- Read-only diagnostic: requested preset, mode, elapsed/remaining time, last
  source classification, emitted/suppressed NMEA counters and actual gate reason.
  Never store or print real/raw GNSS coordinates in persistent diagnostics.
- The menu must distinguish **TX_ACTIVE** (substitution attempted, from sender ACK)
  from **PHONE_ACCEPTED** (independently observed in a supervised test). The latter
  is not automatically inferred in production from the adapter.
- If an adequate parked-state proof is unavailable, display \`Nicht verfügbar:
  Parkzustand ungeprüft\`, not an enabled but unsafe toggle.

The v1.4 version-page implementation in PR #74 is independent; do not embed demo
mode inside the Version page. Respect existing OEM widget and Back/focus contracts.

## High-level protocol: tentative, versioned, separate from canonical settings

Proposed commands (names provisional; exact schema depends on MIBR/3 owner review):

| Control | Payload | Reply/observation |
| --- | --- | --- |
| \`GPS_DEMO_CAPS\` | none | target-qualified, parked-signal-qualified, NMEA-qualified, feature-supported |
| \`GPS_DEMO_STATUS\` | none | OFF/ARMING/SHADOW/TX_ACTIVE/STOPPING/ERROR + TTL + reason + generation |
| \`GPS_DEMO_START\` | \`preset_id\`, \`duration_s<=600\`, request UUID, current session generation | accepted/pending/rejected, no false active ACK |
| \`GPS_DEMO_STOP\` | current generation/request token | idempotent stop receipt |
| \`GPS_DEMO_ABORT\` | internal guard failure | immediate stock-pass-through, reason code |

These are **ephemeral actions**, not persistent profile values. No arbitrary lat/lon
or external network input via HMI; only a signed/checked local curated preset ID.
All responses are correlated to caller, active iAP2 session/handle generation and
controller generation. Reject stale, duplicated, replayed, cross-session requests,
invalid TTL or firmware/brand mismatch. MIBR/3 is control-plane only and must not
transport NMEA or high-rate location samples.

Conceptual state flow:

    OFF --explicit start and all gates satisfied--> ARMING
    ARMING --coherent stream + handoff validated--> TX_ACTIVE
    ARMING --timeout/mismatch--> OFF (reason visible)
    TX_ACTIVE --stop/TTL/disconnect/motion/unknown--> STOPPING -> OFF
    any internal error -> OFF/pass-through + ERROR reason
    SHADOW is observer-only, sends every original sentence unchanged

*Sender acceptance* and *iOS/CarPlay acceptance* are separate gates. An ACK merely
indicates local transformer intent or a confirmed outbound call, not phone fusion.

## Standstill / parked-only interlock

Activation is **not** permitted based solely on an old speed sample, a menu press,
NMEA's own synthetic speed=0, or a stationary map icon. Preferred interlock:

1. Independent, actual OEM/DSI vehicle speed is valid and fresh (suggested freshness
   <= 1 s; final threshold only after verifying real MU1440 update cadence).
2. A separately validated *parking state* such as engaged parking brake is available
   from the exact target and fresh; speed=0 at a red light must NOT qualify as parked.
   If no such reliable parking signal can be proved, do not enable active demo mode.
3. Stable standstill continuously for at least 2 s; invalid/unknown/moving on either
   channel blocks activation and triggers stop. The motion interlock runs independently
   of the spoofed data path; its update must not depend on the NMEA interposer.
4. Every effective send is gated against current session generation, motion and TTL,
   not only checked on the HMI button click.
5. Hard expiration, disconnect, owner change, reconnect, ignition transition,
   reboot or adapter error restores byte-for-byte stock pass-through; no auto-resume.

The recommended thresholds above are proposals, not evidence of an existing
reliable parking-brake DSI binding on MU1440. Until that input is proven,
\`GPS_DEMO_START\` is not supported in a vehicle release.

## NMEA transformation / transactional forwarding

**Critical:** the current \`mibr_vdata_hook.c\` sends \`real(handle,nmea)\` before
optional outputs. Demo mode cannot be implemented by appending synthetic GGA/RMC
after that call; it would leak the real position in the same session and can cause
fusion jumps.

Implement later as a **single replacement-or-pass-through decision** at the
existing send boundary, with bounded no-allocation fast path and no added worker.
Only a reviewed, explicit allowlist of original position-bearing sentence
types may be transformed. Minimum GGA/RMC; audit GNS/GLL/VTG and proprietary
sentences and mixed talker IDs during passive G0 first. Preserve original data
for all unrelated/vehicle-status/diagnostic sentence types, including $PASCD,
unless a separate compatibility review shows location/privacy coupling.

For qualifying GGA/RMC (and every further evidenced position-bearing type):
- Replace latitude/longitude with exactly one WGS84 preset; convert to NMEA
  degrees-and-decimal-minutes with correct N/S/E/W and field precision.
- Coherently preserve **current** UTC/date fields; never replay an old packet.
  GPS fix status/quality, accuracy, altitude, satellites and DOP must not be
  invented as "measured" facts. Validate per-type protocol requirements; if
  consistency cannot be achieved, reject activation before first substitution.
- While parked, speed is consistently zero if a valid position protocol field
  requires it; undefined course/heading must not be fabricated. Do not modify
  actual vehicle speed shared with non-CarPlay systems.
- Maintain sentence boundaries, talker IDs, maximum lengths, checksum XOR,
  CR/LF policy and NUL terminator accepted by the exact target sender ABI.
- Do not send a sequence containing a mix of *real* and *fake* position-bearing
  statements while marked active. Unknown position-bearing proprietary types
  require fail-safe rejection of activation rather than unreviewed forwarding.
- Keep the current optional speed/VehicleStatus feature intact when OFF;
  when active, do not add synthetic vehicle-status data or duplicate traffic.
- The transformer shall never log original or synthetic precise coordinate
  strings to persistent files, public CI, issue attachments or screenshots.

**Error priority:** safety and stock OEM operation trump screenshot privacy.
On an internal error, expired/invalid parking evidence or a changed owner session,
return immediately to original unmodified forwarding. Surface \`PRIVACY_NOT_GUARANTEED\`
and instruct that photography stop. A live screenshot may again contain the real
location; the feature must not claim absolute redaction.

Concurrency: current hook uses a non-blocking trylock for auxiliary data. An
unavailable lock must **not** silently allow one real coordinate while the UI
still claims "TX_ACTIVE". Either design a fast, atomic generation-validated
transform decision with a proven bounded path, or revoke TX_ACTIVE before
pass-through and mark privacy invalid. Host tests must cover lock contention,
concurrent stop and session teardown.

## Feasibility phases, owner and stop/go gates

| Gate | Scope and independently verifiable output | Next phase requires |
| --- | --- | --- |
| G0 / Read-only | Target DIO/GAL/iAP2 call graph; classify **all** outgoing position-bearing sentence types; iAP2 session lifecycle; independently verified DSI speed + parking-state evidence. Sanitize any private capture. | Exact owner, park interlock and sentence coverage established |
| G1 / Host simulator | Pure C NMEA parser/transformer, curated fixtures, checksum/date/UTC/hemisphere, fixed-position and session state machines, fuzz/negative/race tests. Default OFF; **no target hook enabled**. | Test matrix green + independent review |
| G2 / QNX integration | Build optional side module integrated into existing iAP2 sender; firmware ABI, strip/export and pass-through equivalence; simulator/instrumented worker; read-only status; no duplicate originals. | Qualified target, transactional gates, rollback and CI |
| G3 / Supervised vehicle/iPhone | Separately authorized stationary session (verified brake/speed), stock capture without full raw coordinates, requested/accepted location distinction; Apple Maps or target map visual proof and OFF recovery. | Explicit user authorization for a bounded parked test |
| G4 / v1.4 promotion | Only after G3 success: release toggle with prominent warning, targeted acceptance, documentation and rollback; otherwise keep disabled or SHADOW-only as a research feature. | Go/no-go documented by reviewer |

G0 must not initiate a live test without separate authorization. G1 can proceed
entirely without the unit or private OEM binaries. No firmware write, spoof hook
activation, device reload, or public publication of private screenshots is implied.

### Minimum negative/test matrix

- OFF and SHADOW preserve every original NMEA byte and iAP2 return code.
- Unknown sentence / bad checksum / malformed UTF-8 or ASCII / long inputs /
  missing terminator / mixed talker / unexpected source generation.
- Correct GGA/RMC checksums, lat/lon conversions incl. hemispheres/bounds,
  UTC rollover, RMC date rollover, stable preset, static position, no injected
  stale speed/course or made-up fix quality.
- One real position-bearing sentence inside ACTIVE must fail the privacy
  acceptance gate; a duplicate original plus synthetic sentence is a failure.
- Lock contention, torn config/atomic-snapshot read, invalid preset signature,
  stale receipt, TTL, concurrent OFF, crash, lost session, reconnect/reboot.
- Actual driving state, unknown speed, parking brake released, parked but
  temporary 0 km/h, missing or stale DSI values, failure-to-observe motion.
- Two independent test oracles: outbound iAP2 transform worked **and**
  target iOS navigation UI **actually adopted** the demo area.
- After OFF/disconnect, **stock original** NMEA restored, maps eventually
  recover real device position, native vehicle navigation unchanged.
- No installed data store or status file records a private live location.

### Evidence and acceptance interpretation

\`BUILT\`: source compiles. \`TRANSFORM_VERIFIED\`: deterministic host vectors
match. \`SENDER_CONFIRMED\`: exact target forwarding observation.
\`PHONE_ACCEPTED\`: separately observed Core Location/accessory position or
navigation UI match. \`MAP_DEMO_VALIDATED\`: expected map image clearly shows
curated landmark and does not disclose user's location. They must not be
collapsed into one green status.

iOS may ignore accessory GNSS when phone GNSS has a strong fix, blend both, or
jump between them. No undocumented priority/coercion trick is in scope.
If phone fusion rejects the discrepancy, the v1.4 requirement is satisfied
by **documenting the limitation and offering a privacy-safe alternative**
(e.g. curated static map/demo asset or manual viewport plus coordinate masking),
not by destabilizing the authentic phone/GNSS session.

## Release scope: v1.4

This is a **planned optional v1.4 feature with hard acceptance gates**, not a
guarantee that a functional on-device switch will ship. It must not hold up the
core 1.3.2 reproduction, owner-unit recovery, normal video/VC operations or
release qualification if still blocked. Product behavior:
- Unqualified target / absent parking proof / unknown NMEA: default OFF,
  hidden/disabled toggle, status explains reason.
- Qualified target and accepted G3: feature flag available, OFF by default.
- Developer SHADOW-only may be made available after host/static review, but it
  sends **no simulated coordinates** and is not an end-user GPS demo feature.

## Work handoff / ownership

- Source/design and privacy contract: Issue #76 and this document.
- G0 reverse engineering: separate private, read-only evidence and provenance.
- G1 core NMEA replacement library: reviewed standalone host-testable PR.
- G2 QNX/runtime: **after** #73/#74/#75 and after the fully versioned build
  gate; separate PR touching optional vehicle-data path, no changes to
  canonical settings/Version page or a stock firmware binary.
- G3 vehicle evidence: user-supervised parked test only.
- K1–K5 baseline installer/reproduction work remains independent.

**No source in this documentation PR is installable or changes a vehicle.**
