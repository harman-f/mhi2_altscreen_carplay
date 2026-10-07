#!/usr/bin/env bash
set -euo pipefail

QCC="${QCC:-qcc}"
OUTDIR="${1:-build/support-tools}"

mkdir -p "$OUTDIR"

"$QCC"   -shared -fPIC -mfloat-abi=softfp   -O2 -g -std=gnu99 -Wall -Wextra   src/native/isotx2-gate/isotx2_gate.c   -Wl,-soname,libmibr_isotx2_gate.so   -o "$OUTDIR/libmibr_isotx2_gate.so"

"$QCC"   -mfloat-abi=softfp   -O2 -g -std=gnu99 -Wall -Wextra   src/native/isotx2-gate/gate_selftest.c   -o "$OUTDIR/gate_selftest_qnx"

"$QCC"   -mfloat-abi=softfp   -O2 -g -std=gnu99 -Wall -Wextra   src/native/most-ts-writer/most_ts_writer.c   -o "$OUTDIR/most-ts-writer"

# Developer artifacts are intentionally not stripped.


"$QCC"   -mfloat-abi=softfp   -O2 -g -std=gnu99 -Wall -Wextra   src/native/sha256sum-compat/sha256sum_compat.c   -o "$OUTDIR/sha256sum"


"$QCC"   -mfloat-abi=softfp   -O2 -g -std=gnu99 -Wall -Wextra   src/native/tee-compat/tee_compat.c   -o "$OUTDIR/tee"

"$QCC" \
  -mfloat-abi=softfp \
  -O2 -g -std=gnu99 -Wall -Wextra \
  src/native/qnx-shmem-probe/shmem_fs_probe.c \
  -o "$OUTDIR/shmem-fs-probe"


"$QCC" \
  -mfloat-abi=softfp \
  -O2 -g -std=gnu99 -Wall -Wextra \
  src/native/qnx-bound-process-probe/bound_process_probe.c \
  -o "$OUTDIR/bound-process-probe"


"$QCC" \
  -mfloat-abi=softfp \
  -O2 -g -std=gnu99 -Wall -Wextra \
  src/native/tcp-capture/tcp_capture.c \
  -lsocket \
  -o "$OUTDIR/tcp-capture"
