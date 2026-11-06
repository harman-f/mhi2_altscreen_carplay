# P5 Vehicle Data — MU1440 vs LuKa / kamgurgul source delta

**Research status · SOURCE COMPARED / PHONE-SIDE ACCEPTANCE OPEN**


**Evidence boundary:** The project's developer reports that physical
injection tests have observed packets being sent. This does **not** by itself
demonstrate phone-side opt-in/acceptance or a measurable improvement in Maps.
Do not regress or rewrite the existing feature to clone a different stack.

| Layer | Existing harman-f source (NVIDIA MHI2 MU1440) | LuKa MHI2Q source | Suggested action |
| --- | --- | --- | --- |
| Real car data | `modules/carplay/source/vehicle-data` plus target-specific HMI producers: `mvs_core` 8-sample bounded ring, `mibr_vdata`, `mibr_vstatus` and `mibr_vdata_hook` | `VehicleDataModule.java` gets DSI speed, reverse, standstill, range, temp, warning at 200 ms; lazy listener init and per-DSI validity | Compare exact DSI API validity and speed source on Škoda; preserve our bounded source format |
| Ownership | Hook interposes **existing** `iap2_gps_data_send` in `dio_manager` and forwards stock unchanged before optional `$PASCD` with same handle | Native `hook/vehicle` adds commands to existing SendIAP2 owner, hooks Identify & Start/Stop; stock preserved | Our same-owner hook is simpler; do not introduce a second session |
| Request gate | Current model relies on existing Harman driver filtering data based on Identify advertisement and phone Start requests; own engine gate is held open | Explicit hook checks `0xFFFA/0xFFFC`, `0xA100/0xA102`, negative Identify replies | **High-priority evidence gap**: record actual Identify component 20/21/22 and Start/Stop, not just call into driver. Test after reconnect |
| Timing and freshness | Speed ring age <=1500 ms; stock NMEA observation; status latest source <=90s; periodic status refresh up to 10 s | 5 Hz source snapshot, ~1 Hz speed batch, change-based status max 1 Hz, drop gaps >2s | Compare real cadence, throttle periods and no stale values on session rollover; do not assume a faster source is useful |
| Units and validity | Project-generated bounded speed and native status fields; stock data unchanged | Prefers `realVehicleSpeed`; reverse + standstill; unit conversion; outside-temp valid-flag bug discovered and fixed | Check concrete current Škoda DSI validity (particularly `CarBCTemperature.state`); compare reverse/standstill transition |
| Payloads | `$PASCD` and `0xA101` range/temperature/warning | Same functional types; engine type adds declared component, vehicle speed per subscription | **No missing primary feature category** to import |
| Extended display | None claimed for P5 | iPhone battery/telephony BAP, Siri short-key in adjacent modules | Move to P2/phone input track, not a P5 rebuild |

## Precise phone-impact proof

Four distinct observations are required:

1. **Source valid:** DSI data and unit validity observed. Stock NMEA unchanged.
2. **Send handed off:** our hook records `sent_requested`/`sent` and driver return;
   if API returns success, do not infer wire delivery solely from that.
3. **Phone opted in:** Identify advertised speed/status and real iPhone sent
   corresponding Start messages; log Stop/reconnect and Identify rejection.
4. **App effect:** controlled drive under poor GNSS or compare independent
   route/dead-reckoning/Map output with the feature off vs enabled. Map/UI
   visual change is not guaranteed: iOS may use data silently.

Existing project source:

- [Our Vehicle Data source](../../../modules/carplay/source/vehicle-data/)
- [Our documented limitations](../../architecture/OPTIONAL_VEHICLE_DATA_FEATURE_OVERVIEW.md)

Upstream:

- [LuKa vehicle-data notes](https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/docs/connect-and-usb/VEHICLE_DATA_TO_PHONE.md)
- [LuKa hook](https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/hook/vehicle/vehicle_hook.c)
- [LuKa Java DSI source](https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/java_patch/com/luka/carplay/core/VehicleDataModule.java)
- [kamgurgul's VehicleDataModule](https://github.com/kamgurgul/mib2q-carplay/blob/master/java_patch/com/luka/carplay/core/VehicleDataModule.java)

Do not claim `kamgurgul` is a verbatim repository fork: the GitHub
repository is independent, but its VehicleDataModule source explicitly
credits LuKa. **Exact blob comparison completed:** LuKa\'s `VehicleDataModule.java` at `df73e061a29c4d996550716987f42a9243daa09a` and kamgurgul\'s at `5c460600c9205cdafa2c4fecd7e2210b8606aedb` have the **identical Git blob** `2527ce6e166aacba4ea13f31497705d1cbeede32` (353 lines). That confirms byte-identical file content at these revisions, not that either entire repository was forked. Preserve LuKa attribution.
