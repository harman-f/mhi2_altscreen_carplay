# Developer installation

The project now publishes a **developer deployment path**, not an end-user SD-card solution.

It intentionally assumes the operator already has shell access and understands MHI2/QNX recovery.
No instructions are provided for obtaining SSH access.

## Reference target only

```text
MHI2_ER_SKG13_P4526_MU1440
libairplay.so SHA-256:
193a4fd9101ec2aa05e7159cfa307b96500810d379ca74a194f172adc13a46b5
```

Different target hashes are stop conditions. The current vehicle proof is additionally limited to the reference **AID10-class 10.x-inch MQB Virtual Cockpit**. Cluster generation/hardware is a separate compatibility gate; a known MU1440-compatible software baseline does not prove a 12.3-inch AID target.

## Existing Type-111 host-firewall prerequisite (TCP 6031)

The MU1440 reference vehicle already has the narrow inbound `carplay0` exception for the
project's Type-111 receiver. This documents an **existing vehicle-side setup**; it is not a
request to add another rule or change the active vehicle. The normal CarPlay allowlist does
not, by itself, prove that a custom secondary stream port is reachable.

The intended effective PF rule for the default `ALTSCREEN111_PORT=6031` is:

```pf
pass in quick on carplay0 proto tcp from any to any port 6031 allow-opts
```

- Scope is **inbound TCP on the iPhone's CarPlay interface `carplay0`**, port **6031 only**.
  Do not disable PF or open 6031 on unrelated WLAN, cellular, debug or external interfaces.
- Port `6031` is the iPhone-to-head-unit Type-111 video transport. The local H.264 tee at
  `127.0.0.1:19820` is a separate loopback interface and is **not** an inbound CarPlay
  firewall exception.
- The rule must be in the **effective** PF policy after boot, not merely present in a
  file or a staged configuration. Check the loaded rules read-only with the unit's
  `pfctl -sr` and verify the 6031 listener separately with `netstat -an`.
  Neither SETUP success nor a listening socket alone proves inbound connectivity:
  corroborate with an accepted iPhone connection and advancing VideoConfig/frame counters.
- For another firmware/vehicle, first identify its actual PF startup/configuration path
  (including any variant files), preserve the original bytes, inspect existing rules and
  obtain a deliberate, narrowly scoped change and rollback procedure. Never blindly
  append duplicate rules or overwrite other tooling's modifications.
- **Ownership boundary:** the currently published `deployment/mu1440/install.sh` and
  `uninstall.sh` do not install or remove a PF rule. The existing vehicle-side exception
  must be audited and backed up/restored separately; do not assume that uninstalling the
  CarPlay payload removes it.

If Type 111 is advertised in SETUP but no video connection follows, verify the effective
`carplay0` rule before attributing the failure to the hook, decoder or MOST output.
The distinct port roles and diagnostic sequence are in
[STREAM111_PROTOCOL.md](research/STREAM111_PROTOCOL.md#111-mu1440-carplay0-firewall-and-port-ownership)
and [VEHICLE_TEST_PROTOCOL.md](testing/VEHICLE_TEST_PROTOCOL.md#4-verify-the-type-111-source-separately).

## Prepare

From a workstation checkout:

```sh
tools/prepare_mu1440_sd.sh /path/to/mounted-sd-root
```

The generated `install.sh`, `status.sh`, `uninstall.sh`, `PAYLOAD.sha256`, `payload/` and `runtime/` paths live directly in the SD-card root. No `esd/` or `MHI2AltScreen/` wrapper directory is created.

The deployment contains individually auditable payload files; it deliberately does not publish an
opaque install archive.

### Target-side compatibility helpers

The prepared developer directory carries its own reproducibly built QNX ARMv7 `payload/sha256sum` and `payload/tee` helpers. This preserves the stable logging/hash behavior previously obtained from M.I.B. without requiring its `apps/sbin` tree.

The current deployment does not require `sed`; the only former runtime use was replaced with stock `awk` because older firmware trains are known not to provide `sed` consistently.

The prepared package includes the exact vehicle-tested `payload/MIBR-NavIgnore.jar`. Its hash is checked before any target mutation. Provenance and the upstream license are recorded under `THIRD_PARTY/NavIgnore/`.

`MIBR_SHA256` remains an expert override for a separately verified compatible helper. Missing or
non-executable hash support is a hard stop; target/payload verification is never skipped.

## Unknown target: collect first, do not install

For a target that has not yet been validated, use the standalone read-only collector first:

```sh
./compatibility-report.sh
```

It creates the same sanitized vehicle/firmware summary used by install/status logging, then adds
component hashes, relevant process/device observations, and read-only snapshots of
`displaymanager.json`, `dio_manager.json`, and `smartphone_integrator.json`.

No target filesystem is remounted writable and no vehicle file is changed. Only the deployment
SD/USB medium is made writable for the report output.

## Apply

```sh
./install.sh --check
./install.sh --apply
```

The installer:

1. verifies exact target and payload hashes;
2. inventories the current Java/bootclasspath state and archives foreign patch state to the SD before any Java replacement;
3. in `--apply` mode, asks whether to abort or normalize an archived foreign Java state before continuing;
4. stages the tested GEN2 and direct remux runtime internally;
5. preflights and installs the DisplayManager isoTX2 writev gate with STOCK as the fail-safe/default mode;
6. prepares the persistent CarPlay Stream-111 preload with a verified stock backup;
7. verifies the bundled exact vehicle-proven NavIgnore (`b065bab0…`) and installs it when the target does not already have that exact state;
8. sets the initial navigation composition profile to `map-rich`;
9. prepares Auto-Direct persistence **without starting a pre-reboot takeover**;
10. requires a reboot rather than hot-restarting the CarPlay process stack.

## Keyframe policy

The vehicle-proven D2 keyframe policy is available, but the current 1 s watchdog is intentionally
still under tuning. The installer therefore does not silently make that policy permanent.

## SafeArea

The public development source/helper contains configurable SafeArea work, but the stable installer
continues to use the exact 2026-09-27 vehicle-tested GEN2 binary until the SafeArea-capable candidate
has completed its vehicle validation.

## Restore

```sh
./uninstall.sh
```

Restore paths are hash-gated and preserve evidence/runtime files for diagnosis.

See `deployment/mu1440/README.md` for the compact operator view.


## Compatibility helpers and hidden dependencies

The prepared developer directory contains its own public, reproducibly built QNX ARMv7
`sha256sum` and `tee` compatibility helpers. Installation no longer depends on a pre-existing M.I.B.
`/apps/sbin` SD-card tree. The installer also explicitly remounts the active SD/USB deployment medium writable and performs a write test before relying on persistent media logging.

The preflight also verifies the exact command set required by the currently published scripts
before any persistent mutation. This is intentional: common Linux command names/options are not
assumed to exist on QNX.

The top-level preflight inventories experimental DirectVC, legacy Most20FPS, the older combined
`NavActiveIgnore.jar`, and other foreign bootclasspath/JAR states. It archives the original state
to the SD before any Java replacement; `--check` stops with `PREFLIGHT=ATTENTION`, while
`--apply` requires an explicit continue/abort decision before normalization.


## SD session logs and recovery evidence

The top-level `install.sh`, `status.sh` and `uninstall.sh` commands log their complete stdout/stderr
to a timestamped SD-card directory:

```text
mhi2-altscreen-logs/<timestamp>-<action>-<pid>/
  session.log
  vehicle-summary.txt
  archive/
```

The summary records firmware/train/MU when readable, selected version/board metadata, relevant target
hashes, active Java bootclasspath lines and JAR hashes. VIN, FAZIT and device serial numbers are
deliberately excluded.

Known or unknown active Java overrides are not silently overwritten. The original Java state is
archived first. `install.sh --check` remains non-interactive and reports `PREFLIGHT=ATTENTION`.
During `install.sh --apply`, the operator may abort or explicitly continue with archive + Java
normalization. The installer verifies that the exact required NavIgnore can be reached **before**
performing that target-side Java mutation.

For public issue reports, `session.log` and `vehicle-summary.txt` are the intended default
attachments. Review `archive/` locally before sharing it; copied JARs there may contain
third-party/OEM-derived code.


## Current MU1440 reference defaults

The validated developer install now treats these as the reference defaults:

- exact `MIBR-NavIgnore.jar` active in J9;
- exact `MIBR-Most20FPS.jar` active in J9;
- 1010x376 coded-frame/map-surface baseline;
- Auto-Direct persistent;
- GEN2 D2 keyframe recovery persistent with a 1,000 ms source-IDR watchdog and 1,000 ms minimum request gap.

Most20 is no longer an experimental optional add-on on the MU1440 reference target. The 2026-09-29
stock-`isoTX2` capture proved that the standalone patch changes the real native H.264/MPEG-TS stream
from 10 fps to 20 fps.

Advanced and diagnostic runtime switches are documented in
[ADVANCED_RUNTIME_SWITCHES.md](architecture/ADVANCED_RUNTIME_SWITCHES.md).
