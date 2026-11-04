#!/usr/bin/env bash
set -euo pipefail

FFMPEG_VERSION="${FFMPEG_VERSION:-6.1.5}"
FFMPEG_SHA256="${FFMPEG_SHA256:-05fbe9db1f5452a3605bb1d9bf91da9d4bb08162891692e4f172b58c49109412}"
SRC="${1:-modules/carplay/source/direct-ts-remux/direct_ts_remux.c}"
OUT="${2:-build/direct-ts-remux}"
WORK="${WORK:-build/ffmpeg-remux}"
JOBS="${JOBS:-2}"

CC=arm-unknown-nto-qnx6.5.0eabi-gcc
AR=arm-unknown-nto-qnx6.5.0eabi-ar

# Match the vehicle-proven private build environment. The public Luka toolchain
# lives under /opt/qnx650; the historic FFmpeg build expects the /usr/qnx650 alias.
if [ ! -e /usr/qnx650 ]; then
  ln -s /opt/qnx650 /usr/qnx650
fi

# Fail early with a tiny target link test instead of hiding a toolchain problem
# inside FFmpeg configure.
printf '#include <stddef.h>\nint main(void){return 0;}\n' | "$CC" \
  -include stddef.h -D_QNX_SOURCE -O2 \
  -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 \
  -x c - -lsocket -o /tmp/mibr-qnx-link-smoke

mkdir -p "$WORK" "$(dirname "$OUT")"
TARBALL="$WORK/ffmpeg-${FFMPEG_VERSION}.tar.xz"
FFDIR="$WORK/ffmpeg-${FFMPEG_VERSION}"

if [ ! -f "$TARBALL" ]; then
  # Official FFmpeg tar.xz release, independently SHA-pinned by Buildroot.
  # MacPorts mirrors carry the original release bytes. The original ffmpeg.org
  # host is currently unreachable from public CI; do not use unsigned git HEAD.
  URLS=(
    "https://distfiles.macports.org/ffmpeg/ffmpeg-${FFMPEG_VERSION}.tar.xz"
    "https://mirror.math.princeton.edu/pub/macports/distfiles/ffmpeg/ffmpeg-${FFMPEG_VERSION}.tar.xz"
    "https://fco.it.distfiles.macports.org/ffmpeg/ffmpeg-${FFMPEG_VERSION}.tar.xz"
  )
  for URL in "${URLS[@]}"; do
    rm -f "$TARBALL.partial"
    if curl --fail --location --retry 3 --retry-all-errors \
      --retry-delay 2 --connect-timeout 12 --max-time 120 \
      "$URL" -o "$TARBALL.partial"; then
      if printf '%s  %s\n' "$FFMPEG_SHA256" "$TARBALL.partial" | sha256sum -c -; then
        mv "$TARBALL.partial" "$TARBALL"
        break
      fi
    fi
    rm -f "$TARBALL.partial"
  done
fi
[[ -s "$TARBALL" ]] || { echo "FFMPEG_SOURCE_FETCH=FAIL" >&2; exit 32; }
printf '%s  %s\n' "$FFMPEG_SHA256" "$TARBALL" | sha256sum -c -
printf 'source=ffmpeg-%s.tar.xz\nsha256=%s\n' "$FFMPEG_VERSION" "$FFMPEG_SHA256" > "$WORK/FFMPEG_SOURCE_ARCHIVE.txt"

if [ ! -f "$FFDIR/configure" ]; then
  rm -rf "$FFDIR"
  mkdir -p "$FFDIR"
  tar xf "$TARBALL" -C "$FFDIR" --strip-components=1
fi

if [ ! -f "$FFDIR/libavformat/libavformat.a" ]; then
  (
    cd "$FFDIR"
    ./configure       --cc="$CC"       --ar="$AR"       --ld="$CC"       --arch=arm       --target-os=qnx       --disable-asm       --disable-debug       --enable-cross-compile       --extra-cflags='-include stddef.h -D_QNX_SOURCE -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16'       --extra-libs='-lsocket'       --disable-doc       --disable-programs       --disable-avdevice       --disable-swresample       --disable-swscale       --disable-postproc       --disable-avfilter       --disable-everything       --enable-demuxer=h264       --enable-muxer=mpegts       --enable-protocol=file       --enable-protocol=tcp       --enable-parser=h264
    make -j"$JOBS"
  )
fi

"$CC"   -include stddef.h -D_QNX_SOURCE   -O2 -g -std=gnu99   -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16   -I"$FFDIR" "$SRC"   -Wl,--start-group   "$FFDIR/libavformat/libavformat.a"   "$FFDIR/libavcodec/libavcodec.a"   "$FFDIR/libavutil/libavutil.a"   -Wl,--end-group   -lbz2 -lz -lsocket -lm -lc   -o "$OUT"

# The pinned QNX 6.5 ARMv7 sysroot does not ship a separate libpthread;
# pthread APIs on this target are supplied by libc. Do not link -lpthread.
# Intentionally NO strip here.
test -s "$OUT"
