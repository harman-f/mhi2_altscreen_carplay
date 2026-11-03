# Vehicle data source module

This project authored module consists of the host-testable `mvs_core` and `mibr_vdata` logic,
VehicleStatus projection, and the GEN2-side iAP2 adapter. The adapter forwards each original
HARMAN call unchanged before optionally sending a project-generated sentence through the same
handle. Its optional modes default to off and are controlled by the existing runtime configuration
files; this source publication does not claim that those modes were vehicle-qualified.

The module contains no copied OEM implementation. The public repository's GPL-3.0-or-later license
applies. The MVS wire format is project-owned and documented in `mvs_core.h`; the adapter depends on
the public QNX/POSIX interfaces and symbols already present in the receiver process.

Run the host-core fixtures with `bash tools/test_installed_gen2_host.sh`. They use synthetic values,
do not contain vehicle coordinates, and do not execute the QNX interposer.
