# Public source lineage and feature-watch policy (05 Nov 2026)

**Research status · COMPARATOR REGISTER / SOURCE-STAGED ONLY**


This is a **project-targeted reference register**, not a copy-all script.
The freshest GitHub push is not necessarily the most complete or safe
implementation for Škoda MU1440 / SEAT MU1409 / MU1447.

| Public owner | Feature | Source/lineage finding | Current reuse class |
| --- | --- | --- | --- |
| [LuKa](https://github.com/luka-dev/mib2q-carplay-rgi) | P6 MHI2Q surround, Spatial Audio, BAP Phone, Vehicle | Original upstream; 29 Oct latest published release; external Audi B&O/Bose and Qualcomm MHI2Q | Architecture and GPL sources; no direct target binary |
| [yety-ua](https://github.com/yety-ua/mhi2-k3346-carplay-audio-upmix) | P6 Tegra3 NVIDIA audio port | GitHub fork of ProManiFest2122; explicitly integrates LuKa concepts. No enabled on-car audio | Best native-ABI research bridge; source only |
| [ProManiFest2122](https://github.com/ProManiFest2122/mhi2-k3346-carplay-vc) | P2 Audi G22 phone and UI | Independent port/collaboration including attributed LuKa work | Audi-specific method source only |
| [kamgurgul](https://github.com/kamgurgul/mib2q-carplay) | P1 cover, P2 phone, P3 RGI, P5 vehicle, AA | Not marked GitHub fork; `VehicleDataModule` credits LuKa | Favor tested lifecycle/edge cases, no Qualcomm target binary |
| [omonob](https://github.com/omonob/MHI2-Carplay-Maps) | P1 MHI2 native information, P3 lane/ETA | v2.1 RC adapts author's historical V53 branch; independent per-profile firmware builds, host tests/partial emulator | P1 MU1440 information source reference |
| [xPaiiN](https://github.com/xPaiiN/mst2-carplay-vc) | P1 media/cover/picture server | Independent MST2 bridge; public OSS, platform-specific | UI and edge-case comparison |
| [chefranov](https://github.com/chefranov/mhi2-au37x-carplay) | P2 MHI2 AU37x calls | Audi-specific, vehicle-backed in named firmware | Feature acceptance benchmark |

## How to compare future revisions

1. Record exact upstream **commit** and release date, not star count or only
   newest tag; follow credit/provenance and GitHub fork parent where available.
2. Compare at the **function/file** level: incoming events, lifecycle, thread
   affinity, output API, newest pending bugs, regression tests, and whether
   exact target code is built.
3. Map each to one canonical MIBR module and three profile/ABI gates. Distinguish
   *feature exists*, *host check*, *QNX emulator*, *on-unit*, and *on-car end-to-end*.
4. Track novel features and meaningful fixes separately from code copies and
   wholesale firmware overlays. License-check each proposed source adoption.
5. Do not auto-merge research, OEM binaries, JXE class bodies, owner-specific
   calibration or installed driver images into `develop` or `main`.
6. Require explicit recovery/rollback and objective installation conditions
   before any on-car P6 experiment.

A weekly external Upstream Watch can deliver significant changed facts; this
source register is the persistent starting set. No recurring CI job is
activated by these docs.
