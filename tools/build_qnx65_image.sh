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
path.write_text(source.replace(needle, replacement, 1))
PY

docker buildx build --platform=linux/amd64 \
  --target base-env \
  --build-arg BASE=base-4.9 \
  --load \
  -t "$IMAGE" \
  "$WORKDIR"

echo "QNX_IMAGE_BUILD=PASS image=$IMAGE source=$TOOLCHAIN_COMMIT dockerfile_sha256=$ACTUAL_DOCKERFILE_SHA256"
