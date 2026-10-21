# MU1440 integration status — 21 October 2026

This is the current cross-module **research and engineering status**, not a new binary release or a declaration of production readiness. It supersedes older *status summaries* when they disagree; historical test reports retain their original dates and scope.

## Evidence vocabulary

- **VEHICLE OBSERVED:** tested on the reference MU1440/AID10 unit in a named configuration; does not imply cross-brand compatibility.
- **HOST / QNX BUILD:** source tests or ARM/J9 compilation passed; no implied installation.
- **STATIC / RESEARCH:** behavior or attachment candidate supported by a reviewed component or comparative analysis, not by a live end-to-end test.
- **OPEN:** missing proof or integration. A stored setting, an accepted command, and a visibly applied action are distinct outcomes.

## Module-by-module snapshot

| Module | Current evidence | Remaining acceptance |
| --- | --- | --- |
| Classic ScreenAlt / type-111 receive | The September developer path displayed moving Apple Maps, Google Maps and Waze on the reference VC. A newer guarded GEN2 candidate has also been used in development vehicle sessions. | Source/session teardown, reconnect and provider handover reliability; candidate qualification independent of public release. |
| Direct H.264-to-MPEG-TS / MOST | Direct no-transcode path and exclusive DisplayManager writev gate vehicle demonstrated; fixed 64 x 188-byte output blocks. | Reconcile later parity/source-timestamp candidates and independently verify all stop/STOCK outcomes. |
| Source framing / parity | Complete access-unit identity and original source-time transport implemented in experimental engineering lines; motion fixtures and lengthy live sessions studied. | Do not label latest internal test combination a published stable release. |
| Timing and codec diagnosis | Native versus CarPlay H.264 and TS compared; long-run telemetry and parked motion-fixture A/B performed. | Isolate live-arrival jitter, keyframe quality pumping, intermittent latency recovery and actual AID presentation. |
| Zoom | Right-roller event and one existing GEN2 AirPlay zoom sender investigated; Apple Maps visual zoom observed in an independently installed reference-vehicle test, not a general release. | Current-page/focus proof, other navigation apps, OEM-exclusive suppression and public install qualification. |
| HMI | OEM-native HOME/settings work advanced from architecture into installed/visually tested development candidates. Dedicated menu rows, navigation settings and source-only scrollbar candidate exist. | Full field acceptance: storage/TEMP did **not** independently prove visible navigation-config application; new UI and controller must be verified together. |
| Central controller | MIBR/3 native+Java source prototypes, guarded persistence/CAS, role-separated loopback API and route ACTION receipts have host/QNX source evidence. | Genuine on-unit owner, visible AID state, same-request ACK, power-loss/rollback and production credential/lifecycle checks. |
| Vehicle data | Original GNSS path mapped; optional Speed/PASCD and classic VehicleStatus portable candidates and source adapters exist. | Qualified existing iAP2 owner binding, true phone request/receipt and on-unit validation. Not in the current developer release. |
| ViewArea | 1010x376 reference map surface established; two negotiated-area candidates and a proposed further display preset studied. | Validate actual screen composition, visual mapping and acknowledged in-session switching; 1280x480 panel class is not the Direct-TS coded canvas. |
| Wireless CarPlay | Published research and experimental source snapshot. | Native bootstrap/session recovery and complete secondary-display proof remain open. |

## Recent measured results and qualifications

The October 19 analysis of four long live parity sessions includes a roughly 56-minute session with 83,919 incoming AUs, no sequence gaps and no write errors. The logged PTS-minus-PCR lead grew around 0.31–0.33 s/minute across these sessions; it is a **model/clock-domain observation, not evidence of corresponding physical display delay**. Regular 20–25-minute vehicle operation did not reveal the large accumulating visual delay that a literal reading would predict.

Controlled parked variants comparing the original iPhone H.264 with native-like and re-encoded H.264 showed that the original bitstream was decodable in the clean fixture path. A Baseline re-encode was not a demonstrated improvement. Keep the no-transcode path as baseline; do not infer that every live jitter/smear cause is now identified.

October 20 logs distinguish (a) CarPlay/session TEARDOWN, sometimes reason -6753, followed by stream-111 EOF, from (b) loss of our native-gate proof while source 111 remains streaming. In the inspected installed state, **two supervisor instances** were also present; the owner lock prevented a second writer. No causal explanation of the observed iPhone disconnections has been proven. See [October vehicle and timing findings](../findings/OCTOBER_2026_VEHICLE_AND_TIMING_EVIDENCE.md).

The October 20 HMI field result is **not a full functional PASS**: menu changes and TEMP/store observations did not demonstrate that the five selected navigation options actually changed the live CarPlay/VC presentation, even after the tested reconnect/reboot. A verified current-session owner SHOW/APPLY and per-key ACTIVE evidence remain required. A new Java scrollbar/three-view source candidate has build evidence only, not an assumed installed visual PASS.

## Further dated reference-vehicle evidence

The [October 11 Final Drive checkpoint](MU1440_FINAL_DRIVE_LIVE_STATUS_2026-10-11.md), [switch matrix](../testing/MU1440_FINAL_DRIVE_SWITCH_MATRIX_2026-10-11.md), [visual zoom/cadence observation](../findings/MU1440_ZOOM_CADENCE_OBSERVATION_2026-10-11.md) and [package provenance](../../deployment/mu1440-final-drive-v1/PACKAGE_PROVENANCE_2026-10-11.md) were transferred as historical documentation only. They do not import the experimental old-stack code or locally staged ZIPs.

## Current shipping baseline

The [current developer release](../../release/CURRENT.md) remains the existing MU1440-specific experimental checkpoint; no newly described controller, HMI, vehicle-data or parity variant is implicitly part of its ZIP. Use exact component hashes, compatibility checks, backup and rollback. The public research and open draft PRs may be newer than the recommended downloadable binary.

## Start with these boundaries

- [Module architecture and VW/SEAT portability](../architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md)
- [Native HMI/controller detail](../architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md)
- [Optional vehicle-data overview](../architecture/OPTIONAL_VEHICLE_DATA_FEATURE_OVERVIEW.md)
- [Fault isolation and recovery acceptance](../testing/STREAM111_FAULT_ISOLATION_2026-10-21.md)
- Detailed vehicle-data protocol publication remains subject to a separate review.
- [Known issues](../findings/KNOWN_ISSUES.md)
- [Vehicle and timing findings](../findings/OCTOBER_2026_VEHICLE_AND_TIMING_EVIDENCE.md)
- [Compatibility matrix](../testing/COMPATIBILITY_MATRIX.md)
