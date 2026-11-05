# MU1440 developer deployment

This directory is intentionally **not a consumer/one-click SD-card release**.

It provides a compact developer deployment path for the exact vehicle-proven reference target:

```text
MHI2_ER_SKG13_P4526_MU1440
```

The release-readiness CI workflow builds only a legacy SD-root ZIP
(`..._LEGACY_CI_ONLY.zip`) for compatibility checks; it is never uploaded, so
no ZIP can be downloaded from CI. The local staging path is
`tools/prepare_mu1440_sd.sh`.

Prerequisite: working SSH/developer access and the ability to recover the unit. The documentation does
not explain how to obtain shell access.

## Prepare the SD-card root on a workstation

From a repository checkout:

```sh
tools/prepare_mu1440_sd.sh /path/to/mounted-sd-root
```

This writes the deployment directly into the SD-card root:

```text
<SD root>/
  install.sh
  uninstall.sh
  status.sh
  compatibility-report.sh
  PAYLOAD.sha256
  payload/
  runtime/
```

There is deliberately no `esd/` or `MHI2AltScreen/` wrapper directory.

The prepared payload uses the exact 2026-09-27 vehicle-tested GEN2 and direct-ts-remux binaries plus
the byte-reproduced **vehicle-tested** isoTX2 gate.

The prepared package includes the exact vehicle-tested NavIgnore payload:

```text
payload/MIBR-NavIgnore.jar
```

Expected SHA-256:

```text
b065bab0e1c58f8439a3bdd73d2d4cb6060cbac1c943e5b425425eb453c94b34
```

Its upstream/provenance record and license are documented in `THIRD_PARTY/NavIgnore/`.

The prepared package also includes the vehicle-validated standalone Most20 payload:

```text
payload/MIBR-Most20FPS.jar
```

Expected SHA-256:

```text
dbd45609fe4ba69948d39e9e649b224484f680f6aa7934b68c261a4d360ea5bb
```

Most20 is now part of the MU1440 reference default. Vehicle capture proved real
1010x376 H.264 output changing from 10 fps to 20 fps. Provenance is recorded under
`THIRD_PARTY/Most20FPS/`.

The default install also enables the persistent GEN2 D2 keyframe policy:
1 s source-IDR watchdog, 1 s minimum request gap, with event-triggered
`turns`/`suggestUI` requests still debounced at 250 ms. Disable it with
`/mnt/app/root/altscreen-u2/scripts/gen2_keyframes.sh off`.

No external Java payload is required for the validated MU1440/AID10 test path.

## Default configuration of this MU1440 developer installer

For a complete, source-traceable inventory, see the [configuration matrix](../../docs/configuration/DEFAULT_CONFIGURATION_MATRIX.md). Its 48 CarPlay registry entries are **per CarPlay preset**, not per firmware; the 13 broker switches have compiled fallbacks that may be overridden by a platform-default file or an existing stored value. The checked-in standard menu is branded `skoda` and describes layout only.

| Item | Current MU1440 developer reference | Important qualification |
| --- | --- | --- |
| Stream 111 CarPlay setting | `carplay.enabled=1` (registry default) | Effective active state can differ on the unit |
| Phone navigation arrows | `carplay_nav=off` (broker default) | Independent of CarPlay video enablement |
| Arrow source / placement | `auto` / `side` (broker defaults) | Preconfigured even while phone arrows are disabled |
| Navigation composition | `map-rich` | Explicit choice in `deployment/mu1440/install.sh` |
| DisplayManager gate | `STOCK` | Fail-safe until intentionally switched |
| Most20 / NavIgnore | Exact reference JARs included and installed as required | Specific to this older MU1440 development path |
| Auto-Direct | Persistent configuration prepared | Actual session operation must be verified after reboot |
| D2 keyframe recovery | Persistent; watchdog 1,000 ms, minimum gap 1,000 ms | Current install script; the beta-wide decision remains separate |

These are **source-defined / installer-set reference values**, not a measurement of installed effective state. No finished three-firmware beta ZIP is claimed by this README.

## Compatibility helpers

The prepared directory includes project-owned, reproducibly built QNX ARMv7 helpers rather than depending on a pre-existing M.I.B. `apps/sbin` tree:

```text
payload/sha256sum
payload/tee
```

The historical M.I.B. `sed` dependency is intentionally avoided in this deployment; the one required trim operation is implemented with stock `awk`.

The installer uses the bundled helpers by default. An experienced developer may override `sha256sum` with `MIBR_SHA256`, but
only after independently verifying the replacement binary.

## Read-only compatibility report

For an unknown Audi / VW / SEAT / Škoda MHI2 target, **do not start with the installer**. Run:

```sh
./compatibility-report.sh
```

This is intentionally read-only with respect to the vehicle filesystems. It only remounts the
deployment SD/USB medium writable so it can create a report directory. It does not install hooks,
patch Java, remount `/mnt/app` or `/mnt/system` writable, or require the MU1440 hashes to match.

The report contains the normal `vehicle-summary.txt` plus:

```text
compatibility/
  component-hashes.txt
  runtime-observation.txt
  README.txt
  stock-configs/
    displaymanager.json
    dio_manager.json
    smartphone_integrator.json
```

This is the standardized equivalent of the stock-config bundle that was useful for the first Audi
MU1438 comparison. Raw stock configs should still be reviewed before posting publicly.

## On the unit

Run from the prepared directory:

```sh
./install.sh --check
./install.sh --apply
```

Every `install.sh`, `status.sh` and `uninstall.sh` invocation creates a timestamped session under
`mhi2-altscreen-logs/` on the SD card. The session contains the complete console log and a sanitized
vehicle/firmware summary. VIN, FAZIT and device serial numbers are intentionally not collected.

If the installer finds an existing Java/bootclasspath state other than the validated NavIgnore-only
state, `--check` archives the current `lsd.sh`, available backups, JARs and hashes on the SD and
returns `PREFLIGHT=ATTENTION`. `--apply` then asks whether to abort or to use that archive as the
recovery copy, normalize the conflicting Java startup state and continue with the exact NavIgnore.
No target-side Java mutation is made until the required exact NavIgnore is known to be available.

The apply path then performs its hash/firmware gates, creates persistent backups, installs the
Stream-111 hook, installs the DisplayManager writev gate in STOCK-default mode, sets the navigation
profile to `map-rich`, and enables Auto-Direct persistence.

A reboot is required after installation.

After reboot:

```sh
./status.sh
```

The current D2 keyframe policy is deliberately **not permanently enabled by the installer** while the
1 s watchdog is still being tuned. During current development testing it can be enabled explicitly:

```text
/mnt/app/root/altscreen-u2/scripts/gen2_keyframes.sh on
```

## Uninstall

```sh
./uninstall.sh
```

The uninstaller stops/disables Auto-Direct, restores the exact backed-up stock
`smartphone_integrator.json`, restores the exact stock DisplayManager startup policy, and removes
NavIgnore only if this deployment installed it itself.

A reboot is required after restore.

### Issue evidence

For a public issue, attach `session.log` and `vehicle-summary.txt` from the relevant
`mhi2-altscreen-logs/<session>/` directory. The `archive/` subdirectory can contain copied
third-party/OEM JAR bytes and is intended for local recovery; do not upload it blindly.

## Scope

This is a developer convenience layer over vehicle-tested lower-level scripts. It does not change
the project's compatibility claims: a different firmware/hash is a stop condition, and matching firmware alone is not enough. The vehicle-proven reference also uses the project's **AID10-class** 10.x-inch MQB Virtual Cockpit family. A 12.3-inch AID or another cluster generation is a separate unvalidated target.


## Raw steering-wheel/keypanel mapping

The prepared developer directory also includes the read-only discovery helper:

```text
runtime/diagnostics/keypanel_trace_discovery.sh
```

It does not patch Java or modify logger state. Its purpose is only to identify the exact stock trace
reader/sink available on the target before collecting the built-in raw key lines:

```text
HK Received: KBD[n] KEY[n] KST[n]
```

### Live two-SSH key mapping

The prepared directory also carries:

```text
runtime/diagnostics/keypanel_capture.sh
runtime/diagnostics/keypanel_note.sh
```

Preferred first attempt, SSH session 1:

```sh
ksh runtime/diagnostics/keypanel_capture.sh --auto
```

The auto mode uses stock `sloginfo -w` only when that reader is actually present. If the exact
firmware exposes the key trace through another reader, first run
`keypanel_trace_discovery.sh`, then pipe the proven reader into the capture filter:

```sh
<proven-stock-reader-command> | ksh runtime/diagnostics/keypanel_capture.sh --stdin
```

SSH session 2:

```sh
ksh runtime/diagnostics/keypanel_note.sh
```

Type a description **before** performing each physical action, for example:

```text
VIEW kurz
VIEW lang bis OEM-Menue
VIEW sehr lang
Assistenz kurz
rechtes Rad +1
rechtes Rad Druck
```

Both NOTE markers and stock `HK Received` lines are appended in order to the same session log under
`/tmp/mibr-keypanel-<pid>/keypanel.log` by default. The scripts do not patch Java, remap keys or
change logger configuration.

After capture, copy that log off-unit and decode it with:

```text
python3 tools/parse_keypanel_trace.py --gestures keypanel.log
python3 tools/parse_keypanel_trace.py --summary keypanel.log
```

`--gestures` preserves your NOTE markers and reconstructs `SHORT`, `DOUBLE`, `LONG`,
`LONG2`, `LONG3` and the corresponding release state from the OEM DSI sequence.

Do not guess the physical VIEW button from constant names; map it from vehicle evidence.
