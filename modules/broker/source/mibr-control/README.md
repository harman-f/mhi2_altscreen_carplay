# MIBR/3 native controller source

This directory contains the source for the MIBR/3 loopback controller and its
small support programs. It is a source-only reference module. It is not an
installer, a vehicle-ready package, or evidence that a setting or route change
was applied on a unit.

## Source and dependency boundary

The controller is built against the canonical schema-2 settings implementation
in `../alt111-settings/` and its policy/header dependencies in
`../altscreen111-gen2/` and `../sha256sum-compat/`. The canonical registry and
value validators remain owned by that settings implementation. This module
does not copy or regenerate a second settings registry.

The R57 service source is identified by its source-file hash in the build
receipt. Its settings dependency descends from
`harman-f/mhi2_altscreen_carplay@324b4f249883bb707e0d0a8995b2b6b5fe23be25`;
this module builds against the current shared registry at
`settings/registry.json` (SHA-256
`818cfd7b635742c98e291c3a6eb4a4350bec873715245d2d888fcac360ccd098`).
The corresponding installed R57 service SHA-256 was
`97177ddbfe78d49dc0d672c5b70e717a87c0aeebb6ac65ab4e1b7df12e60bb58`.
The source revision and dependency pin identify the input; a build reproduction
is a separate result and must be recorded by the build step.

The public `runtime/mibr-control/mibr-engine.ksh` helper also contains a
review-driven write-safety correction: it remounts `/mnt/system` read-write
before creating its same-filesystem staging file and requests a read-only
remount after remount, staging, and replacement failures. It intentionally is
not byte-identical to the installed R46 helper, whose SHA-256 was
`05986352f312bf2dc7b46223ffa2aa666d7127d38e432b15efcaf133d3be2f31`. The
corrected public helper SHA-256 is
`e4533241733f6e3afea3402fa58e131b065665734e0c053b25442d68ddbfd127`. The
host mock-mount regression verifies ordering and cleanup only; it makes no
exact-target filesystem claim.

The source includes:

- `mibr_v3_service.c`, the authenticated, loopback-only MIBR/3 service;
- the native settings projection, guarded profile store and recovery support;
- route and KEY40 policy adapters that are not attached to a qualified live
  owner in this source snapshot;
- `mibr_v3_client.c` (`mibrctl-v3`) and `mibr_v3_genkey.c`;
- `mibr_key40d.c`, the installed support daemon source. KEY40 short press
  advances the view counter; KEY40 long press resynchronizes to the configured
  view-after-long-press; KEY44 long press requests the existing route toggle.
  These source mappings preserve R57 behavior; they do not qualify a physical
  input port or route action on a vehicle.
- `runtime/mibr-control/mibr-view.ksh`, the helper for the cockpit-view counter,
  its configured resync view, and the existing `viewarea.selected` TEMP write.
  Its defaults are fixed-view mode OFF, Sporttacho present ON, and resync target
  Voll. The r57 long press advances the OEM view once and the helper records the
  next view after the selected resync target.

The service exposes `stored`, `materialized`, `apply`, and `active` as separate
facts. A durable profile readback is not the same as TEMP materialization;
either is distinct from an apply request, and neither proves live runtime
activation. `active=UNKNOWN` remains the honest state without independent
runtime evidence. Route/input capabilities remain disabled until their
qualified providers are actually attached. Physical input and independent
visible-route/ACTIVE validation remain open. Do not enable a capability by
changing a compile flag alone.

## Build and host regression

From the repository root, with the canonical settings sources present:

```sh
tools/build_mibr_control.sh host
MIBR_V3_NATIVE_HOST_BIN=build/mibr-control/mibr-v3-service-host \
  python3 -B -m unittest discover -s tests/mibr-control -v
tools/build_mibr_control.sh qnx
```

For an integrated build already running in the pinned QNX container, use
`tools/build_mibr_control.sh qnx-container`; it writes the same outputs and
uses the same target flags as the Docker convenience mode. Build the toolchain
from the pinned recipe in
[`docs/build/INSTALLED_GEN2_SOURCE.md`](../../../docs/build/INSTALLED_GEN2_SOURCE.md).
The build emits artifacts explicitly named `NOT-INSTALL-READY`. It compiles
source only; it does not stage or write a target. See
[`docs/architecture/mibr-control/BUILD_AND_EVIDENCE.md`](../../../docs/architecture/mibr-control/BUILD_AND_EVIDENCE.md)
for the toolchain pin, output interpretation and source/binary hash limits.

## Runtime limits

The related scripts are in [`runtime/mibr-control/`](../../../runtime/mibr-control/).
They include the corrected public engine helper described above, the boot
helper, and the R57 view helper for source review. The engine helper
intentionally differs from the installed R46 script; the boot helper is not a
qualified startup integration. In particular,
filesystem behavior, credentials, same-user access, durable write guards,
boot recovery, live owner binding, and physical route visibility still require
separate exact-target evidence. No vehicle access was part of this publication.

The module is GPL-3.0-or-later, consistent with the repository's project source
and the pinned upstream settings implementation. No OEM binary, JAR, firmware
file, private log, credential, or third-party asset is included here.
