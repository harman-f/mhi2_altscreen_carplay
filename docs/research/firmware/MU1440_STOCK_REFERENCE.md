# MU1440 stock compatibility reference

> **Research status · 2026-11-05:** **FIRMWARE RESEARCH REFERENCE.** Static comparison is not a supported vehicle or installer claim. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


This page is the public hash authority for the first vehicle-tested MHI2 baseline.

No OEM files are redistributed. The hashes allow another researcher to answer the important question:

> Am I actually looking at the same firmware component?

Reference firmware:

```text
MHI2_ER_SKG13_P4526_MU1440
```

## Canonical stock component fingerprints

| Stock path | Size | SHA-256 |
| --- | ---: | --- |
| `/ifs/lsd.jxe` | 55,840,933 | `A55D9CFB69C5756F8202B7F7AA4079D4D5B637AE4C2FD0FE723F1D6816CBEEA8` |
| `/mnt/system/etc/eso/production/dio_manager.json` | 13,129 | `F11FB9A560FB02CBBDF04EACC304B94D9FF86E343CF48484DE099BA517239B3B` |
| `/mnt/system/etc/eso/production/smartphone_integrator.json` | 7,360 | `DD925B8A85AD1ACC9D88DD5E7AEDABC3118C1C8299E107BBAA99B4C145C807BE` |
| `/mnt/app/eso/lib/factories/libdsicarplayproxy.so` | 73,384 | `9CCB46C1C185F9BE507D74D1E46433CABDE2833FC77AC478744EA95629F9BE96` |
| `/mnt/app/armle/usr/sbin/mm-ipod` | 40,297 | `DE99A7F4DD941589C6D5173B7601856275C4EA615229058EC84B8E3EFA748D27` |
| `/mnt/app/armle/usr/lib/libiap2client.so.1` | 18,613 | `C33021B21C5656886E64964EFCF806FDDB4259027C3C1ED396522E7A44ADFDEA` |
| `/mnt/app/eso/bin/apps/smartphone_integrator` | 806,539 | `14B8458144C2CC01D56ECA09129A4D2EA9569E328E19092F3E6497BA322C42E4` |
| `/mnt/app/eso/lib/libairplay.so` | 703,688 | `193A4FD9101EC2AA05E7159CFA307B96500810D379CA74A194F172ADC13A46B5` |
| `/mnt/app/eso/bin/apps/dio_manager` | 686,552 | `4D6867BDD4C99A032D3C634299F36F88DC72AA54E333589A24AF4497A96AEE02` |

## Why these particular files matter

### `libairplay.so`

Primary AirPlay/CarPlay receiver ABI authority for the current GEN2 hook.

A different hash means the current offset/ABI assumptions have not been proven.

### `smartphone_integrator.json`

Defines integration configuration including preload/runtime behavior around the smartphone stack.

### `smartphone_integrator`

Useful process-level compatibility fingerprint when diagnosing startup/lifecycle differences.

### `dio_manager` + `dio_manager.json`

Relevant to the device/CarPlay runtime environment and useful when comparing another MHI2 train.

### `lsd.jxe`

Authority for the Java/HMI side:

- navigation arbitration;
- Kombi/cluster state;
- ViewArea-related HMI state;
- DisplayManager-facing policy.

Do not assume another `lsd.jxe` has the same class layout or behavior.

### iAP2 / DSI components

`mm-ipod`, `libiap2client.so.1` and `libdsicarplayproxy.so` are useful supporting fingerprints when
a target looks superficially similar but the CarPlay/iAP2 stack differs underneath.

## Contributor rule

When adding support for a new train, add a new named compatibility profile rather than weakening the
existing hash gates.

A useful new profile should record:

- firmware train / MU;
- all available component hashes above;
- differences in exported/imported AirPlay symbols;
- whether the direct MOST path exists;
- whether the stock cluster/HMI state machine behaves the same;
- exact vehicle-test result.

Hashes are evidence. Firmware names alone are not.
