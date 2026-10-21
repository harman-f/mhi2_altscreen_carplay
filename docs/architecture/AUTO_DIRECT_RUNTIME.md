# Auto-Direct runtime architecture

The **published reference** vehicle-tested integration is not just a video binary. Newer experimental supervisor and central-controller development has separate owner/vehicle acceptance; see [architecture index](README.md) and [current status](../status/INTEGRATION_STATUS_2026-10-21.md). It is a small state machine that
decides when the alternate producer is allowed to own the Virtual Cockpit map-video path.

The exact research scripts are published under `runtime/auto-direct/`.

## Components

```text
libaltscreen111.so
  -> /tmp/mibr-carplay111.state
  -> /tmp/mibr-carplay111.heartbeat
  -> TCP Annex-B tee on configured port
                │
                ▼
direct_ts_auto_supervisor.sh
  waits for:
    - gate loaded
    - required navigation arbitration state
    - CarPlay stack healthy
    - stream111 state=streaming
    - validated source heartbeat
                │
                ▼
writev_gate.sh direct
                │
                ▼
direct-ts-remux tcp://127.0.0.1:<tee> -> /dev/mlb/isoTX2
                │
                ▼
post-connect source activity after forceKeyFrame
                │
                ▼
state=direct
```

A separate `direct_ts_auto_watchdog.sh` monitors the supervisor heartbeat. If DIRECT is active and
the supervisor heartbeat becomes stale for the bounded threshold, it removes the DIRECT marker so
stock DisplayManager writes resume.

## Important design choice

Video silence is **not** used as route-end detection after DIRECT has been established.

CarPlay may stop re-encoding an unchanged secondary screen while keeping the Type-111 stream valid.
The supervisor therefore uses a post-consumer-connect activity check to prove the source, then keeps
the session alive until an actual state transition, bridge failure or explicit disable occurs.

## Current prerequisites

The published reference scripts expect:

- `direct-ts-remux`;
- the DisplayManager `isoTX2` gate;
- the GEN2 source state/heartbeat files;
- a compatible navigation-arbitration setup;
- the MU1440 runtime commands used by the scripts.

The current reference implementation checks for `MIBR-NavIgnore.jar`. The current developer
release includes the exact vehicle-tested JAR in `payload/`; provenance, pinned upstream identity,
split logic and license are documented in [NAVIGNORE.md](NAVIGNORE.md) and
`THIRD_PARTY/NavIgnore/`.

## Persistence

The reference `direct_ts_auto_enable.sh` shows the exact tested guarded boot-hook design. It is
published for engineering transparency, not presented as a one-click installer.

The important fail-safe property is:

> No enable marker -> boot hook is inert.

Disabling Auto-Direct stops owned processes and requests STOCK; the guarded hook may remain present
without becoming active.

## Why this is public now

External contributors need this state machine to understand what "automatic start/stop" actually
means. Hiding it behind a future installer would make lifecycle debugging harder and would encourage
people to rebuild the same logic from incomplete symptoms.
