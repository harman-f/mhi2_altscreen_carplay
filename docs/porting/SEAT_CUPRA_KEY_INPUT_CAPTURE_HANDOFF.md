
# SEAT/CUPRA MU1409: steering-wheel and key-input discovery — AI-agent handoff

**Public, English, source-only research handoff · 23 October 2026**

**Audience:** the contributor working on a 2020 CUPRA Ateca, `MHI2_ER_SEG11_P4708_1` / MU1409, Continental 790, and their local AI/Codex agent. **Goal:** independently map the real physical SEAT wheel and head-unit controls so we can later implement a small SEAT-specific input adapter for CarPlay zoom, guarded video switching and the proposed native HOME/Settings menu. **This is a capture/analysis task, not an input remapping, installer or vehicle-compatibility claim.**

Read [joint port plan](SEAT_CUPRA_MU1409_COLLABORATION.md), [local Mac/QNX environment](SEAT_CUPRA_MU1409_LOCAL_ENVIRONMENT.md), [reference Škoda raw keymap](../testing/MU1440_MFW_RAW_KEY_MAPPING.md) and [target QNX shell contract](../testing/MU1440_QNX_SHELL_COMPATIBILITY.md) before beginning. The existing omonob MU1409 video installation need not be removed to undertake an authorised, bounded passive inventory; check its actual bootclasspath and logger coexistence first.

## 1. How we discovered the controls on our Škoda

Exact reference vehicle: `MHI2_ER_SKG13_P4526_MU1440`, fitted AID10-class cockpit. We used **two distinct evidence paths**:

1. **Physical key presses.** The stock `AslTargetSystemKeyPanelHandling` Java logging produced `HK Received: KBD[k] KEY[n] KST[s]`. Our independent QNX native logger connected **receive-only** to the existing Java DebugSPI socket at `127.0.0.1:15001` and decoded OEM text in MLP type-1 / inner `0x0104` UTF-16BE frames. An operator entered a precisely named `NOTE` immediately **before** each physical action in a second SSH session, creating a common monotonic timeline. The stock reaction was also recorded.
2. **Rotary detents.** Physical wheel rotation produced *no* corresponding `HK Received` in the text log. We retained the **original binary MLP frames** and later decoded specifically observed inner `0x0110`, subtype `f9 02`, tag `0x002e`, five signed BE-int records offline. Twelve events matched four annotated blocks (three turns in each direction for each wheel). Their five values strongly match `DSIKeyPanelListener.updateEncoder2(keyboard, encoderId, increment, extra, validity)`. **Do not claim tag 0x002e itself is a proven DSI method number.**

Our listener is passive in the sense that it does not send key/DebugSPI protocol data, patch Java, edit startup/firewall files, emit zoom commands, acquire MOST or change OEM listener fan-out. **Opening the existing DebugSPI socket may activate its sink**, so capture is still a bounded, owner-approved parked experiment.

### Actual Škoda results — NOT a SEAT key map

| Physical action on our exact Škoda | Observed event | Status |
| --- | --- | --- |
| Right wheel PUSH | `updateKey2`: `KBD=4, KEY=40`; short `KST 1→0`; long `1→3→4→5→0` | Physical/stock-log correlation |
| Right wheel turn up / down | `updateEncoder2(4,40,+1,0,1)` / `(4,40,-1,0,1)` | Six decoded records, three per annotated direction |
| Left wheel PUSH | `updateKey2`: `4/44` | Physical/stock-log correlation |
| Left wheel turn up / down | `updateEncoder2(4,44,+1,0,1)` / `(4,44,-1,0,1)` | Six decoded records, three per annotated direction |
| Right Back; right Phone | `updateKey2`: `4/41`; `4/53` | Correlated |
| Left upper/lower; Voice/PTT | `updateKey2`: `4/46`, `4/47`, `4/50` | Correlated |
| Head unit HOME; MENU | `updateKey2`: `13/116`; `13/78` | Correlated |
| VIEW, Assist, other head-unit controls | **Unknown** in this published physical capture | Do not guess |

`KST`: 0=released, 1=pressed, 2=double, 3/4/5=progressive long states; other states 6/7/8 are documented in the reference keymap. A `KEY=40` **press** and an `encoderId=40` **turn** are different DSI event families even though they have the same number. OEM symbolic names ROLLER_LEFT/RIGHT did not match the actual physical mounting sides on our Škoda. The +1/-1 polarity follows the owner-annotated action order: do not infer the final phone Zoom IN/OUT mapping from signs alone.

The Škoda's right-wheel detents also preceded six `A wrong DDS Encoder was recognized` log warnings: this demonstrated an OEM handler had seen the encoder callback, **not** that the wheel was absent or that the native cockpit's map zoom was not working. See [the twelve-record analysis](../research/keypanel/MU1440_F902_FIVE_INT_ENCODER_CAPTURE_2026-10-11.md).

## 2. Public, reusable source — use this, not private captures

| Purpose | Exact public starting point |
| --- | --- |
| Passive RX-only logger source | [`src/native/keypanel/mibr_keypanel_native.c`](../../src/native/keypanel/mibr_keypanel_native.c) |
| Host integration fixtures | [`tests/keypanel-native/integration.py`](../../tests/keypanel-native/integration.py) |
| Reproducible QNX build and ELF validation | [`.github/workflows/build-keypanel-native.yml`](../../.github/workflows/build-keypanel-native.yml) and [`tools/build_keypanel_native.sh`](../../tools/build_keypanel_native.sh) |
| SD-safe two-console wrappers (Škoda paths must be checked on SEAT) | [start](../../runtime/diagnostics/keypanel_start_native.sh), [notes](../../runtime/diagnostics/keypanel_note_native.sh) |
| Native logger operator description | [`MU1440_NATIVE_KEYPANEL_CAPTURE.md`](../testing/MU1440_NATIVE_KEYPANEL_CAPTURE.md) |
| Latest narrow **offline** rotary decoder | [`tools/decode_keypanel_f902.py`](../../tools/decode_keypanel_f902.py) |
| Full measured Škoda keymap and evidence caveats | [`MU1440_MFW_RAW_KEY_MAPPING.md`](../testing/MU1440_MFW_RAW_KEY_MAPPING.md) |

For trace context our Java comparison identified `DSIKeyPanelListener.updateKey2` (five ints) and `updateEncoder2` (five ints), with reply service method numbers 38 and 30 respectively **in the examined firmware corpus**. Verify the actual method/signature/listener path in P4708_1 before implementing any SEAT-specific observer. The typed DebugSPI record tag `0x002e` is **not** automatically the same as reply-service method 30.

The reference CI pins the QNX 6.5 ARMv7 toolchain at `luka-dev/qnx65-armv7-toolchain@56a66557245af14077678cd28a83ce3a337d9e2d`. The older documented v1.4 CI artifact was a QNX ELF32 little-endian ARM EABI executable with QNX loader and libsocket dependency, not a Linux or macOS binary. Rebuild or verify the actual release artifact and its hash before use; do not treat a host ELF as deployable.

## 3. AI/Codex execution instructions — adapt to the actual SEAT, fail closed

### Gate A — establish exact target and source/collector prerequisites (off-car first)

- Pin the public source commit and tool versions. Record the original **P4708_1** firmware identity, fitted Continental cockpit and physically present steering/head-unit controls. Keep private unit files, original JXE/JAR/firmware, raw logs, personal information and credentials outside public Git.
- Inspect the **existing** omonob/NavActiveIgnore and other bootstrap changes read-only. Do not replace their `DSIKeyPanelDispatcher` or append another J9 bootclasspath shadow for a capture experiment.
- Determine which host/target commands actually exist on this exact QNX train. The Škoda shell did not reliably provide `date`, external `printf`, `tr`, GNU options or stock `sha256sum`. Only the existing SD/media path was remounted by the tested wrapper, after a write-probe; do not assume its hardcoded Škoda path exists on SEAT.
- Identify whether the **stock or currently installed Java DebugSPI service** is already listening on loopback port `15001` and can provide genuine, bounded data. Inspect its actual process/owner/route and the current endpoint without modifying startup scripts, logging config or PF. If this is absent, use Gate B fallback: **do not install a blind borrowed Java hook to make it appear**.

**Gate A deliverable:** target/version/source SHA, available and unavailable dependencies, whether the stock sink exists, and a proposed fully read-only/bounded capture route. If access or source/build prerequisites are missing, return `BLOCKED` with the concrete reason.

### Gate B — select the least invasive path

1. **Existing compatible sink, explicitly owner-approved:** build the logger from project source (host self-test + integration first, then pinned QNX cross-build and readelf/file/dependency/hash inspection). Copy only the independently checked logger and reviewed wrapper to a **fresh project-owned directory on the actual writable removable media**. Never overwrite a running omonob/MIBR or factory file. Both SSH sessions use that same directory.
2. **Sink exists but bytes/layout differ:** capture a short bounded synthetic/known-key baseline and inspect the frame protocol on a private host. Treat any unknown record as unknown; adapt a **new SEAT-specific offline parser** with fixtures and bounds checks, rather than forcing the MU1440 decoder to produce a false keymap. Do not send protocol bytes to probe the service.
3. **Sink absent or unusable:** review the exact local `lsd.jxe`/J9 API, available stock log/trace sink and `DSIKeyPanelReplyService` and listener wiring *off-car*. A read-only stock trace is preferable if it actually exposes raw key callbacks. Enabling new logging, a Java/J9 listener or bootclasspath override is **a separate, reviewed, reversible experiment**, not part of this first handoff. Report `DEBUGSPI_ENDPOINT_UNAVAILABLE` and the proposed next evidence required, without restarting Java or installing a listener automatically.
4. If buttons or VIEW/Assist show **no DebugSPI event**, classify `NOT_SEEN_ON_THIS_PATH`, not `NO_SIGNAL`: the physical signal may take a VC-only/another bus or consumer route.

### Gate C — actual physical correlation (parked, brief, two consoles)

Use **the actual verified** QNX logger build and its applicable media directory. For our reference only, the two commands were:

```sh
# Shell 1, in the newly prepared dedicated SD capture directory:
 /bin/ksh keypanel_start_native.sh 240

# Shell 2, same working directory while shell 1 is capturing:
 /bin/ksh keypanel_note_native.sh
```

The above shell scripts are **MU1440 reference material** and contain a fixed Škoda SD path preflight. On SEAT, review/adapt and host-check that path first; do not bypass safety gates with a global edit. The collector writes a new `native-<PID>/` folder containing `combined.log`, `debugspi-text.log`, `debugspi-original.bin`, `report.txt`. The first console shows both event and operator NOTE using the same monotonic clock. Record specific screen state; wall clock can be misleading on QNX.

Operate one action at a time; enter its NOTE **before** pressing/turning; pause around 2–3 s between actions. Use a small repeat count (e.g. three isolated detents per direction). Suggested sequence:

| Phase | Human NOTE and physical test | Also record |
| --- | --- | --- |
| Positive control | Known safe ordinary wheel short press and one known head-unit key (HOME or MENU only if fitted/safe) | Whether *any* genuine OEM text appears |
| Right wheel | UP +1 ×3; DOWN −1 ×3; PUSH short; PUSH long only if safe | Exact physical side, KEY versus ENCODER family, original visible response |
| Left wheel | UP +1 ×3; DOWN −1 ×3; PUSH short | Volume behavior, do not reassign it |
| Other fitted wheel buttons | Back, Phone, Voice, VIEW, Assist *only where their normal action is safe* | Short/long separately; don't infer from generic VW diagrams |
| Head-unit keys / knobs | Each actually fitted hardkey, push and rotation separately | Physical labels; don't transfer Škoda 13/116 or 13/78 as facts |
| Context isolation | If already stable: native VC map; existing CarPlay VC map; OEM VC menu focus, in separate bounded runs | Same button may produce different consumer effects; no stream or media-owner manipulation merely for capture |

If physical input creates an unexpected hazardous stock function, stop that test. Do not test emergency controls, change critical driving functions or operate notebook/SSH while driving. Capture one short session rather than an indefinite trace. Preserve raw privately and share only a redacted `report.txt`, annotated derived tuples and relevant sanitized `combined.log` snippets. The event timestamps and original stock reaction matter as much as the numeric IDs.

### Gate D — analyse and validate offline

Use the checked-in host-only decoder only on a **private copied** raw file, never directly on the vehicle:

```sh
python3 tools/decode_keypanel_f902.py /private/seat-capture/debugspi-original.bin \
  -o /private/seat-capture/typed-five-int-events.csv
```

This parser is deliberately narrow: it validates MLP framing and decodes the **observed MU1440** inner `0x0110/f9 02/0x002e` five-int layout. **Zero results on SEAT are inconclusive**, not proof its wheels use no `updateEncoder2` callback. If SEAT frames differ, first write synthetic fixtures/tests for its measured layout and compare independently with the actual SEAT Java/J9 callback signatures. Do not claim arbitrary bytes are physical input based on one coincidental match.

Review correlation by physical test order/timestamps, count and value stability; annotate confidence as `DIRECT_TYPED+OPERATOR`, `OEM_HK+OPERATOR`, `STATIC_ONLY`, `INFERRED`, `UNKNOWN`. Distinguish `updateKey2`, `updateEncoder2` and legacy `updateEncoder`. The stock `A wrong DDS Encoder was recognized` warning is evidence of an *unhandled encoder in that consumer*, not the numeric encoder ID by itself.

**Gate D acceptance:** repeated events (ideally three per direction), no unexplained framing/truncation, control-key positive test, exact physical-to-callback association, observed native OEM action and a sanitized mapping with unresolved controls explicitly marked.

## 4. Don't confuse the omonob adapter with raw input discovery

In [omonob/MHI2-Carplay-Maps](https://github.com/omonob/MHI2-Carplay-Maps), the common historical 790 JAR used `updateKey2` KEY38/39 for short-press zoom and long-press map changes. Its original encoder callback was **not** converted into zoom. A separate newer [Škoda MU1440-specific steering adapter](https://github.com/omonob/MHI2-Carplay-Maps/tree/main/src/steering-mu1440) accepts the narrowly observed `updateEncoder2(4,40,±1,0,1)` and sends semantic commands to the omonob core's localhost UDP 7032. **There is no established SEAT-specific adapter or verified SEAT wheel ID in that source**; published SEAT/790 reports still list zoom unverified or not working.

An eventual *our-project* SEAT input adapter must target **our single existing control/session authority**, not start the omonob video core or a second CarPlay, MOST, source-111 or zoom writer. Protect OEM listener dispatch/confirmation, Back, volume and menu scrolling. Route zoom only when the qualified current CarPlay VC owner/map focus and session are known, and verify the actual phone app's response (Google Maps and Apple Maps preferred; Waze alone is not a decisive zoom test). An eventual settings-menu key route is **WP2** and must be separately focus/ownership gated.

**No bridge/remap until the passive map is accepted.** It is insufficient to replace `KEY38/39` by `KEY40`: wheel rotation and push are separate callback families.

## 5. Required handoff back to the maintainer

Produce a concise, sanitised English report containing:

| Field | Required |
| --- | --- |
| Tested unit | SEAT/CUPRA model/year, exact train/MU, cockpit hardware, existing mod/provenance (without private IDs) |
| Collection source | Stock trace or DebugSPI socket, availability, actual transport, source/build SHA, QNX ELF details, path differences |
| Reproduction | Commands actually executed, duration, frame counts, text count, raw cap/truncation and any error |
| Physical event matrix | Per control: physical action, UI context, exact KEY/ENCODER tuple, repeat count, confidence and observed OEM effect |
| Unresolved | VIEW/Assist, missing events, non-matching frames, source/loader differences; **do not make up IDs** |
| Proposed adapter | Most additive callback location and evidence it preserves the stock event/listener flow |
| Next reviewed test | One bounded, reversible next step and explicit abort/restore conditions |

Use the following result classification: `READY_FOR_SEAT_PASSIVE_CAPTURE`, `PASSIVE_CAPTURE_COMPLETE`, `PARTIAL_LOGGER_PATH`, `DEBUGSPI_ENDPOINT_UNAVAILABLE`, `INPUT_MAPPING_INCONCLUSIVE` or `BLOCKED_NEEDS_OWNER_REVIEW`. Never label an untested SEAT adapter `WORKING`.

## 6. Paste-ready AI/Codex task

> Read this complete guide and its referenced public sources. You are helping map real physical keys and rotary controls on a CUPRA Ateca P4708_1/MU1409/Continental 790, using the Škoda MU1440 passive-capture **method**, not assuming its numeric key IDs are identical. First inventory source/build/firmware prerequisites and the actual existing SEAT Java/DSI logging route without changing the car. Select the least-invasive Gate B path. Rebuild and test the project's bounded receive-only logger in the pinned QNX toolchain only if its prerequisites are proven, and prepare a dedicated removable-media capture package with the path check adapted to the verified SEAT mount. Give the owner a one-action-at-a-time, parked two-console plan with monotonic operator notes. Decode off-car, adapting the offline parser under tests if SEAT frames differ. Produce the sanitized physical input matrix, confidence classification, unresolved gaps and an evidence-based proposal for a **future** additive SEAT adapter preserving original listener calls. Do not install JAR shadows, disable firewall, overwrite omonob, send DSI inputs, remap controls, touch MOST, or change CarPlay ownership as part of input discovery. If blocked, report the exact observed blocker and safest next evidence instead of guessing.

**Success = a measured SEAT input inventory with repeatable evidence**, not a working zoom patch or a claimed universal key map.
