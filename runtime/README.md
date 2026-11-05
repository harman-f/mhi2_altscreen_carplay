# Shared runtime and diagnostics

The shared `runtime/` directory keeps cross-module diagnostics, deployment helpers and clearly experimental scripts. It is not an installer or a second canonical CarPlay runtime tree.

**CarPlay runtime now belongs exclusively to [`modules/carplay/runtime/`](../modules/carplay/runtime/):** `auto-direct/` contains the guarded Type-111 takeover/recovery scripts and ScreenAlt configuration; `parity/` contains native ownership/session supervision; `isotx2-gate/` contains DisplayManager gate operator controls. These unchanged files are staged into the **original** `runtime/<component>/` package/installation targets by `tools/prepare_mu1440_sd.sh` and related release tooling. Changing development paths must not alter target paths or behavior.

The matching native sources are under `modules/carplay/source/`, including `isotx2-gate/`. Reference-vehicle observations remain configuration-specific and do not qualify new packages automatically.

## `diagnostics/`

Shared SSH-oriented diagnostic and status helpers remain in `runtime/diagnostics/`. Their availability depends on the exact target; consult the QNX shell compatibility contract before using them on a Unit.

| File | Status |
|---|---|
| `deployment/session.sh` | staged by `tools/prepare_mu1440_sd.sh` |
| `diagnostics/gen2_keyframes.sh`, `gen2_resync.sh`, `gen2_status.sh` | staged |
| `diagnostics/keypanel_trace_discovery.sh`, `keypanel_capture.sh`, `keypanel_note.sh` | staged |
| `diagnostics/gen2_collect_logs.sh`, `gen2_prereq.sh`, `gen2_reacquire.sh` | manual diagnostics, not staged |
| `diagnostics/keypanel_note_native.sh`, `keypanel_start_native.sh` | manual diagnostics, not staged |
| `experimental/viewarea_mode.sh` | deliberately excluded from the package (checked by the release workflow) |

## `experimental/`

Experimental controls such as ViewArea toggles remain separate. Their presence does not imply an accepted installation or cross-platform feature.

## Developer deployment

`tools/prepare_mu1440_sd.sh` stages the exact-target developer payload for an SD directory. Deployment requires the approved target, verified backup/recovery and exact runtime qualification; this repository does not promise general end-user installation.
