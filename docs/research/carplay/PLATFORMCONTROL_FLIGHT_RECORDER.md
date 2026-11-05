# PlatformControl / lifecycle flight recorder findings

> **Research status · 2026-11-05:** **CARPLAY RESEARCH REFERENCE.** Preserve original evidence boundaries; newer build behavior needs separate proof. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


This document explains why the current debugging focus moved from "does video work?" to
"what exactly happened to the existing secondary-screen session?"

## Target hook surface

The MU1440 stock AirPlay binary exports:

```text
AirPlayReceiverSessionPlatformControl
```

This is a high-value passive observation point for control-plane commands while leaving the stock
handler in place.

The project built a diagnostic flight recorder that:

- intercepts/logs the command;
- decodes the command as CFString rather than pretending it is a C string;
- records qualifier, params and outParams;
- recursively walks dictionaries/arrays with bounded depth/items;
- identifies integer value `111` as a likely stream descriptor marker;
- redacts likely secrets/tokens/nonces/auth material;
- forwards the stock call unchanged.

## Important early correction

An early logger treated the command parameter as a C string.

That was wrong.

The real ABI uses a CFString-style object. The mistake produced command-object bytes rather than
meaningful command names while still forwarding stock behavior.

This is documented because it is an easy trap for anyone building another interposer.

## Command vocabulary worth correlating

High-value control commands include:

- `setUpStreams`
- `tearDownStreams`
- `stopServer`
- `requestUI`
- `suggestUI`
- `showUI`
- `stopUI`
- `changeModes`
- `modesChanged`
- `forceKeyFrame`

Do not assume all of them are same-direction operations merely because they share a vocabulary.

## The observation that changed test priorities

Late-session PlatformControl activity continued while the private Type-111 stream itself remained
alive.

Combined with exact iOS 27.2 analysis, this moved the primary lifecycle target away from
"expect tearDownStreams(111) on every provider switch" and toward:

1. `suggestUI` candidate withdrawal/selection;
2. navigation ownership;
3. `modesChanged`;
4. `showUI` / `stopUI`;
5. actual Type-111 stream descriptors only when a topology change really occurs.

## High-value trace sequence

For one controlled provider transition, record timestamps for:

```text
navigation A active
 -> finish A
 -> idle
 -> start navigation B
 -> stop B
 -> restart B
```

Correlate:

- PlatformControl command + payload class;
- `suggestUI` URL set;
- stream 111 connection/generation;
- VideoConfig generation;
- IDR/non-IDR counters;
- consumer generation;
- delivered AU count;
- direct-ts-remux block count;
- STOCK/DIRECT gate state.

## Interpretation guide

### Same Type 111 + no fresh H.264

Look upward first:

- UI selection;
- ownership;
- source activation;
- sender bitstream restart.

### Same Type 111 + fresh H.264 + no usable consumer generation

Look at:

- new VideoConfig;
- config generation;
- SPS/PPS;
- IDR boundary;
- queue fencing.

### Fresh decoded/delivered video + frozen cluster

Only then move downstream again:

- remux;
- `isoTX2`;
- producer arbitration;
- presenter/cluster state.

### Actual tearDownStreams(111) + fresh SETUP

That is a real transport generation boundary. Rebuild/reset the stream cleanly.

## Public comparator hint

The public Yuedi AltScreen implementation contains an explicit control-command classifier around the
same AirPlay PlatformControl family. It is useful as a behavioral comparator, not as source
authority for MU1440.

See `.research/DEEP_CUTS.md` for the external project pointers.
