# MU1440 IOC/V850 and vehicle CAN access: architecture, verified interfaces and open limits

> **Research status · 2026-11-05:** **HISTORICAL HARDWARE RESEARCH.** Original static or measured evidence only; not an instruction to change clocks, voltage, boot or flash. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


**Status:** exact-build static research + explicitly labeled historical comparator; **not vehicle-validated CAN access**  
**Date:** 2026-10-12  
**Target:** Harman Škoda `MHI2_ER_SKG13_P4526_MU1440` (MQB)  
**Research question:** Can head-unit software read data received from vehicle CAN and transmit CAN messages, and where is the real boundary between high-level OEM calls and raw frames?

> This is an interoperability and architecture note. It does not include OEM binaries or firmware modifications, does not authorize active CAN traffic, and does not claim that a general-purpose raw CAN device/API has been discovered on MU1440.

## Short answer

1. **CAN-related initialization on the exact V850 IOC application is confirmed from original firmware bytes:** its power-on script contains `Z 03 1E 00 // register CAN at MBC` and an adjacent 500-kBaud-default comment. The `Z` implementation, MBC identity and physical bus have not been fully decoded.
2. **High-level vehicle-state *read interfaces* exist in exact-build software.** The decompiled DSI ReplyServices include standstill, reverse, parking brake, trip/temperature and high/mid-frequency vehicle-state callbacks. The native GAL symbol inventory exposes vehicle-speed reporting and relevant DSI-spy listener surfaces. This is a **static interface finding**, not proof that every value is live, sourced from CAN, or available to an arbitrary application.
3. **High-level OEM *write interfaces* also exist:** the exact `DSICarKombiProxy` serializes settings requests through DSI remote method calls. They control predefined UI/cluster/vehicle-feature settings and are **not equivalent to sending arbitrary CAN frames**.
4. **Raw CAN frame RX and unrestricted frame TX from MMX/RCC remain unproven** on this build. Neither a verified ID/DLC/payload subscription nor an arbitrary CAN send service and complete native source-to-sink call chain has been recovered.
5. Historical independent Harman MIB2 research describes **RCC <-> Renesas V850 over SPI**, restricted stock CAN transmission on an infotainment bus and a separate vehicle gateway. This is a relevant comparator, **not an assumption that every historical offset, API, filter or security property is identical in MU1440**. See [DEFION Research Labs](https://defion.security/en/research-labs/volkswagen-auto-group-mib-infotainment-system-unauthenticated-remote-code-execution-as-root/).

### Evidence labels

- **E1 — exact original binary/assembly:** bytes or instructions in the selected MU1440 image.
- **E2 — exact-target static interface:** corresponding MU1440 decompiled Java class, method, native symbol or configuration; runtime provider may still be unknown.
- **H — historical comparator:** externally published analysis of another Harman MIB2 context.
- **I — architectural inference**, not a demonstrated MU1440 path.
- **OPEN — specific missing proof**; never interpret as evidence of impossibility.

## Communication architecture and boundaries

```text
                  Harman MHI2 head unit (J794)
+----------------------------------------------------------------+
| MMX / application domain                                       |
|  HMI / ASL Java                                                |
|      <-> DSI proxies / reply callbacks                         |
|      <-> native OEM services (e.g. GAL SensorSource / DSI-spy) |
+-------------------------------+--------------------------------+
                                | internal OEM communication
                                v
+----------------------------------------------------------------+
| RCC / QNX control domain                                       |
|  IOC control, state and wakeup handling; IPC service providers  |
|  separate /dev/ipc/ipc6 SWDL update client (NOT a CAN API)       |
+-------------------------------+--------------------------------+
                                | RCC <-> IOC runtime messages
                                | SPI: historical Harman evidence
                                | exact MU1440 mapping OPEN
                                v
+----------------------------------------------------------------+
| Renesas V850 / IOC                                             |
|  Embedded power-on script; "register CAN at MBC"                |
|  CAN controller setup, RX filters/dispatch, permitted TX        |
|  functions: exact addresses/semantics still OPEN                |
+-------------------------------+--------------------------------+
                                | CAN controller / transceiver (I)
                                v
                    Infotainment CAN (H / I)
                                |
                         Vehicle gateway (H)
                                |
                      Other vehicle networks

Separately: instrument-cluster content/display control uses
its own DSI/BAP/MOST / DisplayManager paths. A DSI setting
write must NOT automatically be classified as CAN TX.
```

The existence of a physical CAN-capable IOC and of high-level CAN-derived information does not establish an MMX raw-socket interface. Equally, having an OEM method that changes a dashboard UI setting does not prove the method's sink is CAN rather than another OEM protocol.

## Direct evidence in the exact V850 application

Selected archive member: `IOC/Main/21/default/V850app_MQB.bin`; size **1,093,568 bytes**; SHA-256:

```text
9be22328dab863e055e6ec37e7b0bd7c76a89553752891ae5cf6ff972672535b
```

The existing Ghidra 12.1.3 V850:LE:32 import uses an initialized memory block beginning at `0x00800000`. The VAs below are **imported addresses** (= file offset + that chosen base), not independently proven live MCU physical addresses.

| File offset | Imported VA | Exact short string / finding | Meaning and limit |
|---|---|---|---|
| `0x94ABC` | `0x00894ABC` | `AU_MIB2-A239-C0-MBC_Ver:-T04` | MBC-related build marker, not its hardware identity |
| `0x94FC0` | `0x00894FC0` | `@start` | Start of embedded power-on script |
| `0x9562F` | `0x0089562F` | SPI setup annotated 250-kbaud mode 2 | Distinct serial initialization |
| `0x95672` | `0x00895672` | IOC_INT / J5 `BIOS` handshake annotation | Startup context |
| `0x957DD` | `0x008957DD` | `default is 500 kBaud` | Comment only, not decoded register value |
| `0x957F5` | `0x008957F5` | Commented-out `CAN 1MBaud` line | **Inactive**; its `07FF/07FE` words are not a proven live filter |
| `0x9582D` | `0x0089582D` | `Z 03 1E 00 // register CAN at MBC` | E1, actual startup-script text; `Z` handler not yet traced |
| `0x9586F` | `0x0089586F` | SPI2 open/register at MBC | Another MBC interface, distinct from the CAN line |

Original firmware also contains generic messaging names (`tx_fifo`, `tx_sync`, `resend`, RX/TX ACK/NAK), communication statistics (`receive`, `transmit`, `lost`, `txError`, `rxRaw`, `txRaw`) and gateway-mode diagnostics around file `0x8112C..0x816C8`. These show general bidirectional messaging infrastructure. **No confirmed CAN-specific function/XREF attribution follows from those strings alone.**

**Analysis caveat:** the retained Ghidra pass lists 3,764 candidate functions but reported invalid-reference/decompiler warnings; string XREF recovery did not identify the CAN dispatcher. A basic 32-bit pointer scan of original bytes did not find naïve absolute references to the script text; this does not establish that scripts are unused. Validate bank/section layout and V850 instruction semantics before promoting `FUN_` candidates into named CAN routines.

## Concrete high-level read functions found in MU1440 software

These are names present in the corresponding decompiled `de.esolutions.fw.comm.dsi.*.impl` **ReplyService** dispatch code. They establish typed callback contracts (E2), not a measured on-vehicle CAN feed.

| Exact callback / service | Static finding | Interpretation |
|---|---|---|
| `DSIGeneralVehicleStatesReplyService.updateVehicleStandstill(boolean,...)` | Switch case 7 | Standstill state |
| `updateReverseGear(boolean,...)` | Case 17 | Reverse-gear state |
| `updateParkingBrake(boolean,...)` | Case 37 | Parking-brake state |
| `updateTankInfo(TankInfo,...)` | Case 8 | Structured tank info |
| `DSICarVehicleStatesReplyService.updateDynamicVehicleInfoHighFrequent(...)` | Present | Typed frequent vehicle-state updates; underlying fields/provider to trace |
| `updateDynamicVehicleInfoMidFrequent(...)` | Present | Typed medium-frequency vehicle-state updates |
| `DSICarKombiReplyService.updateBCTotalDistance(...)` | Case 40 | Trip/odometer-related typed distance |
| `updateBCOutsideTemperature(...)` | Case 45 | Outside-temperature update |
| `updateBCCoolantTemperature(...)` | Present | Coolant-temperature update |
| `updateBCOilTemperatureValue(...)` | Present | Oil-temperature update |
| `updateBCDigitalSpeed(boolean,...)` | Case 54 | Digital-speed **display flag**; not a numeric vehicle-speed telemetry value |

The exact-target native `gal` symbol/string inventory also contains `SensorSource::reportSpeedData` (mangled `_ZN12SensorSource15reportSpeedDataEibbbi`), `CDSISpyEvent_UpdateVehicleSpeed`, and `DSICarKombiListenerProxy`, `DSIGeneralVehicleStatesListenerProxy`, `DSICarVehicleStatesListenerProxy`. Its sensor configuration has `dsispy.attributesCarKombi`, `attributesGeneralVehicleStates`, `attributesCarVehicleStates` and `forceSpeedEnabled:false`.

**Likely first read-only integration seam:** trace a stock GAL/DSI subscription and its native provider to obtain already-processed vehicle state (speed and others) without creating a new raw-CAN service. Do not label a DSI value “a directly decoded CAN frame” unless its native data-source chain is established.

## Concrete high-level write functions found in MU1440 software

These **exact** methods are present in decompiled `DSICarKombiProxy` and serialize arguments into a DSI `remoteCallMethod((short)N,...)` request (E2):

| Method | DSI method ID | What this actually demonstrates |
|---|---:|---|
| `setBCDigitalSpeed(boolean)` | 19 | OEM digital-speed display setting; **not a fabricated vehicle-speed measurement** |
| `setBCSpeedWarning(BCSpeedWarningSettings)` | 25 | OEM speed-warning setting request |
| `setBCMenueConfig(BCMenueConfiguration,int)` | 111 | OEM BC menu configuration request |
| `setDCBrightness(int)` | 152 | OEM display-brightness setting request |
| `setDCDisplay1MainSelection(DCMainItems)` | 194 | OEM selection of a supported display item |
| `setDCDisplayViewConfiguration(DCDisplayViewConfiguration)` | 199 | OEM view configuration request |

These are **write-capable RPC contracts**, not proven final physical CAN transmissions. Their provider, permissions/availability and eventual transport must be followed independently. In particular, cluster/MOST/BAP traffic should not be conflated with CAN.

## Separate RCC-to-IOC update finding — not runtime CAN

Static disassembly of the MU1440-labeled standard `mib2_ioc_flash` and separately packaged Emergency-IFS `mib_ioc_update` confirms an RCC IPC-SWDL flow using **`/dev/ipc/ipc6`**, transferring new image chunks up to **224 bytes**. This only demonstrates a firmware-update sender; it is not a raw CAN read/write endpoint.

The standard tool also has an important **static retry-path anomaly**: its data routine `FUN_00102410` (ARM imported VA `0x00102410`) zeros a local 256-byte buffer on entry, and first argument zero skips the file read while the outgoing copy still uses that local buffer. The transfer-status handler `FUN_00102540` makes such retry calls. This supports a possible **zero-payload retry** defect; runtime reachability, receiver treatment and actual programming behavior were **not** tested. The emergency updater's corresponding `FUN_00101ED4` uses a persistent buffer and must not be treated as an identical binary. No flash or update operation was performed.

Neither a sender-side lack of evident whole-file hash checking nor this retry anomaly establishes IOC receiver validation behavior, nor does it imply a general vehicle CAN access path.

## Explicit answer matrix

| Capability or claim | Status on exact MU1440 | Evidence class |
|---|---|---|
| Embedded V850 startup text registers CAN at MBC | **Confirmed** | E1 |
| Exact controller register setup, CAN bus and acceptance filters | **Open** | OPEN |
| RCC/V850 SPI architecture and restricted stock TX, on a studied historical Harman MIB2 | **Documented historical comparator** | H |
| Structured OEM DSI vehicle-state callbacks | **Confirmed in code, live availability untested here** | E2 |
| Native GAL vehicle-speed-related consumers | **Confirmed symbols/configuration, actual provider not traced** | E2 |
| General MMX/RCC raw CAN receive interface (CAN ID, DLC, payload) | **Not demonstrated** | OPEN |
| Structured OEM DSI settings-write methods | **Confirmed in code, physical transport unresolved** | E2 |
| Arbitrary CAN frames sent using *stock* MMX/RCC | **Not demonstrated; historical prior art reports restriction** | OPEN/H |
| `/dev/ipc/ipc6` as an IOC SWDL/update channel | **Confirmed** | E1 |
| `/dev/ipc/ipc6` as raw CAN channel | **Not demonstrated** | OPEN |
| Direct access to other vehicle networks through the gateway | **Not established** | OPEN |

“Not demonstrated” means the current evidence does not prove a feature; it is not an assertion that no such path can ever exist.

## Recommended next investigations (offline first)

1. **Typed read path:** locate the stock GAL `SensorSource` and DSI-spy callbacks, provider registration and subscriptions; trace numerical speed and state updates to their native source. Deliver an exact read-only callback/source map.
2. **Script command decoder:** reconstruct real V850 ROM/bank layout and the embedded interpreter, then decode `Z 03 1E 00` and its MBC registration calls with manually checked disassembly. A comment is not a controller-level proof.
3. **IOC communication path:** separate CAN RX/TX code from generic gateway/SPI queues; identify acceptance filters, message envelopes and permitted-TX dispatch if evidence supports them, without assuming full raw access.
4. **RCC runtime provider:** establish the exact IOC SPI/IPC runtime peer and its exported events, separately from `ipc6` SWDL.
5. **Trace one benign predefined OEM DSI write** to its final service/transport. Call it CAN TX only if the verified native route actually reaches the IOC CAN path.
6. **Compare platform variants:** MQB/MQBTT/MLB script/handler regions may clarify what is a fixed chipset behavior versus platform configuration.
7. Any eventual physical validation should start with passive OEM telemetry or a separately scoped isolated read-only bench capture; this document contains **no CAN-transmission or firmware-flashing procedure**.

## Relationship to AltScreen / Virtual Cockpit

This research is orthogonal to the existing Stream-111 and [FPK firmware/control access](../firmware/FPK_FIRMWARE_AND_CONTROL_ACCESS.md) work. CarPlay/VC maps are presented using stock display/DSI/BAP/MOST contracts. These contracts already provide useful high-level state and writable settings surfaces, but they should not be used as shorthand for a raw CAN API.

## Sources and reproducibility limits

- Exact identified source: `MHI2_ER_SKG13_P4526_MU1440`, selected `V850app_MQB.bin`, SHA-256 above. The original OEM firmware and bulk Ghidra programs/disassembly are **not redistributed** in this public repository.
- Exact MU1440 DSI Proxy/ReplyService decompilation and native GAL symbol inventory underpin the E2 method names above. Decompilation/interface presence alone is not a vehicle runtime test.
- Historical architectural reference: [DEFION Research Labs — Volkswagen Auto Group MIB infotainment system](https://defion.security/en/research-labs/volkswagen-auto-group-mib-infotainment-system-unauthenticated-remote-code-execution-as-root/). Keep the historical platform attribution; do not copy an assumed transmit whitelist or attack-chain conclusion onto MU1440.
- Relevant project methodology: [Research method](../../RESEARCH_METHOD.md), [Publication privacy](../../PUBLICATION_PRIVACY.md). No raw firmware, VINs, private filesystem paths, credentials, or vehicle/location captures are included.
