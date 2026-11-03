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
