# Navigation runtime helpers

This directory contains the GEN2 navigation surface and SafeArea controls.

## Vehicle-tested helpers

- `gen2_nav_config.sh` — live/persistent navigation surface and query controls.

These paths were exercised during the 2026-09-27 MU1440 vehicle run.

## Development helper

- `gen2_safearea.sh` — persistent SafeArea geometry configuration.

The SafeArea helper corresponds to newer build-confirmed source and has **not yet been vehicle
validated**.

Direct vehicle shell use remains developer-only. MU1440 is QNX; do not assume GNU/Linux utility
availability or option syntax.

## Route-guidance launcher

- `mm-ipod-rgi.sh` is the source of the `mm-ipod-rgi` wrapper (installed name without `.sh`). The unit's USB launcher
  selects it only while the enable file `/mnt/app/root/mibr/config/features/rgi.on` exists. It copies `/etc/mm/iap2.cfg` into RAM,
  starts the `mibr-rgi` helper and then `exec`s the stock `mm-ipod` with `libmibr_rgi_ipod.so` preloaded. The stock
  config is never modified. It runs fully stock when the kit is disabled, after an identification rejection, or when
  the RAM copy already has an `[ident]` section. The library and helper sources are in
  [`../source`](../source/README.md). Not vehicle-qualified by this publication.
