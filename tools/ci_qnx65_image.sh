#!/usr/bin/env bash
# CI runner only: consume a verified immutable QNX 6.5 ARMv7 compiler image.
# The old source bootstrap remains an explicitly enabled transition/recovery path.
set -euo pipefail

IMAGE=${IMAGE:-mhi2-qnx65-armv7-public:4.9}
QNX65_VERIFIED_IMAGE=${QNX65_VERIFIED_IMAGE:-}
QNX65_LEGACY_REBUILD_ALLOWED=${QNX65_LEGACY_REBUILD_ALLOWED:-0}
TOOLCHAIN_COMMIT=${TOOLCHAIN_COMMIT:-56a66557245af14077678cd28a83ce3a337d9e2d}
TOOLCHAIN_DOCKERFILE_SHA256=${TOOLCHAIN_DOCKERFILE_SHA256:-9a867a7ae70f2c0222a241b80232856526ccec0db2cfe013f8991ca31c74bcb1}
RUNNER_TEMP=${RUNNER_TEMP:-${TMPDIR:-/tmp}}
PROVENANCE="$RUNNER_TEMP/qnx65-toolchain-provenance.txt"
COMPILER=arm-unknown-nto-qnx6.5.0eabi-gcc
READELF=arm-unknown-nto-qnx6.5.0eabi-readelf

if [[ -n "$QNX65_VERIFIED_IMAGE" ]]; then
  # Check syntax *before* using it in Docker. No mutable tags, no fallback if
  # pull or compatibility validation fails, and no account identity in source.
  if [[ ! "$QNX65_VERIFIED_IMAGE" =~ ^ghcr[.]io/[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+@sha256:[0-9a-f]{64}$ ]]; then
    echo "QNX_IMAGE_REF=FAIL expected an approved ghcr.io/name@sha256:64hex reference" >&2
    exit 10
  fi
  # Suppress registry ownership and image path in public CI logs.
  if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    echo "::add-mask::$QNX65_VERIFIED_IMAGE"
  fi
  echo "QNX_IMAGE_MODE=ARCHIVED_PULL"
  if ! docker pull "$QNX65_VERIFIED_IMAGE" > "$RUNNER_TEMP/qnx65-image-pull.log" 2>&1; then
    echo "QNX_IMAGE_PULL=FAIL (registry access or digest mismatch; no automatic source fallback)" >&2
    exit 11
  fi
  image_arch=$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$QNX65_VERIFIED_IMAGE")
  [[ "$image_arch" == linux/amd64 ]] || {
    echo "QNX_IMAGE_PLATFORM=FAIL (expected linux/amd64, got $image_arch)" >&2; exit 12;
  }
  actual_refs=$(docker image inspect --format '{{range .RepoDigests}}{{println .}}{{end}}' "$QNX65_VERIFIED_IMAGE")
  grep -Fxq -- "$QNX65_VERIFIED_IMAGE" <<< "$actual_refs" || {
    echo "QNX_IMAGE_DIGEST=FAIL registry digest missing from local image" >&2; exit 13;
  }
  compiler_ver=$(docker run --rm --platform=linux/amd64 "$QNX65_VERIFIED_IMAGE" "$COMPILER" -dumpversion)
  [[ "$compiler_ver" == 4.9* ]] || {
    echo "QNX_COMPILER=FAIL expected GCC 4.9, got $compiler_ver" >&2; exit 14;
  }
  docker run --rm --platform=linux/amd64 "$QNX65_VERIFIED_IMAGE" \
    bash -c 'command -v arm-unknown-nto-qnx6.5.0eabi-gcc >/dev/null &&
             command -v arm-unknown-nto-qnx6.5.0eabi-readelf >/dev/null &&
             command -v qcc >/dev/null &&
             command -v bash >/dev/null'
  # Existing project build jobs use IMAGE locally. Only tag *after* verification.
  docker image tag "$QNX65_VERIFIED_IMAGE" "$IMAGE"
  {
    echo "mode=archived-pinned"
    echo "image_manifest_digest=${QNX65_VERIFIED_IMAGE##*@}"
    echo "image_id=$(docker image inspect --format '{{.Id}}' "$IMAGE")"
    echo "compiler=$COMPILER"
    echo "compiler_version=$compiler_ver"
    echo "target=QNX_6.5_ARMv7"
    echo "upstream_toolchain_commit=$TOOLCHAIN_COMMIT"
    echo "upstream_dockerfile_sha256=$TOOLCHAIN_DOCKERFILE_SHA256"
    echo "source_revision=${GITHUB_SHA:-unknown}"
    echo "vehicle_qualified=false"
    echo "bit_reproducible_verified=false"
  } > "$PROVENANCE"
  echo "QNX_IMAGE_PULL=PASS platform=linux/amd64 compiler=$compiler_ver digest-verified=true"
  mode=archived-pinned
else
  [[ "$QNX65_LEGACY_REBUILD_ALLOWED" == 1 ]] || {
    echo "QNX_IMAGE_NOT_CONFIGURED=FAIL; supply QNX65_VERIFIED_IMAGE as a digest-qualified repository variable" >&2
    exit 15
  }
  echo "::warning::QNX65_VERIFIED_IMAGE is not configured. Explicit transitional source-bootstrap path enabled; this rebuilds GCC and is not the archived-image migration."
  echo "QNX_IMAGE_MODE=LEGACY_REBUILD"
  QNX_BUILDX_GHA_CACHE=1 bash tools/build_qnx65_image.sh \
    "$RUNNER_TEMP/qnx-toolchain-${GITHUB_RUN_ID:-manual}-${GITHUB_RUN_ATTEMPT:-1}" "$IMAGE"
  compiler_ver=$(docker run --rm --platform=linux/amd64 "$IMAGE" "$COMPILER" -dumpversion)
  [[ "$compiler_ver" == 4.9* ]] || {
    echo "QNX_COMPILER=FAIL expected GCC 4.9, got $compiler_ver" >&2; exit 16;
  }
  {
    echo "mode=legacy-rebuild"
    echo "image_id=$(docker image inspect --format '{{.Id}}' "$IMAGE")"
    echo "compiler=$COMPILER"
    echo "compiler_version=$compiler_ver"
    echo "target=QNX_6.5_ARMv7"
    echo "upstream_toolchain_commit=$TOOLCHAIN_COMMIT"
    echo "upstream_dockerfile_sha256=$TOOLCHAIN_DOCKERFILE_SHA256"
    echo "source_revision=${GITHUB_SHA:-unknown}"
    echo "vehicle_qualified=false"
    echo "bit_reproducible_verified=false"
  } > "$PROVENANCE"
  mode=legacy-rebuild
fi

if [[ -n "${GITHUB_ENV:-}" ]]; then
  {
    echo "QNX_TOOLCHAIN_MODE=$mode"
    echo "QNX_TOOLCHAIN_PROVENANCE=$PROVENANCE"
  } >> "$GITHUB_ENV"
fi
echo "QNX_IMAGE_READY=PASS mode=$mode compiler_version=$compiler_ver"
