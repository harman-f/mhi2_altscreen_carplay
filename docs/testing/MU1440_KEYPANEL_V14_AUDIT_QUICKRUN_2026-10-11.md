# MU1440 — native keypanel v1.4 artifact audit and parked quick run
Date: 2026-10-11. Public sanitized record. No changes to firmware, J9/LSD, Parity, MOST or CarPlay source 111.

## Verified offline artifact (not yet a live-v1.4 vehicle PASS)
Source/CI head: `4ab9062bb183859ede738d95b43f57524dd25390`; workflow run [38090171136](https://github.com/harman-f/mhi2_altscreen_carplay/actions/runs/38090171136), successful host self-test, type-1/inner-0104 integration, QNX build and artifact upload. GitHub artifact ID 11683924139, name `mibr-native-keypanel-MU1440-QNX65-ARMv7`.
Downloaded CI ZIP SHA256: `a76acf2d3824856fa2cae072c3b70df8b992a4c62aa3182b0af3add7902f2a10`; archive CRC and all three inner manifest hashes PASS (7 files).
Executable `mibr-keypanel-native`: size **19485 bytes**, SHA256 `2bf23bd2216a51da6ab99a21bc2f7ac2ac85355443555eccb23ed3e0dac94e95`; ELF32 LE ARM EABI5, QNX loader `/usr/lib/ldqnx.so.2`, dependencies libsocket.so.3 and libc.so.3. Companion script SHA256: start `ef8a7bd0133544b7856287a87501acca6260d56cc5544334ea3762031bef4b60`, note `e33f73354d3bdc16c96a3715a11cb500f8b8c3586ea71ee814a5771e28d264ec`. Binary import review and source show RX-only TCP 127.0.0.1:15001; no send/rename/system/exec/kill imports. SD wrapper may remount only SD writable.
**Do not conflate** the CI ZIP with the separately archived private `MIBR-Native-Keypanel-v1.4-QNX.zip`, which has its own distinct package hash. The private video/raw trace is not in Git.

## Capability verdict
| Requirement | v1.4 status |
| --- | --- |
| Passive original DebugSPI MLP capture, 16 MiB raw cap; 4 MiB text cap | YES |
| Inner 0x0104 OEM UTF-16BE text in MLP type-1 frames | YES |
| Live `HK Received` KBD/KEY/KST and derived short/long/double gesture chronology | YES if OEM message is emitted |
| Common monotonic NOTE/EVENT timeline via second SSH console | YES; NOTE before each action |
| Original inner 0x0110 structured records | SAVED RAW, NOT PHYSICALLY DECODED |
| Five raw `updateEncoder2` ints / legacy `updateEncoder` | NO |
| Assist and VC-only buttons on any other bus / complete front-panel mapping | NOT GUARANTEED |
| Native semantic BAP MapScale, VC focus, OEM overlay owner | NO |
| Zoom, ViewArea/SafeArea switch, native/CarPlay switch, button remap | NO: not the job of this recorder |

A success exit after the first TCP connection is **not** itself proof of a full healthy capture (the code can return success after early socket close). Check actual data, duration, STOP note, truncated flags, events and OEM visual reaction. The `GESTURE=SHORT` label is inferred at release, not proof a system action was executed. Missing HK does not mean missing hardware signal. The first live v1.4 run is still outstanding.

## Morning procedure: one parked 240-second run
Prepare the exact CI artifact in a fresh dedicated SD folder `/net/mmx/fs/sda0/esd/carplay-test/keypanel-logger-v14/`; preserve other installs and parity/video state. Check any existing `mibr-keypanel-native-current` pointer and `pidin ar | grep mibr-keypanel-native`; never blindly delete an active/stale pointer. Both SSH shells **must use the same directory**.

Shell 1:
```sh
cd /net/mmx/fs/sda0/esd/carplay-test/keypanel-logger-v14
/bin/ksh keypanel_start_native.sh 240
```
Shell 2:
```sh
cd /net/mmx/fs/sda0/esd/carplay-test/keypanel-logger-v14
/bin/ksh keypanel_note_native.sh
```
Type NOTE **before** each action, do exactly one movement/press, leave 2–3s between inputs, then record the actual OEM visible reaction. Use physical names rather than assuming borrowed VW QEMU key IDs. Record explicit mode `NATIVE_MAP`, `CARPLAY_VC_MAP` or `VC_MENU_FOCUS`; do not infer focus merely from running type-111 source. Suggested priority:

1. `RIGHT_WHEEL +1`, `RIGHT_WHEEL -1`, right press short, right press 3s; separately repeat rotary +/- with VC menu visibly open (menu scroll must remain native).
2. `LEFT_WHEEL +1/-1`, left press short; right Back short/hold, Phone short; left upper/lower short, Voice short only where safe.
3. Right Assist short and **optional** 3s hold only when parked and its OEM consequence is safe; report actual result even if no HK text. Do not touch emergency/hazard controls for experimentation.
4. All **physically present** front-display hardkeys, including Home/Menu and any NAV/CAR/RADIO/MEDIA/APP, and any front rotary/press if present. Do not infer their IDs from VW QEMU; tag actual labels. Existing vehicle associations Home 13/116, Menu 13/78 require isolation for definitive recheck.
5. If direct CarPlay is already stable, compare a short native-map vs CarPlay-map wheel sequence with explicit state notes; do not manipulate the Parity transport to force this comparison.

Let recorder finish or Ctrl+C, then `/quit` in shell 2. Export the new `native-<PID>/` directory: `report.txt`, `combined.log`, `debugspi-text.log`, `debugspi-original.bin`. Share report and combined first, retain raw/optional synchronized video privately. Public Git receives only sanitized conclusions.

PASS gate: socket connection observed, nonzero raw bytes/frames and expected OEM text for a known button, no raw/text truncation, each NOTE attributable to a single action, OEM visual effect noted. If text is silent while raw arrives, label it `LOGGER_PATH_INCONCLUSIVE` and preserve raw. If 240s is too crowded, split into two sessions rather than rush. Do not drive/operate SSH while moving.

## Follow-up — separate from the next quick run
**Update after this historical v1.4 test plan:** The twelve measured five-int wheel records have already been decoded offline from inner 0x0110: right KBD4/encoder40 ±1, left KBD4/encoder44 ±1. Do not deploy a new Java hook solely to rediscover these baseline IDs; see [measured encoder evidence](../research/keypanel/MU1440_F902_FIVE_INT_ENCODER_CAPTURE_2026-10-11.md). Next correlate native-map, CarPlay-map and VC-menu focus with actual semantic OEM MapScale requests, preserving all original DSI callbacks and confirmation behavior. **Primary MHI2 input comparator:** [omonob/MHI2-Carplay-Maps by omonob/QCDWJ](../research/keypanel/MU1440_OMONOB_MHI2_WHEEL_ENCODER_BINARY_PATCH_OPTIONS_2026-10-11.md), not the separate Audi MHI2Q implementation by [yuedizhibo/MHI2Q-CarPlay-AltScreen](../research/keypanel/MU1440_MHI2Q_ALTSCREEN_ZOOM_PORT_BINARY_PATCH_OPTIONS_2026-10-11.md). The user-approved future controls remain source111+confirmed-map-focus zoom, a toggle of two pre-negotiated ViewArea/SafeArea pairs and guarded native/CarPlay presentation ownership without mixed MOST packets. HMI/VC menu injection is a separate research track; there is no dedicated app-launch key.

References: `modules/broker/source/keypanel/mibr_keypanel_native.c`, `tests/keypanel-native/integration.py`, `.github/workflows/build-keypanel-native.yml`, `docs/testing/MU1440_NATIVE_KEYPANEL_CAPTURE.md`; normative Research `MU1440_MASTER_REQUIREMENTS_AUTHORITY.md`.
