# MU1440 Classic Type-111 vehicle test — 2026-10-05

## Candidate identity

Use only this audited vehicle ZIP:

```text
MHI2_AltScreen_MU1440_FRAMING_V1_CANDIDATE.zip
SHA256 2a09a8c2c03045f36db6e5e71fc9f03c3c6728fc764623190c35c1ed2b95de21
```

It was produced from:

```text
repo   harman-f/mhi2_altscreen_carplay
branch work/source-timestamp-framing-v1
source HEAD bbfa20cb11c574d14b3cb607731ea20ccfb9fef8
Actions run 37183996909
artifact ID 11296122415
```

Binary hashes:

```text
libaltscreen111.so
8cccf1cb1764952acd973cbb4f881cfd70f3312e7f6a29cdef7fec930c83d25c

direct-ts-remux
3f0e730523bd290608dc13e186baa962eeb9c46f117d4d4976be523c0cd94c09
```

## Safety boundaries

Exact target only:

```text
MHI2_ER_SKG13_P4526_MU1440
AID10-class Virtual Cockpit
```

The installer checks the expected MU1440 `libairplay.so` hash before mutation. If `--check`
does not return PASS, do not apply.

Do not hard-restart `smartphone_integrator` or `dio_manager` to apply a reconnect-class setting.
Disconnect/reconnect CarPlay. If the projection stack becomes stale, use a normal MHI reboot and, if
required, a complete vehicle bus-sleep boundary.

The candidate is vehicle-test ready, not merge/production ready.

## SD layout and install

Extract the complete vehicle ZIP to one folder on the SD card. The folder root must contain:

```text
install.sh
uninstall.sh
status.sh
CANDIDATE-MANIFEST.txt
PAYLOAD.sha256
PACKAGE-SHA256SUMS.txt
payload/
runtime/
```

SSH to the unit and `cd` into that folder.

Preflight:

```sh
ksh ./install.sh --check
```

Expected:

```text
MIBR_CLASSIC111_CHECK=PASS
next=./install.sh --apply
```

Apply:

```sh
ksh ./install.sh --apply
```

Expected final lines include:

```text
MIBR_CLASSIC111=PASS
config_precedence=/tmp_then_/mnt/app/root_then_default
source_fps_default=30
framing_default=raw
source_version_default=1005.8.1
viewareas_default=2
d2_default=enabled:1,event_delay:250,min_gap:1000,watchdog:1000
source_timing=clock_monotonic
pts_pcr=UNCHANGED_CFR
REBOOT_REQUIRED=YES
```

Then:

```sh
reboot
```

After the unit is back, preferably before connecting the iPhone:

```sh
ksh ./status.sh
```

Save that complete output.

## Baseline — first CarPlay connection

Do not create any temporary overrides before the first run.

Expected effective defaults:

```text
AltScreen master  = 1
Auto-Direct       = 1
FPS               = 30
framing           = raw
video pace        = 1
pace_buffer       = 3
sourceVersion     = 1005.8.1
raw URL           = auto
nav               = query=0, surface=base
ViewAreas         = 2, initial=0
ViewArea 0 Safe   = 0,0,1010,376
ViewArea 1 Safe   = 0,58,1010,248
D2                = enabled, 250/1000/1000 ms
PTS/PCR           = CFR unchanged
```

Connect CarPlay and reproduce the known navigation scenario first. Capture:

```sh
ksh ./status.sh
cat /tmp/mibr-alt111-gen2.status
cat /tmp/mibr-alt111-source-timing.status
cat /tmp/mibr-direct-remux.status
```

Relevant timing evidence includes measured source arrival FPS/intervals, source/remux/MOST bitrate,
pacing/jitter and backpressure.

## Test A — live ViewArea switching

The two areas were negotiated at session start, so changing the active index is live:

```sh
/mnt/app/root/altscreen-u2/scripts/gen2_viewareas.sh select 1
```

Expected target: `GAUGE_REDUCED`.

Return:

```sh
/mnt/app/root/altscreen-u2/scripts/gen2_viewareas.sh select 0
```

Expected target: `MAP_FULL`.

After each switch:

```sh
cat /tmp/mibr-alt111-gen2.status
tail -n 100 /tmp/altscreen111.log
```

Do not edit the geometry during this first switch test.

## Test B — M1AU source metadata

Temporary framing override:

```sh
/mnt/app/root/altscreen-u2/scripts/direct_source_mode.sh m1au
```

This restarts only the local bridge. PTS/PCR remains CFR.

Reproduce the same navigation scenario and collect:

```sh
ksh ./status.sh
cat /tmp/mibr-alt111-source-timing.status
cat /tmp/mibr-direct-remux.status
```

Verify that M1AU sequence and raw source timestamp telemetry advances. The eight timestamp bytes are
evidence only and must not be interpreted as the presentation clock yet.

Back to baseline:

```sh
/mnt/app/root/altscreen-u2/scripts/direct_source_mode.sh raw
```

## Test C — FPS, only after A/B baseline evidence

A bare FPS command is a temporary override:

```sh
/mnt/app/root/altscreen-u2/scripts/direct_fps.sh 25
```

or:

```sh
/mnt/app/root/altscreen-u2/scripts/direct_fps.sh 20
```

Because this changes the Type-111 advertised `maxFPS`, disconnect/reconnect CarPlay before judging it.

Clear the test override:

```sh
/mnt/app/root/altscreen-u2/scripts/direct_fps.sh clear-temp
```

After clearing, reconnect again. The effective value returns to persistent/default 30.

Do not test multiple FPS values and M1AU/D2 changes in the same run.

## Presentation settings

Navigation config and raw URL are presentation-class changes. They can be applied through a bounded
same-session:

```text
stopUI -> showUI(new URL) -> forceKeyFrame
```

Example:

```sh
/mnt/app/root/altscreen-u2/scripts/gen2_nav_config.sh use-temp map-clean
```

Return:

```sh
/mnt/app/root/altscreen-u2/scripts/gen2_nav_config.sh clear-temp
/mnt/app/root/altscreen-u2/scripts/gen2_nav_config.sh apply
```

Raw exact URL test:

```sh
/mnt/app/root/altscreen-u2/scripts/gen2_url.sh temp 'maps:/car/instrumentcluster/map'
/mnt/app/root/altscreen-u2/scripts/gen2_url.sh apply
```

Clear:

```sh
/mnt/app/root/altscreen-u2/scripts/gen2_url.sh clear-temp
/mnt/app/root/altscreen-u2/scripts/gen2_url.sh apply
```

## ViewArea definition edits

Changing geometry, nested SafeAreas, count, initial index or advertised URL/display metadata is a
reconnect-class change.

Examples:

```sh
/mnt/app/root/altscreen-u2/scripts/gen2_viewareas.sh temp-set view1.safe.y 70
/mnt/app/root/altscreen-u2/scripts/gen2_viewareas.sh temp-set view1.safe.h 236
```

Then disconnect/reconnect CarPlay.

To discard all temporary ViewArea-definition tests:

```sh
/mnt/app/root/altscreen-u2/scripts/gen2_viewareas.sh clear-temp
```

Reconnect again.

A reboot also clears every `/tmp` setting and returns to the persistent/default layer.

## Rollback

From the extracted candidate folder:

```sh
ksh ./uninstall.sh
reboot
```

Expected before reboot:

```text
MIBR_CLASSIC111_UNINSTALL=PASS
REBOOT_REQUIRED=YES
```

Rollback restores exactly the pre-install state captured under:

```text
/mnt/app/root/mibr-framing-v1-backup
```

The audited installer and uninstaller cover the same 41 saved/restored entries.

## First-run evidence priority

1. baseline 30 fps / raw / ViewArea 0;
2. live 0 ↔ 1 ViewArea switching;
3. same scenario with M1AU only;
4. source arrival timing + raw M1AU timestamp evidence;
5. only then 25/20 fps or D2 timing A/B;
6. geometry calibration after the two-area control path itself is proven.

Do not merge PR #10 or promote this candidate before vehicle validation.
