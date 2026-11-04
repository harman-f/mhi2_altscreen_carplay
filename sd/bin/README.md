# Extra SD binaries

This is a **logical bin catalog**, not a dump of all binaries present on an M.I.B. SD card. The canonical tracked binary files for the existing MU1440 developer package are:

- `artifacts/mu1440/sha256sum-compat/build-confirmed-current/sha256sum` → `payload/sha256sum`
- `artifacts/mu1440/tee-compat/build-confirmed-current/tee` → `payload/tee`

The explicit source paths and pinned SHA-256 values are in [`../manifest.json`](../manifest.json). During assembly these files are copied into the output SD root; duplicate executable blobs are intentionally **not** committed under `sd/bin/`.

New tools such as `sed` belong in the manifest only after their original artifact, license/provenance, ABI, target command behavior and integrity have been checked. No binary is assumed available merely because a similarly named program exists on Linux or an unrelated M.I.B. card.
