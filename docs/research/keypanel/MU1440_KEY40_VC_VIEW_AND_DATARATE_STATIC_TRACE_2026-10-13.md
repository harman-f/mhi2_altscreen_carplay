# MU1440 KEY40 / VC VIEW / ChangeDataRate: static evidence boundary (2026-10-13)

**Status:** sanitized exact-MU1440 decompilation audit cross-referenced with the user's existing successful 300 s Dual R2 capture. No new vehicle test, no new runtime hook, no deployment. Full proprietary decompile stays in the private Research repository. Related bench-only zoom work: draft PR #36, `work/mu1440-zoom-input-v1`.

## One-line conclusion

Physical right roller PRESS (KBD4/KEY40), the stock HU hardkey pipeline and the Kombi native graphics stream data-rate arbitration can be traced. **None of these is by itself an authoritative feedback channel for the AID's absolute five-state VIEW or currently focused VC menu row.** Keep contextual takeover disabled until proven.

## KEY40 exact HU key path

```text
DSIKeyPanelListener.updateKey2()
 -> AslTargetSystemKeyPanelHandling.updateKey2()
 -> processKeyEvent()
 -> submitHardkeyFilteredWithTouchInteractionCheck()
 -> KeyLockServiceImpl.processKeyEvent() [lock evaluation]
 -> SystemKeyUtil.createAndSubmitHardkeyEvent()
      -> sendHmiEvent()
           -> HardKeyReader.findDsiKeyToASLSystemHKEvent(...)
           -> System eventDispatcher.createAndSubmitHardkeyEvent(...)
      -> notifyKeyListeners(...)
```

Crucial previously missing mapping source: `SystemKeyUtil.createReadHardKeyReader()` loads `ServiceManager.configManagerDiag.getKeyTimesAndMappingsData()`. Exact (keyboard4,key40,state) -> HMI hardkey IDs and eventual listeners remain to be decoded from that configured mapping. Never silently equate a five-step sequence of KEY40 **presses** correlated with user-announced VIEW changes with a proven absolute VIEW-state sender; separately map the physical steering VIEW button, whose raw ID is not independently established.

The exact MU1440 `mostkombi.kombiview.controller.KombiViewCategoryManager` returns an empty category list and special-cases only the NavInfoAdapter service; `kombiview.states.RunningState` has no five-stage VIEW publisher. Name similarity is not code evidence.

## ChangeDataRate: different functional domain

```text
DSIKOMOGfxStreamSink.ATTR_DATARATE (raw 0 OFF,1 REDUCEDBANDWIDTH,2 FULL)
 -> ChangeDataRate.dsiKOMOGfxStreamSinkUpdateDataRate(...)
 -> ChangeDataRateSequence
      -> NavigationMapService.setMapVisible/Invisible (when appropriate)
      -> DisplayManagementService.setDataFrameRate(0/1/10 [stock])
 -> DisplayManagementAdapter.setDataFrameRate()
      -> ASL event 1075841829
```

Exact related `DisplayManagementAdapter`: current Kombi display datapool 2110010, frame-rate datapool 2110011; display context event 1075841828. `NavigationMapAdapter`: Kombi map status 1110044, map visibility 1110045, visible/invisible events 1074841845 / 1074841846.

Observed `f902/tag53` class association to `...streamsink.usecases.ChangeDataRate` and two payload variants is consistent with a producer/data-rate path. It **did not change at any of the five annotated VIEW presses**. Never use it as a five-position view code or alone as proof of visible CarPlay focus. Separate Research already prepared a two-class reversible Java producer-policy prototype preserving the raw DSI value and using a volatile DIRECT lease; that is not a new deployed/validated VIEW sensor.

## DSI ABI permits more *potential* passive observations; capture did not prove emission

In exact MU1440 DSI proxy/reply bytecode:

| Method | Wire ID | Direction |
|---|---:|---|
| `setDCActiveDisplayPreset(int)` | 192 | HU outbound |
| `setDCDisplayViewConfiguration(...)` | 199 | HU outbound |
| `updateDCActiveDisplayPreset(int,int)` | 208 | HU inbound callback |
| `updateDCDisplayViewConfiguration(DCDisplayViewConfiguration,int)` | 219 | HU inbound callback |
| `requestDCDisplayPresetsList(...)` / `responseDCDisplayPresetsList(...)` | 187 / 189 | request / response |

Main-selection/setup callbacks for displays 1/2/3 are also declared, but not demonstrated to be actual AID selection/focus feedback in this vehicle. Previous 300s dual VIEW sequence showed no identified 208/219. Wire method ID is **not** an automatically valid `setNotification` attribute ID. Before a passive observer, resolve interface attribute constants, actual subscription configuration, vehicle capability and validity flags. Never blindly add numeric 208/219 subscriptions or mutate presets as an observational test.

## Dual R2 alignment and decision

Five measured KEY40 presses in a six-comment, FullScreen-to-FullScreen sequence; four immediate post-key ±850ms windows had no unique VIEW transition record beyond the ordinary press/release pair. High-rate `f902/31`, `f905/94`, Komonav `f904/38-f905/38` and f902/53 do not encode a verified five-position VIEW field. Eleven semantic native map zoom steps *are* independently correlated to right rotary + DebugSPI f904/56 + DSIBAP 50/45. Radio BAP 49/36 can run in background and does not establish visible audio menu focus.

**Required next steps:** exact configured (4,40) key mapping and HMI receiver inventory; discover genuine preset/view/main-selection subscription and emitting side; search AID-local MCU/CAN if no HU-side feedback; keep source111+DIRECT+VC-map-focus conjunctive policy in PR #36 fail-open STOCK. The semantic MapScale interception must be located **before** native map-scale mutation and preserve all other OEM input delivery/ACK.
