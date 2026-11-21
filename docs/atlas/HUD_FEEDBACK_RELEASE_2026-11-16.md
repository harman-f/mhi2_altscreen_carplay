# MIB Atlas HUD taxonomy and public feedback — 2026-11-16

This documentation-only publication builds on [PR #183](https://github.com/harman-f/mhi2_altscreen_carplay/pull/183). No vehicle/ECU/firmware experiments were performed. The original 58 × 22 scoring baseline is **4 Nov 2026**, and the source-review date remains **16 Nov 2026**.

## Disambiguation
- **OEM / factory HUD:** existing vehicle projector; head-unit route/RGI data adapted into factory navigation or BAP/Java/HMI. CarPlay Type 111 cluster video is a **different** feature. Five source-specific rows (edzenis, ekuka86, LuKa, kamgurgul, ProManiFest2122) now live in the ordinary CarPlay/Android Auto tab.
- **Aftermarket / DIY HUD:** separate hardware, controller and power. Three public source leads are [1e1 direct VW PQ CAN OLED](https://github.com/1e1/arduino-obd2-hud), [Me-in-U Pi/ESP32 CAN+OBD+Android bridge](https://github.com/Me-in-U/headunit-revived-esp32-hud), and [PowerBroker2 ArduHUD OBD/ELM327](https://github.com/PowerBroker2/ArduHUD). An auxiliary screen is not necessarily an optical projected HUD. Speed/RPM support does not imply navigation arrow support or MQB compatibility.
- **Java/J9 retrofit interface:** while factory MIB navigation integrations can use HU Java/BAP classes, no independently verified direct Java API feed to *separately installed* custom HUD hardware was found in these sources. Status remains **not proven**, not absent.
- **Dongle firmware / other peripherals:** nine pre-existing records retained under Miscellaneous, independently filterable from DIY HUD. Do not confuse USB adapter Type111 forwarding with native wireless, factory HUD software, or a projector.

## Feedback and release
The permanent [Atlas feedback issue #187](https://github.com/harman-f/mhi2_altscreen_carplay/issues/187) accepts public corrections, missing projects and firmware/evidence reports. GitHub login is needed. Do not disclose private Telegram messages, credentials, vehicle IDs, firmware dumps or bypass details. Maintainers triage comments and link accepted fixes to documentation-only PRs. The separate full 58 × 22 reassessment is [Issue #184](https://github.com/harman-f/mhi2_altscreen_carplay/issues/184).

Site counts after this edit: **nine topical tabs**, **nine independently searchable/filterable research matrices**, five factory HUD source leads, three additional hardware HUD leads and nine remaining dongle/peripheral entries. The 58 frozen baseline rows and repository cards are unchanged. Publication is complete only once validation and the Pages deploy succeed on main.
