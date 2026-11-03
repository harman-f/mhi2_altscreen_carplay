# Shared runtime and diagnostics

The shared `runtime/` directory keeps cross-module diagnostics, deployment helpers and clearly experimental scripts. It is not an installer or a second canonical CarPlay runtime tree.

**CarPlay runtime now belongs exclusively to [`modules/carplay/runtime/`](../modules/carplay/runtime/):** `auto-direct/` contains the guarded Type-111 takeover/recovery scripts and ScreenAlt configuration; `parity/` contains native ownership/session supervision; `isotx2-gate/` contains DisplayManager gate operator controls. These unchanged files are staged into the **original** `runtime/<component>/` package/installation targets by `tools/prepare_mu1440_sd.sh` and related release tooling. Changing development paths must not alter target paths or behavior.

The matching native sources are under `modules/carplay/source/`, including `isotx2-gate/`. Reference-vehicle observations remain configuration-specific and do not qualify new packages automatically.

## `diagnostics/`

Shared SSH-oriented diagnostic and status helpers remain in `runtime/diagnostics/`. Their availability depends on the exact target; consult the QNX shell compatibility contract before using them on a Unit.

## `experimental/`

Experimental controls such as ViewArea toggles remain separate. Their presence does not imply an accepted installation or cross-platform feature.

## Developer deployment

`tools/prepare_mu1440_sd.sh` stages the exact-target developer payload for an SD directory. Deployment requires the approved target, verified backup/recovery and exact runtime qualification; this repository does not promise general end-user installation.
