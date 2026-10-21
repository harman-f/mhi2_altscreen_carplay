# Vehicle test protocol

This is the common test protocol for contributors with SSH access to a compatible MHI2 unit.

It is intentionally component-oriented rather than an installer walkthrough.

## 0. Safety / privacy

Before testing:

- vehicle stationary;
- known recovery route;
- exact firmware/component hashes recorded;
- no VIN, home/work address or credentials in public logs;
- stock behavior confirmed before modification.

Do not test while driving.

## 1. Identify the target

Record at minimum:

```text
brand/model:
model year:
firmware train:
MU:
cluster/AID:
SSH path: WLAN | USB-LAN | other
```

For the current reference target verify:

```text
MHI2_ER_SKG13_P4526_MU1440

/mnt/app/eso/lib/libairplay.so
193a4fd9101ec2aa05e7159cfa307b96500810d379ca74a194f172adc13a46b5
```

If the hash differs, stop treating the current native hook as compatible.

See `docs/research/MU1440_STOCK_REFERENCE.md`.

## 2. Capture a stock baseline

Before DIRECT:

- confirm normal CarPlay;
- confirm native VC map;
- record relevant process list;
- record current stock hashes;
- record whether `/dev/mlb/isoTX2` exists;
- record DisplayManager ownership/state.

A useful result always has a known STOCK baseline.

## 3. Test the downstream VC transport independently

The cleanest isolation order is:

```text
MOST writer
   ↓
direct-ts-remux with known H.264
   ↓
live CarPlay Type 111
```

### 3.1 MOST contract

Use the project `most-ts-writer` source/build to confirm the target accepts the proven application
write contract:

```text
64 × 188 = 12032 bytes
```

Do not debug CarPlay and MOST at the same time if the lower layer has never been confirmed.

### 3.2 H.264 -> MPEG-TS

Use the canonical `direct-ts-remux` developer artifact or a CI rebuild.

Confirm:

- valid Annex-B input;
- MPEG-TS output;
- strict complete block writes;
- no positive short writes;
- bounded test duration first.

### 3.3 STOCK/DIRECT arbitration

Verify the gate in both directions:

```text
STOCK
 -> native map visible
 -> native DisplayManager writev bytes pass

DIRECT
 -> stock process stays alive
 -> tracked stock isoTX2 payload is swallowed
 -> alternate producer can own the transport

STOCK again
 -> native bytes resume
 -> native map returns
```

The recovery half is part of the test.

## 4. Verify the Type-111 source separately

Before automatic takeover, check:

- GEN2 hook loaded;
- stock main CarPlay screen still works;
- SETUP returns the actual Type-111 data port (normally TCP 6031);
- the already configured, effective inbound `carplay0` PF rule allows that port
  (read-only inspection, e.g. the unit's `pfctl -sr`; check again after reboot);
- Type-111 listener exists and an **actual iPhone TCP connection** is accepted
  (a listener or SETUP alone does not establish firewall reachability);
- source state reaches `streaming`;
- VideoConfig has been accepted;
- H.264 AU counters advance;
- local tee is loopback-only;
- new consumer can obtain a usable config/IDR boundary.

Useful helper:

```sh
ksh runtime/diagnostics/gen2_status.sh
```

or copy the helper scripts to a generic target-side staging directory.

## 5. Automatic DIRECT test

Reference sequence:

```text
native map / STOCK
       ↓
CarPlay navigation starts
       ↓
Type 111 becomes usable
       ↓
supervisor sees valid source
       ↓
gate -> DIRECT
       ↓
direct-ts-remux attaches
       ↓
fresh post-connect source activity
       ↓
live VC video
```

Observe:

- supervisor state;
- watchdog heartbeat;
- bridge PID;
- source heartbeat;
- gate stats;
- DisplayManager PID before/after;
- MOST block count.

Expected property:

> DisplayManager remains alive throughout the normal takeover.

## 6. Navigation lifecycle matrix

Use the same controlled sequence for each provider pair:

```text
A: start navigation
 -> wait 10 s
 -> finish navigation
 -> wait 10–15 s
B: start navigation
 -> wait 10–15 s
 -> finish navigation
 -> wait
 -> restart B once
```

Test combinations where available:

- Apple Maps -> Apple Maps
- Apple Maps -> Google Maps
- Apple Maps -> Waze
- Google Maps -> Apple Maps
- Waze -> Apple Maps

Do not interpret one provider's failure as a transport failure until the lifecycle counters are
classified.

## 7. Frozen-last-frame classification

If the last VC frame freezes, collect evidence **before reconnecting**.

Classify in this order:

```text
same Type-111 generation?
  |
  +-- no -> inspect actual teardown/setup
  |
  +-- yes
       |
       +-- fresh H.264 absent
       |     -> UI/ownership/source activation
       |
       +-- fresh H.264 present
             |
             +-- no usable config/IDR generation
             |     -> resync/consumer priming
             |
             +-- delivered video advances
                   -> downstream remux/gate/presenter
```

Useful helpers:

```sh
ksh runtime/diagnostics/gen2_status.sh
ksh runtime/diagnostics/gen2_collect_logs.sh
ksh runtime/diagnostics/gen2_resync.sh status
```

For a bounded manual same-session experiment:

```sh
ksh runtime/diagnostics/gen2_resync.sh on
ksh runtime/diagnostics/gen2_resync.sh arm
```

Record the before/after status rather than reporting only "worked" or "didn't work".

## 8. Reacquire / reconnect hierarchy

Prefer the least destructive recovery first:

```text
observe
 -> bounded same-session resync
 -> explicit reacquire
 -> CarPlay cable reconnect
 -> only then consider head-unit restart
```

A cable reconnect is useful recovery evidence but does not prove which same-session state was wrong.

## 9. ViewArea test

ViewArea work is separate from basic video proof.

When testing layouts:

- choose one visible VC layout;
- record all available stock layout/state signals;
- record current advertised ViewArea/SafeArea;
- change exactly one cluster view;
- wait long enough for state propagation;
- repeat.

Do not publish location-bearing screenshots. If visual geometry evidence is essential, sanitize/crop
it so no street/address/navigation-history data remains.

## 10. Collect evidence

Recommended public report contents:

```text
target firmware/MU
cluster type
stock component hashes
project commit
artifact SHA-256
provider/test sequence
GEN2 status
PlatformControl/lifecycle excerpt
source/config/IDR counters
Auto-Direct state
gate stats
remux summary
STOCK recovery result
```

The helper:

```text
runtime/diagnostics/gen2_collect_logs.sh
```

writes a target-side report without requiring an SD-card layout.

Review/redact it before posting.

## 11. Pass/fail vocabulary

Use precise language:

- **PASS** — the specific tested condition was directly observed.
- **PARTIAL** — useful behavior occurred but a required transition/recovery is inconsistent.
- **FAIL** — the tested condition reproducibly did not occur.
- **NOT TESTED** — no evidence yet.
- **HYPOTHESIS** — interpretation not yet proven.

Do not turn one successful transition into a claim of full provider compatibility.

## 12. Final recovery

End every vehicle session by verifying:

```text
custom producer stopped
DIRECT marker absent
gate reports STOCK
stock DisplayManager alive
native map visible
normal CarPlay works
```

If those conditions are not restored, the experiment is not complete.
