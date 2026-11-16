# MIB1 High (MHIG): CarPlay / Android Auto retrofit research

**Source review:** 2026-11-16. **Public release status:** UNVERIFIED; forum prototype only. **Source cutoff:** Telegram HTML export supplied by the user, through 2026-11-15. No raw export, direct private Telegram URLs, user IDs, VINs, firmware dumps or sensitive technical payloads are distributed in this public research note.

## Findings directly from the supplied community messages

| Date (2026) | Telegram display author and message | Evidence level | Context |
| --- | --- | --- | --- |
| Nov 13 | **korho**, `#18572` | Author report | “app-connect (aa/cp) on mhig”; author asserts local implementation, exact hardware and firmware not provided in message |
| Nov 13 | **Priit V**, `#18578` | Third-party attribution | Credits the MHIG experiment to korho |
| Nov 13 | **korho**, `#18581` | Author announcement | Responding to whether the MHIG or wireless work will be public: “Both: yes”; not a public package or release date |
| Nov 13 | **korho**, `#18597`, `#18598` | Author report / future claim | Says MHIG hardware can handle App-Connect and that it can also run wireless |
| Nov 13 | **korho**, `#18599` | Author explanation | Explicit hardware-accelerated video decoding **over USB**; only a few hours of testing and development-tool/SD-card setup |
| Nov 14 | **korho**, `#18613`, `#18615`, `#18616` | Author inference / implementation notes | MHI2 firmware port is distinct from MHIG due to CPU instructions; USB native-host interception and H.264 acceleration matter |
| Nov 14 | **mr-fix**, `#18612` | Question only | Asks whether **MSTD** can run CarPlay. Not evidence of implemented MIB1 Standard support |
| Nov 14 | **Marshall Eriksen**, `#18621` | Opinion | Notes possible MHIG CPU-performance limits in Audi; not a validated negative compatibility matrix |

## Technical classification

- **Head-unit:** VAG/Audi/VW **MIB1 High (`MHIG_`)**. In the chat no independently confirmed exact MU/train, Audi/VW model, hardware revision, iPhone/iOS pair, USB controller driver hash or car test/installation report was given. Do not copy `MHI2` or `MST2` compatibility into MHIG.
- **Apple CarPlay**: original HU screen via USB, *claimed working by author*. Not necessarily native to all MHIG and not proven on the original Virtual Cockpit or a separate Type111 stream.
- **Android Auto**: also claimed by author as App-Connect, but no independent car acceptance log.
- **Wireless**: author says “it'll do wireless too”; no BT/iAP2, Wi-Fi, AirPlay production proof, public firmware or exact supported train established. This status is *announced*, not a released wireless receiver.
- **H.264:** hardware accelerated USB decode is specifically reported; not an independently validated performance benchmark.
- **AltScreen / VC / HUD:** unknown / unverified, and possibly not applicable for early MIB1 configurations without Virtual Cockpit. Do not claim an implemented second screen.

## Repository cross-check

- No standalone public `korhojoa` MHIG CarPlay retrofit repository was identified in the 2026-11-16 GitHub owner/repository searches. Treat this as **public-source pending**, not as a private source with a known name.
- [`korhojoa/mib2-extenders`](https://github.com/korhojoa/mib2-extenders) is an **MHI2-era Wireless Android Auto** project for a firmware-specific unit; **it does not independently prove the MHIG port**.
- [`Mr-MIBonk/M.I.B._More-Incredible-Bash/apps/carp`](https://github.com/Mr-MIBonk/M.I.B._More-Incredible-Bash/blob/main/apps/carp) explicitly stops CarPlay/AA activation on MHIG. That older switch-based feature activation is not the same as adding a receiver/hardware decoder on MIB1 High.
- [Public GitHub discussion on MHIG K1550](https://github.com/Mr-MIBonk/M.I.B._More-Incredible-Bash/discussions/987) is **an unanswered compatibility question**, not positive evidence for K1550 support.

## Source and validation requirements before changing status

Request exact train (e.g. `MHIG_*`), HU model/part number, firmware/SoC and original OS identity, MFi/USB/iAP2 implementation approach, whether car or bench test, stable reconnection and logs, release/rollback files, and explicit indication of whether any cluster rendering exists. Require a public source/release before adding a scored repository row to the 58×22 matrix; currently publish only a **MIB1 technology lead** in the regular CarPlay/Android Auto tab. MIB1 Standard `MSTD` remains a separate, unverified question.

**Classification at this snapshot:** `Community-reported / public source not found / vehicle proof unverified / exact train unknown`.
