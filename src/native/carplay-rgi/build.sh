#!/bin/sh
# Build the MU1440 route-guidance step-1 artifacts for QNX 6.5 armle-v7 with clang + ld.lld.
#   QNX_TARGET=<.../target/qnx6> ./build.sh [outdir]
# QNX_TARGET is the SDP sysroot from the pinned QNX toolchain (commit
# 56a66557245af14077678cd28a83ce3a337d9e2d in .github/workflows/build-mu1440-source.yml).
# This standalone build uses caller-provided Clang/LLD; the common source workflow's GCC build
# does not currently invoke this optional RGI build. IAP2_LIB must point to a locally
# obtained MU1440 libiap2client.so.1; firmware bytes are deliberately not part of this repository.
# The exact reviewed library SHA-256 is pinned below.
# Two PT_LOADs (RX, RW) and base 0x100000 for the executable, like the stock QNX 6.5 binaries.
# Shared library: no .init_array (QNX 6.5 runtime linker); the entry is DT_INIT = mibr_rgi_ipod_init.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/build}"
: "${QNX_TARGET:?set QNX_TARGET to the QNX 6.5 sdp target/qnx6 directory}"
CLANG="${CLANG:-clang}"
LLD="${LLD:-ld.lld}"
SYS="$QNX_TARGET/armle-v7"
EXPECTED_IAP2_SHA256=c33021b21c5656886e64964efcf806fddb4259027c3c1ed396522e7a44adfdea
: "${IAP2_LIB:?set IAP2_LIB to the locally available MU1440 libiap2client.so.1}"
test -f "$IAP2_LIB" || { echo "IAP2_LIB_NOT_A_FILE: $IAP2_LIB" >&2; exit 2; }
actual_iap2_sha256=$(sha256sum "$IAP2_LIB" | awk '{print $1}')
test "$actual_iap2_sha256" = "$EXPECTED_IAP2_SHA256" || {
  echo "IAP2_LIBRARY_HASH_MISMATCH: expected $EXPECTED_IAP2_SHA256, got $actual_iap2_sha256" >&2
  exit 3
}
CFLAGS="--target=armv7a-none-eabi -marm -mfloat-abi=softfp -fPIC -Os -std=gnu99 -Wall -Wextra -Werror -DENABLE_LOGGING=0
 -Wno-unused-function -fno-stack-protector -fvisibility=hidden -D__QNX__ -D__QNXNTO__ -D__ARM__ -D__LITTLEENDIAN__
 -nostdinc -isystem $QNX_TARGET/usr/include -isystem $($CLANG -print-resource-dir)/include
 -I$HERE/src/common -I$HERE/third_party/luka-rgd -I$HERE/third_party/luka-rgd/framework"

mkdir -p "$OUT"
OBJ=$(mktemp -d "$OUT/.objects.XXXXXX")
trap 'rm -rf "$OBJ"' 0
cc() { "$CLANG" $CFLAGS -c "$1" -o "$OBJ/$2.o"; }
cc "$HERE/src/common/mibr_rgi_wire.c" wire
cc "$HERE/src/ipod/mibr_rgi_ipod.c" ipod
cc "$HERE/src/helper/mibr_rgi.c" helper
cc "$HERE/src/common/mibr_rgi_guidance.c" guidance
cc "$HERE/third_party/luka-rgd/routeguidance/rgd_tlv.c" rgd_tlv
"$CLANG" $CFLAGS -fno-builtin -c "$HERE/src/common/mibr_aeabi_mem.c" -o "$OBJ/aeabi.o"

"$LLD" -shared --no-rosegment -z norelro -z max-page-size=0x1000 --hash-style=sysv --gc-sections -soname libmibr_rgi_ipod.so \
  -init mibr_rgi_ipod_init -o "$OUT/libmibr_rgi_ipod.so" \
  "$OBJ/ipod.o" "$OBJ/wire.o" "$OBJ/aeabi.o" -L"$SYS/lib" -lc

"$LLD" --image-base=0x100000 --no-rosegment -z norelro -z max-page-size=0x1000 --hash-style=sysv --dynamic-linker /usr/lib/ldqnx.so.2 \
  -o "$OUT/mibr-rgi" "$SYS/lib/crt1.o" "$SYS/lib/crti.o" "$SYS/lib/crtbegin.o" \
  "$OBJ/helper.o" "$OBJ/guidance.o" "$OBJ/wire.o" "$OBJ/rgd_tlv.o" "$OBJ/aeabi.o" \
  -L"$SYS/lib" -lc --allow-shlib-undefined "$IAP2_LIB" "$SYS/lib/crtend.o" "$SYS/lib/crtn.o"

( cd "$OUT" && sha256sum libmibr_rgi_ipod.so mibr-rgi > SHA256SUMS )
echo "$OUT"
