# Extra SD scripts

These are **references to the maintained project installation/verification scripts**, not a complete third-party SD card snapshot. The currently inventoried entrypoints are `install.sh`, `status.sh`, `uninstall.sh`, `compatibility-report.sh`, and their shared `runtime/deployment/session.sh` helper. Their canonical sources are under `deployment/mu1440/` and `runtime/deployment/`, with stage paths and byte checks in [`../manifest.json`](../manifest.json).

Other on-unit runtime scripts are copied from their module owners by `tools/prepare_mu1440_sd.sh` and scanned separately in the release workflow. Script changes must be made at the canonical source, never in a copied release ZIP. Each package must pass target-shell static validation and exact-board command checks before an installation is authorized.
