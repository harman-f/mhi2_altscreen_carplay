# SEAT/CUPRA MU1409 — AltScreen and native Settings port

**Public collaboration guide · 23 October 2026 · Experimental research, not an installer**

The [MU1440 R57 source baseline](../build/MU1440_R57_SOURCE.md) now supplies the real [OEM Java adapter](../../src/hmi/oem-menu/), [native controller](../../src/native/mibr-control/), canonical registry, GEN2 and parity sources with standalone native build/tests. Start a SEAT-specific menu adapter from those implementations; provide your own exact MU1409 firmware/API inputs locally. The MU1440 OEM widget IDs, artwork, Java ABI and input mapping still require target-specific work. This is a partial source publication with documented external dependencies, not a validated MU1409 installer.

This page describes a proposed joint SEAT/CUPRA port of [mhi2_altscreen_carplay](../../README.md), aimed initially at a contributor's **2020 CUPRA Ateca, `MHI2_ER_SEG11_P4708_1` / MU1409, Continental 790**. Its goal is more than another working moving map: reuse our modular CarPlay video/control architecture, then adapt the **OEM-native HOME/Settings menu** to the SEAT interface. Development can proceed in small, individually agreed steps; no fixed time commitment is expected.

**Start with the actual evidence:** the contributor has already reported a working wired CarPlay moving-map result using an experimental, omonob-derived **MU1409** package, with the same limitations as the original Leon test in [community issue #47](https://github.com/harman-f/mhi2_altscreen_carplay/issues/47). This does *not* mean our own binaries have been tested on his Ateca.

## What already exists

| Reference | Firmware / fitted target | Established result | Important distinction |
| --- | --- | --- | --- |
| Our reference system | Škoda `MHI2_ER_SKG13_P4526_MU1440` / AID10-class | Vehicle-demonstrated Type-111 video, direct transport and guarded stock/direct work; additional HMI and recovery development | Newer integrated source and UI features have their own evidence/release gates |
| [omonob CarPlay Maps VC](https://github.com/omonob/MHI2-Carplay-Maps) | Its explicitly supported original profiles | Existing alternative moving-map and installer design | Not an automatic approval for MU1409 |
| [M.I.B. Bash's omonob module](https://github.com/Mr-MIBonk/M.I.B._More-Incredible-Bash/tree/3a2526a386f54ec7f49bbc32984ef7edb1106d33/mod/carplay_maps_vc/omonob) | Includes **SEAT SEG11 P4709 / MU1447 / 790** | Public integrated installer/profile; its MU1440/790 and MU1447/790 native `core.so` entries refer to the same Git blob | The inspected selector does **not** admit MU1409; this is an omonob integration, not a fourth independent video stack |
| [TheIronShadow's MU1409 adaptation](https://github.com/harman-f/mhi2_altscreen_carplay/issues/47) | SEAT Leon Cupra `P4708` / MU1409 / 790 | Wired Apple Maps, Google Maps and Waze displayed in the cockpit, with framing and input limitations | Third-party experimental implementation |
| Contributor's Ateca report in [issue #47](https://github.com/harman-f/mhi2_altscreen_carplay/issues/47#issuecomment-6286368363) | `P4708_1` / MU1409 / 790 | Reports equivalent working behavior and limitations using the adapted port | Exact P4708 vs. P4708_1 binary identity has not been independently established |

The previously analysed **MU1447** stock firmware is a useful comparator: it shares a complete `libairplay.so` byte profile with the Škoda MU1440 reference, and the existing corpus shows considerable Java/native reuse. The MU1409 contributor separately reported **26,240** common Java class paths versus MU1447, of which **26,202** were byte-identical and **38** differed. Those are reported comparison results; they are not a substitute for hashing and analysing the exact installed `P4708_1` firmware. Its reported `lsd.jxe` size is also not a reliable identity check on its own.

See also [MU1409 auxiliary scaling and bounded queue recovery](../testing/SEAT_CUPRA_MU1409_SCALING_AND_RECOVERY.md) for the 25 October target observation, opt-in zoom percentage and remaining acceptance limits.

## The intended result: two work packages

### WP1 — Qualify our video and control stack on this exact SEAT firmware

The intended pipeline is:

```text
Existing authenticated wired CarPlay session
    → auxiliary Type-111 / GEN2 receiver
    → original H.264 access units (no screen-capture/re-encode requirement)
    → MPEG-TS transport
    → one guarded STOCK/DIRECT media owner
    → qualified MOST / cockpit output
```

We expect substantial source-level reuse, but cannot promise unchanged Škoda binaries. Compare the precise target `libairplay.so` and `dio_manager` ABI, DisplayManager behaviour, QNX loader/startup, MOST endpoint, video block contract and actual cluster geometry before building a target profile. The reference uses `/dev/mlb/isoTX2` and 64 × 188-byte TS blocks; the contributor's prior omonob result is valuable corroboration, but our independent writer/ownership path still needs qualification.

**No OEM menu is required for WP1.** Start with our existing file-based/manual switches and settings. Confirm that the same media owner handles source/start/stop, reconnect and fallback. Test wired video, then independently demonstrate a visible and reversible **STOCK → DIRECT → STOCK** return with original infotainment behaviour intact. Investigate map cropping/ViewArea only against the actual fitted SEAT cluster, not against an assumed Škoda canvas or panel resolution.

**WP1 acceptance:** a reproducibly built and tested target-specific version of *our* runtime; meaningful diagnostics; wired map output; session stop/recovery; exclusive writer; and an independently checked stock restoration. This is not achieved merely by running the already working third-party package.

**WP1 networking prerequisite:** the target's Type-111 `carplay0` PF ingress is a separate **mandatory installer/test-package gate**, not an optional debugging tweak. See the [persistent firewall/profile contract](../installation/TYPE111_FIREWALL_INSTALLER_CONTRACT.md). Collect actual effective rules, installed profile variants and startup/network reload behaviour read-only first; `pf.conf` containing a permit is not sufficient. The eventual reviewed installer must handle backup, all relevant profiles, postboot verification and owned rollback. The initial contributor bundle is not authorised to automatically patch live PF or reload rules during an SSH/CarPlay session.

**Physical controls are a target-specific evidence gate:** [SEAT/CUPRA key-input discovery — AI-agent handoff](SEAT_CUPRA_KEY_INPUT_CAPTURE_HANDOFF.md) explains our actual Škoda passive DebugSPI/DSI capture method and how to adapt it to P4708_1 without assuming identical keys. First obtain a measured physical key/encoder matrix; only then implement a SEAT input adapter.

### WP2 — Port the OEM-native HOME / Settings experience to SEAT

This is the principal new collaboration goal. Our reference development has an OEM-style **HOME → Virtual Cockpit / CarPlay** menu design with presentation/navigation preferences, selectable options, diagnostics and a **single canonical native settings/control interface**. The menu should be usable even when CarPlay is active; it should not create a second AirPlay/iAP2 login, settings store, media writer or arbitrary shell-command channel.

Proposed process:

1. Use the **exact SEAT `lsd.jxe`** to inspect stock HOME/Settings views, Java/J9 classes, ViewHandler/CIO links, widgets, resource/layout identities and the relevant DSI/input relationships. Compare only the required classes with the existing reference analysis.
2. Measure the actual menu viewport and original Back/focus/scroll/re-entry behaviour. Do **not** copy Škoda widget IDs, controller assumptions, keyboard tuples or menu positions into SEAT unverified.
3. Create an **inert UI-only proof** first: a project-owned HOME entry and native-looking settings rows, with no production video/control writes.
4. Attach a thin SEAT-specific Java adapter to our existing versioned native control API. Keep one authoritative registry and separate **stored**, **requested**, **applied** and independently **ACTIVE/visible** status.
5. Activate one setting at a time. Confirm UI appearance, validation/readback, current-session application and actual phone/cockpit effect as **four separate acceptance checkpoints**. Preserve OEM Back/navigation and factory restoration.
6. Add wheel/headunit controls only after passive target-specific event observations. OEM-owned controls remain unchanged unless an explicitly qualified route is active.

**WP2 acceptance:** the SEAT OEM-style CarPlay/Virtual Cockpit menu visibly operates qualified settings and route actions through the shared controller, with normal factory interaction and rollback preserved.

Some recent Škoda HMI development builds already have visual/menu and storage evidence, but not every presentation setting has a demonstrated live ACTIVE effect. Our [current integration status](../status/INTEGRATION_STATUS_2026-10-21.md), [native HMI/control design](../architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md) and [published-source coverage](../status/PUBLISHED_SOURCE_COVERAGE.md) distinguish these levels. This page does not announce a new complete release.

## First practical setup on the contributor's Mac

**Detailed step-by-step setup:** [SEAT/CUPRA MU1409 — local Mac, QNX build and firmware-analysis environment](SEAT_CUPRA_MU1409_LOCAL_ENVIRONMENT.md). This standalone guide is the authoritative entry point for prerequisites, installation checks, directory separation, extraction/conversion, reproducible toolchain and E0–E6 gates. The table below is only an overview.

We can provide a pinned source handoff, reference comparisons, build guidance and focused review; the contributor can run the host tools and explicitly approved parked vehicle tests locally. **Start off-car.** Nothing below authorizes installation, flashing or modification of an ECU.

| Stage | Local work | Evidence to retain |
| --- | --- | --- |
| Host build | Git, Python 3.10+, 7-Zip, Docker or a suitable x86_64 Linux builder, a pinned QNX 6.5 ARMv7 cross-toolchain; JDK/Java tools and Ghidra for analysis | Compiler/container identity, simple ARM ELF smoke build, Java build and hashes |
| Firmware intake | Obtain an original, legitimately accessible **P4708_1** update; record exact train, size and SHA-256; use our [firmware toolkit](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit) in a separate private host directory | Source and component manifests, MMX/RCC/Java extraction result, no changed firmware |
| Binary/Java diff | Extract only required MMX/RCC/Java components; compare `libairplay.so`, `dio_manager`, DisplayManager/MOST configuration, `lsd.jxe`, selected Java classes and HMI dependencies with the MU1440/MU1447 baselines | Exact hashes, method/signature deltas and a small target-portability table |
| Read-only car inventory | With the owner's permission: verify actual firmware, running paths, installed omonob/M.I.B./navigation patches, startup/classpath and rollback resources | Redacted inventory and independent recovery plan; **no remounts or writes** |
| Small gated tests | Only after a reviewed target build, checks and owner approval: WP1 stages, then UI-only WP2 and progressively enabled settings | Per-test observations, rollback result, source/owner/session evidence |

The toolkit's host flow begins with `extract_firmware.py --plan`, followed by deliberate `--component mmx --component rcc --component java` extraction into a **new output directory**. Its documented, pinned JXE conversion wrapper and a Java decompiler help compare the actual SEAT classes. The published [QNX build workflow](../../.github/workflows/build-direct-ts-remux.yml) is a reference for the cross-toolchain pin; on Apple Silicon, check any required `linux/amd64` emulation or use a separate x86_64 builder. Build proof is not live QNX proof.

The maintainer must first assemble and identify a coherent, provenance-reviewed **source snapshot**, including its dependencies and applicable test evidence. The public repository currently exposes several independent experimental components, but not every newest HMI/controller/parity element as one complete buildable target release.

## Suggested responsibilities and collaboration boundaries

**Maintainer/project:** reference architecture and existing MU1440/MU1447 comparator notes; a source pin and build recipe when reviewed; target-delta checklist; proposed SEAT menu-adapter boundary; code/test review; and a safe per-stage acceptance checklist.

**Contributor:** authorised local Mac environment, exact original update/hash if available, read-only installed-unit observations, SEAT menu and input evidence, running pre-reviewed builds/tests, and reporting actual results or limitations. We can narrow the tasks and help with analysis so that he does **not** have to repeat the whole reverse-engineering project alone.

Keep original OEM firmware/classes, private Ghidra projects, credentials/keys, vehicle/phone identifiers and unredacted logs **off public Git**. Reuse existing SSH access only with the owner's specific permission, never by placing credentials in an AI prompt or source file. Any vehicle write, restart or install needs a separate explicit review, reliable backup and recovery route; parked testing only. For shell scripts, audit the target commands/options against the [QNX compatibility contract](../testing/MU1440_QNX_SHELL_COMPATIBILITY.md) and validate unknown SEAT behaviour independently.

## Possible later extensions — separate scope, not prerequisites

- **Actual vehicle-speed feedback to the iPhone** through the existing authenticated CarPlay/iAP2 owner and a validity-checked SEAT-specific vehicle-data adapter. Experimental design/source candidates exist; phone subscription, same-session transport and an on-car effect remain unqualified. Better positioning/smoothness is a hypothesis to measure, not a guaranteed result.
- GNSS, ambient temperature, range/warnings only where genuine source values and CarPlay capabilities are proven.
- **Navigation maneuver arrows/text inside the cockpit:** an additional future work package, *not an integrated feature of the current project*. Existing approaches may be evaluated separately for functional fit and licensing.
- Native wireless, advanced wheel input and more display presets only after their own technical and vehicle gates.

## Useful links

- [Issue #47 — the original MU1409 vehicle report and contributor confirmations](https://github.com/harman-f/mhi2_altscreen_carplay/issues/47)
- [Public firmware-profile map](../research/MHI2_FIRMWARE_PROFILE_MAP_2026-09-28.md) and [portability estimate](../research/MHI2_PATCH_PORTABILITY_ESTIMATE_2026-09-28.md)
- [Module architecture and SEAT/VW boundaries](../architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md)
- [HMI and single-controller specification](../architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md)
- [Optional vehicle-data design](../architecture/OPTIONAL_VEHICLE_DATA_FEATURE_OVERVIEW.md)
- [Firmware toolkit](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit)
- [Original omonob project](https://github.com/omonob/MHI2-Carplay-Maps) and [M.I.B. Bash integration](https://github.com/Mr-MIBonk/M.I.B._More-Incredible-Bash)
