# MU1440 Stream-111 source timing telemetry

Status: development candidate, not yet vehicle validated.

## Purpose

This instrumentation measures the real Stream-111 source cadence and the downstream Direct-VC/MOST
transport without changing the established media contract.

The baseline remains:

```text
CarPlay maxFPS advertisement: 30
Direct output target:          30
SafeArea/ViewArea:             existing independent GEN2 configuration
```

A 40-fps mode is available only as an explicit diagnostic test. It is not a new default.

## What is measured

GEN2 records timing at the accepted complete-AU boundary immediately after Stream-111 decryption and
validation. It measures:

- accepted source frames and H.264 bytes;
- monotonic inter-arrival intervals;
- measured source arrival FPS;
- source H.264 bit rate;
- both raw 32-bit timestamp words from Stream-111 header offsets 0x08 and 0x0c.

The two Apple timestamp words remain deliberately uninterpreted. This candidate does **not** assume
that they are milliseconds, microseconds, NTP, 90-kHz PTS or any other timebase.

Auto-Direct combines this source snapshot with the already existing direct-remux/MOST counters:

- remux input bit rate;
- MOST/TS bit rate;
- remux input interval;
- pacer underflow/late/backpressure counters;
- isoTX write EAGAIN/timeouts/errors;
- block wait times;
- maximum emit jitter.

## Configuration

`runtime/auto-direct/altscreen111.conf` keeps 30 fps as the default:

```text
ALTSCREEN111_FPS=30
DIRECT_OUTPUT_FPS=30
ALTSCREEN111_TIMING_DEBUG=1
ALTSCREEN111_TIMING_INTERVAL_MS=1000
DIRECT_TELEMETRY=1
```

Allowed diagnostic source/output targets are 20, 25, 30 and 40 fps.

Use the runtime helper:

```sh
/mnt/app/root/altscreen-u2/scripts/direct_fps.sh status
/mnt/app/root/altscreen-u2/scripts/direct_fps.sh 30
/mnt/app/root/altscreen-u2/scripts/direct_fps.sh 40
/mnt/app/root/altscreen-u2/scripts/direct_fps.sh default
```

A source maxFPS change applies to a new CarPlay negotiation. Reconnect CarPlay before comparing a
changed source rate. Do not interpret an immediate bridge restart as source renegotiation.

SafeArea is intentionally separate:

```text
/mnt/app/root/mibr-carplay111-safearea.conf
```

and remains controlled through the existing GEN2 SafeArea/ViewArea development path.

## Runtime status

Source timing:

```text
/tmp/mibr-alt111-source-timing.status
```

Typical fields:

```text
configured_max_fps=30
frames_total=...
bytes_total=...
source_arrival_fps_x100=...
source_input_bps=...
source_arrival_last_us=...
source_arrival_min_us=...
source_arrival_max_us=...
source_ts_word1=0x........
source_ts_word2=0x........
```

The measured FPS is based on N-1 arrival intervals for N frames. It is therefore not the historical
configured-FPS estimate.

Existing remux/MOST status remains:

```text
/tmp/mibr-direct-remux.status
```

`direct_ts_auto_status.sh` displays both sets together.

## Persistent per-session evidence

When the deployment medium is available, each Auto-Direct session receives:

```text
<deployment-media>/mhi2-altscreen-logs/direct-ts/<timestamp>-auto-direct-<session>/
    bridge.log
    SUMMARY.txt
    telemetry.tsv
    telemetry-events.log
    source-timing-final.status
    remux-final.status
```

If persistent media is unavailable, the existing runtime falls back to `/tmp/mibr-altscreen-logs`.

`telemetry.tsv` contains one row per supervisor interval and correlates:

```text
source maxFPS
measured source FPS
source H.264 bit rate
source arrival interval
raw source timestamp words
remux input bit rate
MOST/TS bit rate
pacer/backpressure counters
isoTX block-wait metrics
emit jitter
```

`telemetry-events.log` records a new 15/20/25/30/40 source-FPS bucket only after two consecutive
samples agree. A single jitter spike therefore does not become an FPS-change event.

## First vehicle comparison

Use the same navigation route/provider where possible.

1. Run the existing 30/30 baseline and retain the session directory.
2. Inspect source arrival FPS, H.264 bit rate, MOST bit rate, write/backpressure metrics and jitter.
3. Set 40 with `direct_fps.sh 40`.
4. Reconnect CarPlay so the new maxFPS can be negotiated.
5. Repeat the same route/provider.
6. Compare the two `telemetry.tsv` files and event logs.
7. Return to `direct_fps.sh default` or 30 after the experiment.

The useful questions are:

- Does iOS actually emit approximately 25-ms frame intervals when maxFPS=40?
- Does the source remain at 30 or dynamically fall to 20/15 on static/complex scenes?
- Does H.264 source bit rate materially increase?
- Does MOST/TS throughput remain stable?
- Do `write_eagain`, block wait, late frames or jitter increase at 40?
- Does visible VC motion improve, stay equal or regress?

## Deliberate non-goals of this candidate

This instrumentation does **not** yet:

- change PTS/PCR generation to Apple source timestamps;
- replace the Annex-B local tee with the Omonob CPRG ring;
- copy Omonob's periodic forceKeyFrame policy;
- infer the unit of the two raw Apple timestamp words;
- change the stable SafeArea defaults;
- make 40 fps a release default.

Those decisions remain gated by vehicle telemetry and the Free-790 / Free-791 / Paid-pre-v51
producer diff.
