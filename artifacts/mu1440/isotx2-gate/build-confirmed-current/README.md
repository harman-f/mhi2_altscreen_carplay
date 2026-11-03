# Build-confirmed isoTX2 writev gate

This binary is produced by the pinned public QNX 6.5 ARMv7 workflow from
`modules/carplay/source/isotx2-gate/isotx2_gate.c`.

The gate mechanism/source has been vehicle-proven on the MU1440 reference target.
This particular public binary is labelled **build-confirmed** unless its exact SHA-256
is separately recorded in a vehicle test.

The library defaults to STOCK/pass-through behavior. DIRECT suppression is only requested
through the explicit runtime marker/control path.

See `docs/architecture/DIRECT_VC_VIDEO_PATH.md` and `modules/carplay/runtime/isotx2-gate/`.
