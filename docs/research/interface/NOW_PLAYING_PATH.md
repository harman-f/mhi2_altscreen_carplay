# Now Playing: metadata path vs Stream-111 surface

> **Research status · 2026-11-05:** **HMI / INPUT RESEARCH REFERENCE.** APIs/build studies do not alone prove installed HMI behavior. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


Now Playing should not currently be treated as another proven Stream-111 video URL.

The exact MU1440 configuration already exposes an iAP2/PPS metadata path rooted at:

```text
/ramdisk/pps/iap2/nowplaying
```

with fields for title, album, artist, genre, duration, elapsed time, playback state, shuffle/repeat
state and playback application name. Exact-target iAP2 code also exposes artwork-related support.

This fits a separate working hypothesis:

> useful phone/CarPlay Now-Playing data may feed the vehicle's native cluster media presentation
> rather than requiring another H.264 auxiliary-screen surface.

The native Virtual Cockpit already has media presentation capability, and related OEM implementations
use cluster media/Now-Playing information independently of a navigation video surface.

Future work should correlate:

```text
iAP2 nowplaying PPS
        -> artwork / metadata retrieval
        -> native DSI/Kombi media update
        -> physical VC media page
```

before adding speculative `NowPlaying://` or bundle identifiers to the AltScreen URL selector.
