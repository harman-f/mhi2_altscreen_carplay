# Public repository attribution and steering-wheel scope audit (2026-10-11)

> **Research status · 2026-11-05:** **DATED INPUT RESEARCH.** Evidence is limited to the documented physical capture, static API or attribution scope. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


Audit target: **harman-f/mhi2_altscreen_carplay**, current default-branch working tree. This is a documentation/provenance audit; it neither replaces proprietary firmware nor changes car binaries, key events, QNX runtime or Parity.

## Correct owner/project identity

**Primary implementation discussed by the user:** [omonob/MHI2-Carplay-Maps](https://github.com/omonob/MHI2-Carplay-Maps), owner/author **omonob (QCDWJ)**. Relevant **MHI2** published profile: [MU1440_SKODA/790_AID10.5](https://github.com/omonob/MHI2-Carplay-Maps/tree/main/MU1440_SKODA/790_AID10.5). Omonob's public profile supplies the Free790 `CarPlayClusterControls.jar` and `core.so`, with KEY38/39-based short zoom/long map-provider switching. Its exact tested Java adapter observes `updateKey2`, not physical `updateEncoder2` detents. Our vehicle's right rotation correlates with `(4,40,+/-1,0,1)`; left with `(4,44,+/-1,0,1)`.

**Other, distinct public comparator:** [yuedizhibo/MHI2Q-CarPlay-AltScreen](https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen), owner **yuedizhibo**, for **Audi MHI2Q/AUG22**, not the requested MHI2 Omonob package and not a compatible binary swap. Its magnification callback/zoom pacing may be relevant as a design comparison only. Another independent Audi comparator is [Allemon/mib2-carplay-rgi-altscreen](https://github.com/Allemon/mib2-carplay-rgi-altscreen), owner **Allemon**.

## What is now indexed

- [Primary Omonob MHI2 encoder adapter / binary options](MU1440_OMONOB_MHI2_WHEEL_ENCODER_BINARY_PATCH_OPTIONS_2026-10-11.md)
- [Independent measured twelve-encoder evidence](MU1440_F902_FIVE_INT_ENCODER_CAPTURE_2026-10-11.md) and [read-only decoder](../../../tools/decode_keypanel_f902.py)
- [Earlier Omonob-specific JAR bytecode study](MU1440_WHEEL_DSI_AND_OMONOB_2026-10-11.md), now visibly marked as predating the numeric mapping
- [Separately labeled MHI2Q/yuedizhibo comparator](MU1440_MHI2Q_ALTSCREEN_ZOOM_PORT_BINARY_PATCH_OPTIONS_2026-10-11.md)
- [Research index](../README.md), [prior-art references](../PUBLIC_REFERENCES.md), [acknowledgements](../../../ACKNOWLEDGEMENTS.md), and [third-party notices](../../../THIRD_PARTY_NOTICES.md).

The earlier dated v1.4 quick-run page and steering-wheel mapping notes now link to the later decoder result rather than silently implying that numerical encoder identification remains undone.

## Repository-level wording check

- Enumerated the current recursive Git tree (279 blobs before new documentation additions; 245 then 246 text/source candidates when the primary audit was added) and checked every eligible text/source blob for the case-insensitive internal nickname `informal label`. At the prior head the **sole remaining current-tree content occurrence** was the old v1.4 test-plan wording. It was corrected to the fully qualified upstream and the newer mapping. No current-tree pathname contains the nickname.
- The obsolete internal-codeword-named document was removed from the current default tree and replaced with an explicitly labeled yuedizhibo/MHI2Q comparison and a separate primary Omonob/MHI2 document. Historic Git commits remain immutable and can still expose prior titles/text; the current branch does not.
- Author and project identities should always be stated as full repository slugs, preferably a direct link, whenever technical claims are derived from a third party. Preserve the distinction between physical observations, static/bytecode analysis and vehicle-qualified implementation.

**No installed patch is claimed.** The correct next work is a narrowly tested MHI2/Omonob input bridge for real `updateEncoder2`, plus independent VC-map context detection. Do not relabel provider `map-next` as the user-approved OEM native/CarPlay map-source toggle, and do not conflate key PRESS with rotary ENCODER.
