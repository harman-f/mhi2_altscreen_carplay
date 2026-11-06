# Public capability delta / P1-P5 (2026-11-04)

**Research status · SOURCE-STAGED / ABI AND VEHICLE EFFECT OPEN**


This is an implementation-difference audit, **not** a claim of physical VC
acceptance. It separates existing original development from source references.

| Priority | Already implemented in harman-f/develop | Public source delta | Action |
| --- | --- | --- | --- |
| P1 Media/Now Playing | No complete published MHI2 native cover + BAP media path | omonob v2.1.0-rc.7: read-only iAP2 transfer ID/file pull, bounded artwork image, session/track signature, ASL coalescing, music switch, `VCInformation.jar` (experimental); xPaiiN: native title/artist/album/progress/shuffle (MST2); kamgurgul: picture-provider mux avoiding disruption of BT/radio (MHI2Q) | New `media` state core and selected non-active GPL source extracts; exact 3-profile adapter still pending |
| P2 Phone/calls | OEM music/video/menu work present; CarPlay phone BAP action integration not published | chefranov Audi AU37x phone tab (P5089 MU1326); ProManiFest Audi K3346 gate/PPS/parser; kamgurgul Audi MHI2Q phone/steering wheel | New `phone` fail-closed state core and selected non-active K3346 sources; all 3 profile adapters pending |
| P3 Navigation/HUD | `modules/navigation/source`: compiled-source definition for `libmibr_rgi_ipod.so` + `mibr-rgi`, existing NavSD arrows, composition, 1010×376, own Java HMI controls; source build depends on exact MU1440 `libiap2client.so.1` SHA `c33021b21c5656886e64964efcf806fddb4259027c3c1ed396522e7a44adfdea` | omonob v2.1 experimental: route replay/duplicate guard, lane association, BAP/ASL dispatch, ETA-timezone logic, clear-on-disable; HUD is not automatically implied by an AID10 native-arrow path | **No new P3 module or second iAP2/Navi hook.** Compare behavior/fixtures with existing Navigation; HUD output requires actual fitted cluster/HUD BAP capability and exact classes |
| P4 Android Auto | Separate projection topic, no changes requested here | kamgurgul MHI2Q and kkrvch MST2 different GAL backends | Out of scope |
| P5 Vehicle Data | `modules/carplay/source/vehicle-data/`: `mvs_core`, `mibr_vdata` + hook, `mibr_vstatus`. Speed via same original GPS worker; vehicle status 0xA100/0xA101 for genuine range, outside temperature and reserve warning, guarded by phone subscription; modes off/shadow/send | kamgurgul supports similar speed/range/temperature/status in MHI2Q, but no missing *feature category* found that merits a new module | **No duplicate P5 module.** Review exact unit DSI source and iPhone feature negotiation. Not vehicle-qualified; off by default |

## Why P3 should not be imported again

Own navigation code is already present, with a source-built TLV decoder and
the exact MU1440 firmware-library fingerprint; the selected omonob information
classes mix route, media, ASL and HMI side effects. Replacing current
`mm-ipod` with their wrapper would conflict with our existing iAP2 hooks.
Only isolate missing behavior after targeted diff of event handling,
out-of-order/duplicate suppression, session teardown, time zones and native
HMI BAP entrypoints. In particular, no general HUD capability should be
asserted from Audi research or from a video plane alone.

## Why P5 is not '100% finished'

Our source tests support bounded samples, stale suppression, same-owner
send and subscription policy. The public status explicitly says that the
target vehicle's DSI units, iAP2 request/acceptance and enabled install path
have **not** been accepted end-to-end. The implementation should remain off
until real vehicle state and phone-side acceptance can be measured.

## Risk and ownership

There is **one authenticated CarPlay owner** and **one native MIBR broker**.
The new modules provide no alternate renderer, media transport, independent
phone session, direct OEM Java replacement, or another `mm-ipod`/DIO wrapper.
Never register a CarPlay picture provider in a way that hides the stock radio
or Bluetooth provider. Use exact original LSD JXE hashes to select adapters.
No OEM binaries, installed compiled JARs or firmware-derived Java classes were
imported into this branch; the copied individual GPL classes are documented.
