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

## Additional exact mapping-storage discovery (2026-10-13)

In exact `de.vw.mib.configuration.internal.generated.ConfigurationManagerImplGenerated.getKeyTimesAndMappingsData()` (about lines 1773–1778), the method returns **`(int[]) objectSwapperData[24]`** if `isObjectSwapperDataAvailable(24)`, otherwise `null`. The generated class also labels the corresponding field `OBJSWAP_KEYTIMESANDMAPPING_INDEX`. Therefore the full key map is an **externally loaded ObjectSwapper configuration payload**, not encoded as a literal hardkey mapping in `SystemKeyUtil` or `HardKeyReader`. The next offline step is to locate and decode this exact MU1440 slot-24 object from the existing original configuration artifacts, then parse its `HardKeyReader.readTimingAndKeyMapping()` version-dependent structure. There is not yet a verified numeric HMI event ID for (KBD4, KEY40), and no runtime patch is justified on that basis.

## FPK discovery: exact consumer of active preset and exact DSI attributes (2026-10-14)

**This section supersedes the earlier statement that the attribute numbers had yet to be resolved.** The original firmware's *actual emitting/subscription behavior in this particular fitted car* remains unproven.

A more relevant exact-MU1440 package than the nearly empty MOST KombiView facade is `de.vw.mib.asl.internal.car.fpk`:

- `ASLCarFPKSetupTarget.onPowerOn()` instantiates `CarFPKSetupAPIImpl` and subscribes to the DisplaySetup service state. The API instance constructs `DisplaySetupServiceImpl`, `ContentSelectionServiceImpl`, `PresetsServiceImpl` and `FactorySettingsImpl`.
- All FPK `ServiceBase` instances acquire `DSICarKombi`, create a method adapter and subscribe to `new int[]{82}` (`DCVIEWOPTIONS`). Availability check in `ServiceBase.isServiceAvailable(CarViewOption)`: `state == 2 && reason == 0`.
- `PresetsServiceImpl` has `selectedPresetId = -1` and implements `dsiCarKombiUpdateDCActiveDisplayPreset(int presetId,int validity)`: logs it, saves the preset ID, calls `onPresetSelected`, which publishes ASL properties **10862** (predefined selected ID) or **10861** (user-defined selected ID), other -> -1. The callback is an actual in-process HUD-side state consumer, not just an unused DSI interface declaration.
- When `DCViewOptions.getDisplayPresetsList()` becomes available, `PresetsServiceImpl` subscribes `new int[]{97,96,99,98}`, and attaches a response listener; otherwise it unsubscribes. These are respectively **DCDISPLAYPRESETSLISTUPDATEINFO**, **DCDISPLAYPRESETSLISTTOTALNUMBEROFELEMENTS**, **DCACTIVEDISPLAYPRESET**, **DCDISPLAYDEPENDENCYSETUP**.
- Exact `skoda-dsi-audit-r1/result.json` attribute table resolves **82=DCVIEWOPTIONS, 86=DCDISPLAY1SETUP, 87=DCDISPLAY2SETUP, 96=DCDISPLAYPRESETSLISTTOTALNUMBEROFELEMENTS, 97=DCDISPLAYPRESETSLISTUPDATEINFO, 98=DCDISPLAYDEPENDENCYSETUP, 99=DCACTIVEDISPLAYPRESET, 100=DCDISPLAYVIEWCONFIGURATION**.
- Incoming *wire method* **208** calls `updateDCActiveDisplayPreset(int,int)`; **219** calls `updateDCDisplayViewConfiguration(DCDisplayViewConfiguration,int)`. Attribute **99/100** are the notification IDs and MUST NOT be confused with wire method IDs 208/219. Outbound methods **192** `setDCActiveDisplayPreset(int)` and **199** `setDCDisplayViewConfiguration(...)` are SETTERS; passive testing must not invoke these.
- `DCDisplayViewConfiguration` has exactly one exposed field **`int activeDisplayView`** in the exact JXE decompile. This makes attribute **100** a concrete, single-value *candidate* for the five observed hardware VIEW layouts. No exact observed callback/values in Dual R2; do not assert that `activeDisplayView` maps one-to-one to those layouts without live proof.
- Unlike attribute 99, the discovered `PresetsServiceImpl` subscription **does not include 100**. `DCViewOptionListenerImpl` exposes capability states for `getActiveDisplayPreset()` and `getDisplayViewConfiguration()` at mapping slots 5/6, but this is **option availability, not a current value**. The existing successful tracer recorded BC/radio notifications yet no demonstrated active VIEW callback.
- `Preset` types are `1=individual,2=classic,3=driving profile`; states `0=empty,1=predefined,2=user defined`, and a preset record stores selection/setup for Display1–3. These *configuration presets* are NOT necessarily identical to the physical five VIEW layouts; treat 99 as configuration telemetry and 100 as the more direct candidate for visual VIEW feedback.
- `DisplaySetupServiceImpl` separately subscribes **86,87** to Display1/2 setup values; no discovered FPK service is already a proven active menu-row focus publisher. `DCMainItems` offers flags (navigation, audioMedia, telephone, tripScreen etc.), but content/capability flags are NOT synonymous with the currently highlighted AID top-level menu row.

### Minimal safe qualification plan

1. On original system, passively determine whether `DCViewOptions` attribute 82 reports preset list + active preset + display view configuration as available; log state and reason, no setter calls.
2. If 100 is supported by the fitted AID, create a narrow **read-only, exact DSICarKombiListener observer** subscribed to genuine attribute **100** (and preferably 99 as a cross-check), accepting only valid callbacks; record raw values, time, and reconnect/restart behavior. Do not glob the entire DSI system or globally change any dispatch.
3. Correlate `updateDCDisplayViewConfiguration(...).activeDisplayView` with the existing five-step visual cycle and the return to FullScreen; separately ask whether pressing the physical VIEW key or right roller triggers each transition. A value must survive independent re-entry and missed-event tests to serve as absolute VIEW state.
4. For CarPlay focus, additionally prove *actual* VC map visibility and DIRECT owner; neither presetId 99 nor activeDisplayView 100 automatically equals `vc_map_focus`.
5. If 100 is unsupported or silent, consider AID-local ownership/MCU/CAN and stop inferring focus from unrelated `f902/tag53` stream data rate or passive radio BAP traffic. Keep existing zoom PR fail-open OEM.

Proven source fixtures: exact `IGNORE:.../java/de/vw/mib/asl/internal/car/fpk/{ServiceBase.java,ASLCarFPKSetupTarget.java,api/impl/CarFPKSetupAPIImpl.java,usecases/presets/service/PresetsServiceImpl.java,functions/DCViewOptionListenerImpl.java}`, `.../java/org/dsi/ifc/carkombi/{DCViewOptions.java,DCDisplayViewConfiguration.java,DCDisplayPresetsListRecord.java}`, and `projects/mhi2-qemu-windows-skoda/evidence/skoda-dsi-audit-r1/result.json`. No proprietary raw firmware or private user trace is copied into the public report.

### Additional adjacent DSI attribute family and scope distinction

Exact original DSI attribute table also maps **89 = DCDISPLAY1MAINSELECTION, 90 = DCDISPLAY2MAINSELECTION, 91 = DCDISPLAY3MAINSELECTION**; these callbacks carry `DCMainItems` boolean flags such as `navigation`, `audioMedia`, `telephone`, `tripScreen`, etc. This is a useful passive content/selection-state candidate but **not an established highlighted AID top-level menu row**. `DCViewOptions` includes availability flags for Display1/2/3 main selection, active preset and view configuration independently; `DCViewOptionListenerImpl` maps availability of active preset/display view configuration into two ASL-list entries, not current values. The standalone `DCDisplayViewConfiguration` class's sole scalar `activeDisplayView` differs conceptually from `DCDisplayPresetsListRecord` configurations (record pos/state/type/instance and per-display content), so test 100 and 99 separately and never assume preset ID tracks every cycling hardware VIEW.
