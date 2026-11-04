#!/usr/bin/env bash
# Build the pinned QNX 6.5 ARMv7 toolchain image without modifying an existing checkout.
set -euo pipefail

WORKDIR=${1:?usage: build_qnx65_image.sh NEW_TOOLCHAIN_WORKDIR [IMAGE_TAG]}
IMAGE=${2:-mhi2-qnx65-armv7-public:4.9}
TOOLCHAIN_REPO=${TOOLCHAIN_REPO:-https://github.com/luka-dev/qnx65-armv7-toolchain.git}
TOOLCHAIN_COMMIT=${TOOLCHAIN_COMMIT:-56a66557245af14077678cd28a83ce3a337d9e2d}
TOOLCHAIN_DOCKERFILE_SHA256=${TOOLCHAIN_DOCKERFILE_SHA256:-9a867a7ae70f2c0222a241b80232856526ccec0db2cfe013f8991ca31c74bcb1}

if [[ -e "$WORKDIR" ]]; then
  echo "Refusing to reuse an existing toolchain directory: $WORKDIR" >&2
  echo "Pass a new, empty path; this helper never removes source trees." >&2
  exit 2
fi

git clone --no-checkout "$TOOLCHAIN_REPO" "$WORKDIR"
git -C "$WORKDIR" checkout --detach "$TOOLCHAIN_COMMIT"
DOCKERFILE="$WORKDIR/Dockerfile"
ACTUAL_DOCKERFILE_SHA256=$(sha256sum "$DOCKERFILE" | awk '{print $1}')
if [[ "$ACTUAL_DOCKERFILE_SHA256" != "$TOOLCHAIN_DOCKERFILE_SHA256" ]]; then
  echo "Pinned Dockerfile digest mismatch: $ACTUAL_DOCKERFILE_SHA256" >&2
  exit 3
fi

# Repoint the historical Debian security mirror to its pinned snapshot so the
# frozen QNX SDK image remains buildable after the original mirror rotates.
python3 - "$DOCKERFILE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_text()
needle = "RUN dpkg --add-architecture i386 && apt-get update && \\\n"
replacement = (
    "RUN sed -i 's#http://deb.debian.org/debian-security#"
    "http://snapshot.debian.org/archive/debian-security/20260903T220410Z#g' "
    "/etc/apt/sources.list && \\\n"
    "    echo 'Acquire::Check-Valid-Until \"false\";' "
    "> /etc/apt/apt.conf.d/99snapshot && \\\n"
    "    dpkg --add-architecture i386 && apt-get update && \\\n"
)
if source.count(needle) != 1:
    raise SystemExit("qnx-sdp apt bootstrap anchor must occur exactly once")
source = source.replace(needle, replacement, 1)
# Keep the Dockerfile provenance pin above; replace the GCC fetch with
# a COPY of the host-fetched, SHA-256 verified identical tarball.
gcc_lines = source.splitlines(keepends=True)
matches = [
    i for i, line in enumerate(gcc_lines)
    if line.startswith('RUN curl -fsSL "https://ftp.gnu.org/gnu/gcc/gcc-${GCC49_VER}/gcc-${GCC49_VER}.tar.bz2"')
    and '-o /tmp/gcc49.tar.bz2 && ' in line
]
if len(matches) != 1:
    raise SystemExit("pinned GCC fetch anchor must occur exactly once")
gcc_lines[matches[0]] = "COPY gcc-4.9.4.tar.bz2 /tmp/gcc49.tar.bz2\nRUN "
path.write_text("".join(gcc_lines))
PY

# Pre-fetch GCC 4.9.4 on the host; Docker must not rely on ftp.gnu.org.
# The pinned source SHA is the one in the verified upstream Dockerfile.
GCC49_SHA256=6c11d292cd01b294f9f84c9a59c230d80e9e4a47e5c6355f046bb36d4f358092
GCC49_TARBALL="$WORKDIR/gcc-4.9.4.tar.bz2"
if [[ -n "${GCC49_SOURCE_ARCHIVE:-}" ]]; then
  [[ -s "$GCC49_SOURCE_ARCHIVE" ]] || { echo "GCC49_SOURCE_ARCHIVE_MISSING" >&2; exit 4; }
  cp -- "$GCC49_SOURCE_ARCHIVE" "$GCC49_TARBALL"
else
  GCC49_MIRRORS=(
    https://gcc.gnu.org/pub/gcc/releases/gcc-4.9.4/gcc-4.9.4.tar.bz2
    https://mirror.math.princeton.edu/pub/gcc/releases/gcc-4.9.4/gcc-4.9.4.tar.bz2
    https://ftp.mpi-inf.mpg.de/mirrors/gnu/mirror/gcc.gnu.org/pub/gcc/releases/gcc-4.9.4/gcc-4.9.4.tar.bz2
  )
  for URL in "${GCC49_MIRRORS[@]}"; do
    echo "GCC49_DOWNLOAD_TRY=$URL"
    rm -f "$GCC49_TARBALL.partial"
    if curl --fail --location --retry 2 --connect-timeout 15 --max-time 240 \
        --output "$GCC49_TARBALL.partial" "$URL"; then
      if printf '%s  %s\n' "$GCC49_SHA256" "$GCC49_TARBALL.partial" | sha256sum -c -; then
        mv "$GCC49_TARBALL.partial" "$GCC49_TARBALL"
        break
      fi
    fi
    rm -f "$GCC49_TARBALL.partial"
  done
fi
[[ -s "$GCC49_TARBALL" ]] || { echo "GCC49_DOWNLOAD=FAIL all mirrors" >&2; exit 5; }
printf '%s  %s\n' "$GCC49_SHA256" "$GCC49_TARBALL" | sha256sum -c - || {
  echo "GCC49_SHA256=FAIL" >&2; exit 6;
}
echo "GCC49_DOWNLOAD=PASS sha256=$GCC49_SHA256"

BUILD_ARGS=(--platform=linux/amd64 --target base-env --build-arg BASE=base-4.9)
if [[ "${QNX_BUILDX_GHA_CACHE:-0}" == 1 ]]; then
  BUILD_ARGS+=(--cache-from type=gha --cache-to type=gha,mode=max)
fi
docker buildx build "${BUILD_ARGS[@]}" --load -t "$IMAGE" "$WORKDIR"

echo "QNX_IMAGE_BUILD=PASS image=$IMAGE source=$TOOLCHAIN_COMMIT dockerfile_sha256=$ACTUAL_DOCKERFILE_SHA256 gcc49_sha256=$GCC49_SHA256"
