# MU1440 source111 zoom implementation v1 — isolated source branch

**Branch:** `work/mu1440-zoom-input-v1`, based on `work/mu1440-final-drive-upstream-20261011@795a096f71141484c73a4566b1b420257e7028c3`.

**Status:** Actual source code and host tests, not an installed automotive feature or a fully connected physical DSI input. Production binaries, `main`, settings registry, four frozen core boundaries and Parity/MOST writer are unchanged.

## Code now implemented

- `include/alt111_zoom.h`, `src/alt111_zoom.c`: independent C99 bounded, nonblocking control-plane queue for measured right MFW `updateEncoder2` five-int vectors; 12 maximum outstanding relative steps, 140ms minimum interval, one asynchronous AirPlay command in flight; reversal retargeting. Encoder 44 (left volume), key presses, unknown IDs/validities/extra and oversized signed increments are rejected without touching OEM callbacks. Preserve in-flight reversal compensation and reject stale session-generation callbacks.
- `include/alt111_zoom_adapter.h`: deliberately narrow native integration API `mibr_alt111_zoom_bind_verified(session,vc_map_focus,direct_owner,positive_is_in)`, `mibr_alt111_zoom_observe_encoder2(session,kbd,id,signedSteps,extra,effectiveValidity)`. The **actual** VC focus + DIRECT owner source is not currently connected; the API defaults off and has no cross-process IPC listener. It cannot be legitimately enabled by type111 negotiation alone. `positive_is_in=0` blocks all output until sign is calibrated against visible OEM map scale.
- `libaltscreen111_gen2.c`: same existing retained source111/control owner sends CFDictionary `type=changeMapZoomLevel`, `params.uuid=the active negotiated display UUID`, `params.zoomDirection=0 in/1 out`. Command construction uses the active session's existing settings scope. It is scheduled only when ordinary showUI/stopUI/keyframe/view control has no pending transaction, `shown_ack` is true and configured/primed source111 video is present, and after explicit *independent* VC-map-focus and DIRECT-ownership truth has been bound. Completing, losing focus/ownership, a failed dispatch, a new generation, repeated setup or teardown clears/outdates queued detents. Completion means AirPlay command result, NOT proof of actual app zoom. No pixel scaling or independent second AirPlay producer.
- `tools/build_altscreen111_gen2.sh`: links the new `alt111_zoom.c` into the existing `libaltscreen111.so`; no fifth core.
- `tests/alt111_zoom_test.c` and `tools/test_alt111_zoom_host.sh`: host C99 test for all twelve measured records, left volume rejection, missing context, unknown polarity, key/validity rejection, bounds, in-flight sign reversal, minimum gap, stale generation, failure and teardown.
- Build workflow adds a separate fast host zoom job and QNX compilation on PR changes.

## Exact input and command provenance

Physical input measured from the user's private v1.4 raw trace: right `(4,40,+1,0,1)`×3 and `(4,40,-1,0,1)`×3; left `(4,44,+1,0,1)`×3 and `(4,44,-1,0,1)`×3. Structured f902/tag0x002e is highly compatible with the DSI `updateEncoder2` signature, but tag-to-DSI-method semantics have not been independently verified. User's positive physical movement to Zoom IN/OUT is still an explicit calibration gate. Original release and QNX implementation do **not** alter OEM key fan-out, ASL encoder IDs, KEY38/39 or existing Omonob packages.

Primary comparator: **omonob/MHI2-Carplay-Maps** (owner omonob/QCDWJ), specifically `MU1440_SKODA/790_AID10.5` common 8,431-byte Free790 control JAR; its `updateKey2` KEY38/39-only bridge does not observe physical right-roller rotations. Other distinct architecture references are `Allemon/mib2-carplay-rgi-altscreen` and `yuedizhibo/MHI2Q-CarPlay-AltScreen` (Audi MHI2Q, not a Škoda/MHI2 binary donor). Full verified raw mapping: `docs/research/keypanel/MU1440_F902_FIVE_INT_ENCODER_CAPTURE_2026-10-11.md` on main.

## What must happen BEFORE a usable vehicle build

1. Pin/reconstruct exact MU1440 Java/J9 DSI listener service/instance and, without suppressing normal listeners, bridge physical `updateEncoder2` 4/40 signed ticks to *our existing* source111 owner via a reviewed cross-process ingress. An exported native C function is **not itself an inter-process transport from Java**. Do not repackage or install a third-party JAR alongside our live Parity path.
2. Prove real VC focus/page and actual STOCK/DIRECT visibility, not inferred from stream111 handshake, and pass that trusted state to `mibr_alt111_zoom_bind_verified`. Unknown page/focus/owner must remain disabled. Native menu scrolling, left volume and OEM key presses must be preserved. Raw encoder swallowing is forbidden.
3. In a parked native map test determine whether +1 means actual OEM zoom IN or OUT. Keep positive_is_in=0 until calibrated; no hard-coded assumed sign.
4. Bench-test native sender lifecycle and AirPlay response plus app visual output, queue/reversal; run QNX CI and exact vehicle/rollback validation. Determine semantic OEM map-scale branch before considering suppression of native overlay/double zoom.
5. After the separately authorized test only, integrate the reviewed input adapter and update master requirements/registry if a *new settings control* is proposed; the user-approved quick-control capability is already recorded but no new user-facing toggle/physical long-press binding is silently added.

### Host test
```sh
bash tools/test_alt111_zoom_host.sh
bash tools/build_altscreen111_gen2.sh build/gen2/libaltscreen111.so  # requires pinned QNX qcc
```

**Not in this branch:** no automatic input socket, no anonymous focus assumption, no bootclasspath installer, no actual JAR/binary deployment, no modification to `settings/registry.json` or historical vehicle-proven output binaries, and no VCA/HMI injection. This is intentional to protect active VC menu and Parity ownership while the remaining firmware-specific signal seam is validated.
