# omonob Wireless CarPlay Maps V3.1 — experimental MU1440 native wireless port

**Reviewed:** 16 November 2026, Europe/Berlin. **Release:** [V3.1](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/releases/tag/v3.1), published **11:46:43 UTC / 12:46:43 CET** as an **experimental prerelease**. Latest release found during this review; V3.0 is historical and was superseded on the same day. **Scope:** release notes, tagged build manifest, installer code, compatibility guide and offline validation. No device testing, binary redistribution or installation.

## Exact target compatibility

| Firmware | Exact `/ifs/lsd.jxe` size | AID / cluster | V3.1 native wireless status |
| --- | ---: | --- | --- |
| MU1102 | 55,915,411 bytes | 790 / 791 | Retained packaged wireless receiver (experimental release) |
| MU1367 | 55,840,541 bytes | 790 / 791 | **New firmware-specific experimental wireless port** |
| **Škoda MU1440** | **55,840,933 bytes** | **790** | **New firmware-specific experimental wireless port** |
| Škoda MU1440 | 55,840,933 bytes | 791 | **Unsupported** |
| MU1433 | 52,751,492 bytes | 790 | **Wired-only** |
| SEAT MU1447 | 55,712,574 bytes | 790 | **Wired-only** |

The [tagged BUILD_INFO](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/blob/v3.1/standalone/SD_ROOT/BUILD_INFO.json) lists `wireless_firmware = ["MU1102","MU1367","MU1440"]`, one active `iPhone 17 Pro Max` profile, `headunit_accessed=false` and no completed physical acceptance. The [transaction script](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/blob/v3.1/standalone/SD_ROOT/carplay/payload/common/feature-transaction.sh) verifies exact firmware bytes/profile and selects wireless for those three MUs only; `MU1440:790:17PM` is a supported experimental combination. This is not a general MU1440 compatibility claim for other firmware builds or AID791.

## What V3.1 changed

- Added MU1367 790/791 and Škoda MU1440 790 wireless adaptations based on the three firmware-specific HMI SDKs, Bluetooth program windows and exact native-program fingerprints. Original MU1367/MU1440 `connectionmanager` programs are preserved; the MU1102 program is not copied over these.
- Corrected Bluetooth startup object vs the identically named settings object in production configuration merging; the dedicated ARM/QNX helper was rebuilt and its binary format checked. Installer refuses unexpected native binaries or third-party modifications instead of relaxing the gates.
- Migration from known wired predecessor configurations, with first-baseline backup, update and rollback checks. Existing new runtime/receiver source binaries are not necessarily rebuilt from the public distribution.
- **Installer metadata repack on the V3.1 release page** preserves the provided `metainfo2.txt` Windows CRLF and signed prefix; retains `Final Script` and target script path; computes the author's full-directory 7-Zip **SHA1 for data** `f98e4c9162f089363b6a8d6c92cd40112ba902a1`, not merely the hash of `hashes.txt`. Earlier package metadata was incorrect. The publisher instructs replacing the **complete** V3.1 SD media and rechecking SHA256SUMS, not mixing older files.
- Initial wireless use explicitly requires manually pairing iPhone Bluetooth **and** joining the head unit's own Wi-Fi hotspot. The Wireless CarPlay toggle or Bluetooth-only connection does not establish a session. See [bilingual first-use guide](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/blob/v3.1/docs/WIRELESS_CONNECTION.zh-CN_EN.md).

## Validation tiers: package versus working car

[Tag-specific V3.1 validation](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/blob/v3.1/docs/WIRELESS_VALIDATION.zh-CN.md) reports **396** current-profile and **1,071** historical offline install/migration/regression assertions (nine old releases, 49 combinations). Three HMI SDKs each pass 296 menu-contract and 92 profile-identification checks; Bluetooth has 39 entry-signature checks across three originals including 15 compared critical function windows for 1367/1440; configuration merging has 36 checks.

**Crucial limitation:** none of this proves actual vehicle success. `headunit_accessed=false`. In-car SWDL acceptance of the signed metadata (even after repack), QNX load, Bluetooth/Wi-Fi pairing, audio, touch, stream-111 cluster map/mirroring, first/cold start, USB/wireless switching, parking/assist coexistence and long-term stability are **not accepted** on the new MU1367/MU1440 ports. Release remains prerelease; full native implementation sources are **not distributed separately**, only installer/runtime and technical documents. A GitHub auto-created source ZIP is a repository snapshot, not a rebuildable standalone receiver-source release.

**Atlas editorial action:** replace the one existing omonob entry within the six-item native wireless matrix and update its prominent MU1440 notice. Keep the 4 Nov historical 58×22 score baseline and the 56-entry curated catalog unchanged. Retain the [V3.0 point-in-time audit](OMONOB_WIRELESS_V3_2026-11-16.md) as superseded historical evidence, not the current MU1440 result.

## Primary sources

- [V3.1 prerelease and corrected installer package](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/releases/tag/v3.1)
- [Exact build and physical acceptance manifest](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/blob/v3.1/standalone/SD_ROOT/BUILD_INFO.json)
- [Exact transaction and firmware/profile installer gates](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/blob/v3.1/standalone/SD_ROOT/carplay/payload/common/feature-transaction.sh)
- [Validation and offline check counts](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/blob/v3.1/docs/WIRELESS_VALIDATION.zh-CN.md)
- [Compatibility and unresolved risks](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/blob/v3.1/docs/WIRELESS_COMPATIBILITY.zh-CN.md)
- [First-use Bluetooth and Wi-Fi connection guide](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/blob/v3.1/docs/WIRELESS_CONNECTION.zh-CN_EN.md)
