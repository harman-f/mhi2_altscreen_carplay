# Runtime switches

The current MU1440/AID10 Classic Type-111 runtime-control authority is:

**[CLASSIC_TYPE111_RUNTIME_CONTROL_CONTRACT_2026-10-04.md](CLASSIC_TYPE111_RUNTIME_CONTROL_CONTRACT_2026-10-04.md)**

That document supersedes the older marker-by-marker switch descriptions for the active vehicle-test
candidate.

## Core rule

```text
/tmp/<basename>                   temporary override
/mnt/app/root/<basename>          persistent override
compiled/configured default       fallback
```

Temporary always wins. The filename is identical in both layers.

## Active settings

| Basename | Default | Apply |
| --- | --- | --- |
| `mibr-carplay111-enabled` | 1 | CarPlay reconnect |
| `mibr-carplay-autodirect` | 1 | runtime |
| `mibr-carplay111-fps` | 30 | CarPlay reconnect |
| `mibr-carplay111-framing` | raw | bridge restart |
| `mibr-carplay111-video.conf` | pace=1, pace_buffer=3 | bridge restart |
| `mibr-carplay111-keyframes.conf` | 1 / 250 / 1000 / 1000 ms | live |
| `mibr-carplay111-sourceversion` | 1005.8.1 | CarPlay reconnect |
| `mibr-carplay111-url` | auto | presentation refresh |
| `mibr-carplay111-ui-urls.conf` | three classic cluster URLs | CarPlay reconnect |
| `mibr-carplay111-nav.conf` | classic base / query off | presentation refresh |
| `mibr-carplay111-display.conf` | 1010×376 / 200×74 mm | CarPlay reconnect |
| `mibr-carplay111-viewareas.conf` | two areas | definition reconnect / selection live |

The ViewArea configuration contains both ViewAreas, both nested SafeAreas, initial index, transition
time and adjacency. The current Area-1 SafeArea candidate is `x=0 y=58 w=1010 h=248`.

## Source timing / M1AU

The FPS setting controls advertised Type-111 maxFPS and direct output pacing. Independent telemetry
measures actual source AU arrival timing with CLOCK_MONOTONIC. M1AU v1 carries the exact eight raw
Stream-111 timestamp bytes. Those bytes do not drive PTS/PCR in the current candidate; PTS/PCR remain
CFR-derived.

## No longer active switches

Bit26, bit37, old URL-map/autoshow markers, split direct-output FPS, old D2 marker, old ViewArea
marker and old nav-query marker are not part of the current contract.

Media/Now Playing and Ultra/NextGen features are deliberately excluded from this vehicle candidate.

See the authority document for exact file formats, helpers, apply semantics, HMI integration and the
controlled vehicle baseline.
