# omonob Wireless CarPlay Maps V3.0 — release and MU1440 compatibility audit

**Reviewed:** 2026-11-16 (Europe/Berlin), after [V3.0 experimental prerelease](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/releases/tag/v3.0) was published at 09:19:51 UTC (10:19:51 CET). **Scope:** public release, manifest, installer guard code, source documentation; no live head-unit or iPhone tests. This addendum does **not** re-score the original 58×22 features (baseline 2026-11-04).

## New evidence and release identity

- Canonical repository renamed to [omonob/VW-MHI2-Wireless-Carplay-Maps](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps). Do not treat redirects from `VW-MHI2-Carplay-Maps` as an additional separate project.
- `v3.0` is a **prerelease**, not a general release validated on all hardware. The early `wireless-carplay-maps-v0.2.0-beta.1` package on the same date is explicitly superseded.
- Release provides `Wireless_CarPlay_Maps_Standalone_v3.0.zip` (installer tree under `SD_ROOT`), checksum/installation/history/release notes. Does not publish the complete receiver implementation source-build tree. Public install scripts and frozen runtime binaries exist.
- Publisher documents a direct/native, no-USB-dongle Wireless CarPlay path: Bluetooth stack interposer and iAP2 bootstrap, unit Wi-Fi hotspot/connection manager, independent wireless receiver/media pipeline, HMI Java hooks, OEM main display, cluster map/mirror/cards/zoom. These are **project-release claims**; verify target runtime separately.
- The only active phone profile is **iPhone 17 Pro Max**. This is a stated shipping profile constraint, not an iPhone hardware incompatibility proof.

## Firmware/cluster gate — do not generalize by brand

| Target | Head-unit software identity | Cluster | Native Wireless V3.0 |
| --- | --- | --- | --- |
| VW MU1102 | `/ifs/lsd.jxe` = **55,915,411 bytes** | 790 / AID 10.5, 791 / AID 12.3 | **Receiver and wireless integration packaged**; acceptance still limited |
| VW MU1367 | `/ifs/lsd.jxe` = **55,840,541 bytes** | 790 / 791 | **No — wired mapping only** |
| Škoda MU1440 | `/ifs/lsd.jxe` = **55,840,933 bytes** | 790 | **No — wired mapping only** |
| Škoda MU1433 | `/ifs/lsd.jxe` = **52,751,492 bytes** | 790 | **No — wired mapping only** |
| SEAT MU1447 | `/ifs/lsd.jxe` = **55,712,574 bytes** | 790 | **No — wired mapping only** |

Source: [V3.0 release](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/releases/tag/v3.0); [`BUILD_INFO.json`](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/blob/v3.0/standalone/SD_ROOT/BUILD_INFO.json); [`feature-transaction.sh`](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/blob/v3.0/standalone/SD_ROOT/carplay/payload/common/feature-transaction.sh). The transaction function accepts these exact wired profiles but gates the wireless payload on **`MU1102` only**. The public wireless manifest includes firmware-specific `CarPlayWireless-CP-55915411.jar`, `CarPlayWireless-SI-55915411.jar`, `CarPlayWireless-Touch-55915411.jar`; no MU1440 wireless JAR/profile.

## Why this does not run as native Wireless on MU1440

1. **Packaging gate:** the installer explicitly limits the wireless path to MU1102, so the presence of `MU1440/790/core.so` and wired menu files does not confer a wireless receiver.
2. **Exact HMI/J9 ABI:** `55915411`-specific Java CP/SI/Touch hooks and menu helpers cannot be assumed compatible with MU1440's `55840933` firmware. An actual rebuild/ABI qualification would be required.
3. **Bluetooth/network owner:** `btstack_wrap.sh`, `libbtwcp.so`, `connectionmanager`, `uap0`, hotspot-channel synchronization and PF rules are tightly coupled to the original runtime behavior. [HARMAN-F's exact MU1440 research](../research/mhi2-native-wireless-2026-10/09_END_TO_END_ARCHITECTURE.md) found a generic iAP2 service vocabulary but no active legacy iAP servicegraph node, and identified secure session/iAP Control gaps; it does **not** establish compatibility of omonob's binary interposers with MU1440.
4. **Receiver lifecycle:** MU1440 target-side Pair Setup/Verify, secure control, authenticated peer ownership and iAP-over-Control are still unqualified; the release is not a verified port and must not be cross-installed.

These are observed **missing port/proof conditions**, not evidence that MU1440's Tegra/QNX/WLAN hardware makes native wireless impossible.

## Evidence and validation

- **`RELEASED_EXPERIMENTAL`:** published V3.0 installer and provenance/documentation, developer claims for the MU1102 receiver.
- **`OFFLINE_TEST`:** publisher's [validation report](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/blob/v3.0/docs/WIRELESS_VALIDATION.zh-CN.md) records 355 current-profile assertions, 994 historical assertions, and 92 menu-profile identification cases.
- **Not independently accepted end-to-end:** `BUILD_INFO.json` expressly records `headunit_accessed=false` and `physical_acceptance=NOT PERFORMED FOR THIS LEAN BUILD`. First connection drop, 790 card geometry, switching wired→wireless with USB attached, network-policy coexistence and long-term stability require real hardware validation.
- Standalone installer is not a full source/build release; avoid redistributing frozen proprietary/OEM/SDK receiver components or inferring license from publicly downloadable binary artifacts.

**Atlas editorial outcome:** update one existing omonob native-wireless row in the six-lead matrix (no duplicate lead), its evidence filter and above-the-table MU1440 banner; link this audit, retain the dated scoring baseline, and run CI/Pages publishing checks.
