#!/usr/bin/env bash
# Build OEM-derived HMI JARs from private, locally provisioned inputs and assemble
# the complete three-profile package. Never copy private inputs into the artifact.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
ROOT_REAL="$(cd "$ROOT" && pwd -P)"
BUILD_SCRIPT="$ROOT/modules/menu/source/build.sh"
PROFILES=(skoda-mu1440-p4526 seat-mu1409-p4708 seat-mu1447-p4709)

MIBR_MENU_JAR_MODE="${MIBR_MENU_JAR_MODE:-prebuilt}"
case "$MIBR_MENU_JAR_MODE" in
  prebuilt|rebuild) ;;
  *) echo "MIBR_MENU_JAR_MODE_INVALID: expected prebuilt or rebuild" >&2; exit 18 ;;
esac

# In prebuilt mode the three profile JARs always come from pinned Git
# artifacts. The separately required extender may also be supplied as an
# independently built, hash-pinned local binary. Otherwise J9 is still needed.
NEEDS_PRIVATE_J9=1
if [[ "$MIBR_MENU_JAR_MODE" == "prebuilt" && -n "${MIBR_PREBUILT_EXTENDER_JAR:-}" ]]; then
  NEEDS_PRIVATE_J9=0
  : "${MIBR_PREBUILT_EXTENDER_SHA256:?MISSING_EXTENDER_PIN: set the reviewed extender JAR SHA-256}"
  [[ "$MIBR_PREBUILT_EXTENDER_SHA256" =~ ^[0-9a-f]{64}$ ]] || {
    echo 'MIBR_PREBUILT_EXTENDER_BAD_SHA256' >&2; exit 20;
  }
else
  : "${J9_HOME:?MISSING_INPUT: set J9_HOME to the locally provisioned IBM J9 SDK}"
  : "${MIBR_PRIVATE_INPUT_ROOT:?MISSING_INPUT: set private input root (not a GitHub artifact or repository path)}"
  : "${MIBR_PRIVATE_INPUT_MANIFEST_SHA256:?MISSING_TOOLCHAIN_PIN: set private input manifest SHA-256}"
  : "${MIBR_J9_JAVAC_SHA256:?MISSING_TOOLCHAIN_PIN: set the approved J9 javac SHA-256}"
  : "${MIBR_J9_JAR_SHA256:?MISSING_TOOLCHAIN_PIN: set the approved J9 jar SHA-256}"
fi
: "${QNX65_GHCR_TOKEN:?MISSING_INPUT: QNX image read-only token is required}"
: "${QNX_TARGET:?MISSING_INPUT: private QNX 6.5 target sysroot is required for route guidance}"
: "${MIBR_QNX_TARGET_MANIFEST_SHA256:?MISSING_TOOLCHAIN_PIN: set QNX target manifest SHA-256}"
: "${IAP2_LIB:?MISSING_INPUT: private exact MU1440 IAP2 library is required for route guidance}"
: "${CLANG:?MISSING_INPUT: provisioned Clang executable is required for route guidance}"
: "${LLD:?MISSING_INPUT: provisioned LLD executable is required for route guidance}"
: "${FFMPEG:?MISSING_INPUT: pinned ffmpeg executable is required for calibration clip}"
: "${MIBR_CLANG_SHA256:?MISSING_TOOLCHAIN_PIN: set the approved Clang SHA-256}"
: "${MIBR_LLD_SHA256:?MISSING_TOOLCHAIN_PIN: set the approved LLD SHA-256}"
: "${MIBR_FFMPEG_SHA256:?MISSING_TOOLCHAIN_PIN: set the approved ffmpeg SHA-256}"
: "${RUNNER_TEMP:?MISSING_INPUT: RUNNER_TEMP must be set by GitHub Actions}"
: "${GITHUB_RUN_ID:?MISSING_INPUT: GITHUB_RUN_ID must be set by GitHub Actions}"
: "${GITHUB_RUN_ATTEMPT:?MISSING_INPUT: GITHUB_RUN_ATTEMPT must be set by GitHub Actions}"
: "${OUT:?MISSING_INPUT: set output directory}"
RUNNER_TEMP="$(cd "$RUNNER_TEMP" && pwd -P)"

command -v realpath >/dev/null || { echo 'REALPATH_MISSING' >&2; exit 19; }
ensure_private_path_outside_repo() {
  local resolved
  resolved="$(realpath -e "$1")" || { echo 'PRIVATE_INPUT_PATH_UNRESOLVABLE' >&2; exit 19; }
  case "$resolved" in "$ROOT_REAL"|"$ROOT_REAL"/*) echo 'PRIVATE_INPUT_INSIDE_CHECKOUT' >&2; exit 19 ;; esac
}
if [[ "$NEEDS_PRIVATE_J9" == 1 ]]; then
  ensure_private_path_outside_repo "$J9_HOME"
  ensure_private_path_outside_repo "$MIBR_PRIVATE_INPUT_ROOT"
else
  ensure_private_path_outside_repo "$MIBR_PREBUILT_EXTENDER_JAR"
fi
ensure_private_path_outside_repo "$QNX_TARGET"
ensure_private_path_outside_repo "$IAP2_LIB"
ensure_private_path_outside_repo "$CLANG"
ensure_private_path_outside_repo "$LLD"
ensure_private_path_outside_repo "$FFMPEG"

check_tool_hash() {
  local file="$1" expected="$2" actual
  actual="$(sha256sum "$file" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || { echo 'PINNED_TOOL_HASH_MISMATCH' >&2; exit 20; }
}
check_tool_hash "$CLANG" "$MIBR_CLANG_SHA256"
check_tool_hash "$LLD" "$MIBR_LLD_SHA256"
check_tool_hash "$FFMPEG" "$MIBR_FFMPEG_SHA256"
if [[ "$NEEDS_PRIVATE_J9" == 1 ]]; then
  for executable in "$J9_HOME/bin/javac" "$J9_HOME/bin/jar"; do
    [[ -x "$executable" ]] || { echo "J9_EXECUTABLE_MISSING=$executable" >&2; exit 21; }
  done
  check_tool_hash "$J9_HOME/bin/javac" "$MIBR_J9_JAVAC_SHA256"
  check_tool_hash "$J9_HOME/bin/jar" "$MIBR_J9_JAR_SHA256"
  [[ -d "$MIBR_PRIVATE_INPUT_ROOT" ]] || { echo 'PRIVATE_INPUT_ROOT_MISSING' >&2; exit 22; }
  [[ -s "$MIBR_PRIVATE_INPUT_ROOT/SHA256SUMS" ]] || { echo 'PRIVATE_INPUT_MANIFEST_MISSING' >&2; exit 21; }
  check_tool_hash "$MIBR_PRIVATE_INPUT_ROOT/SHA256SUMS" "$MIBR_PRIVATE_INPUT_MANIFEST_SHA256"
  (cd "$MIBR_PRIVATE_INPUT_ROOT" && sha256sum --check --strict SHA256SUMS >/dev/null) || {
    echo 'PRIVATE_INPUT_MANIFEST_MISMATCH' >&2; exit 22;
  }
  for profile in "${PROFILES[@]}"; do
    for filename in lsd.jar Activator.java WidgetFactoryImpl.java; do
      grep -Eq "^[0-9a-f]{64}  $profile/$filename$" "$MIBR_PRIVATE_INPUT_ROOT/SHA256SUMS" || {
        echo 'PRIVATE_INPUT_MANIFEST_INCOMPLETE' >&2; exit 22;
      }
      input="$MIBR_PRIVATE_INPUT_ROOT/$profile/$filename"
      [[ -f "$input" && -s "$input" && ! -L "$input" ]] || {
        echo 'PRIVATE_BUILD_INPUT_MISSING' >&2; exit 22;
      }
    done
  done
else
  [[ -f "$MIBR_PREBUILT_EXTENDER_JAR" && -s "$MIBR_PREBUILT_EXTENDER_JAR" &&
    ! -L "$MIBR_PREBUILT_EXTENDER_JAR" ]] || {
    echo 'PREBUILT_EXTENDER_MISSING_OR_SYMLINK' >&2; exit 22;
  }
  check_tool_hash "$MIBR_PREBUILT_EXTENDER_JAR" "$MIBR_PREBUILT_EXTENDER_SHA256"
fi
[[ -d "$QNX_TARGET/armle-v7" ]] || { echo 'PRIVATE_QNX_TARGET_MISSING' >&2; exit 23; }
[[ -s "$QNX_TARGET/MIBR_TARGET_SHA256SUMS" ]] || { echo 'PRIVATE_QNX_TARGET_MANIFEST_MISSING' >&2; exit 23; }
target_manifest_sha="$(sha256sum "$QNX_TARGET/MIBR_TARGET_SHA256SUMS" | awk '{print $1}')"
[[ "$target_manifest_sha" == "$MIBR_QNX_TARGET_MANIFEST_SHA256" ]] || {
  echo 'PRIVATE_QNX_TARGET_MANIFEST_PIN_MISMATCH' >&2
  exit 23
}
(cd "$QNX_TARGET" && sha256sum --check --strict MIBR_TARGET_SHA256SUMS >/dev/null) || {
  echo 'PRIVATE_QNX_TARGET_CONTENT_MISMATCH' >&2
  exit 23
}
[[ -x "$CLANG" && -x "$LLD" ]] || { echo 'ROUTE_GUIDANCE_TOOLCHAIN_MISSING' >&2; exit 24; }
[[ -f "$IAP2_LIB" && -s "$IAP2_LIB" && ! -L "$IAP2_LIB" ]] || { echo 'PRIVATE_IAP2_LIBRARY_MISSING' >&2; exit 25; }
command -v docker >/dev/null || { echo 'DOCKER_MISSING' >&2; exit 26; }
"$CLANG" --version >/dev/null
"$LLD" --version >/dev/null
"$FFMPEG" -hide_banner -encoders 2>/dev/null | grep -q 'libx264' || { echo 'FFMPEG_LIBX264_MISSING' >&2; exit 28; }

IMAGE=mhi2-qnx65-armv7-public:4.9
export IMAGE
bash "$ROOT/tools/ci_qnx65_image.sh"
QNX_PROVENANCE="$RUNNER_TEMP/qnx65-toolchain-provenance.txt"
[[ -s "$QNX_PROVENANCE" ]] || { echo 'QNX_IMAGE_PROVENANCE_MISSING' >&2; exit 29; }

expected_out="$RUNNER_TEMP/mibr-multiprofile-beta-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
[[ "$OUT" == "$expected_out" ]] || { echo 'OUTPUT_PATH_NOT_RUN_SCOPED' >&2; exit 32; }
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'OUTPUT_PATH_EXISTS_REFUSING_STALE_OUTPUT' >&2; exit 32; }
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd -P)"
case "$OUT/" in "$RUNNER_TEMP"/*/) ;; *) echo 'OUTPUT_PATH_OUTSIDE_RUNNER_TEMP' >&2; exit 32 ;; esac
mkdir -p "$OUT/hmi"
WORK="$OUT/work"
NATIVE="$OUT/native"
PRIVATE_LOG="$RUNNER_TEMP/.mibr-private-build-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT.log"
umask 077
: > "$PRIVATE_LOG"
mkdir -p "$NATIVE/bin"
cleanup() {
  case "$WORK" in "$OUT"/work) rm -rf -- "$WORK" ;; *) echo 'PRIVATE_WORK_CLEANUP_PATH_INVALID' >&2 ;; esac
}
trap cleanup EXIT

DOCKER_ARGS=(docker run --rm --platform=linux/amd64 -v "$ROOT:/src" -v "$OUT:/release-out" -w /src "$IMAGE")
"${DOCKER_ARGS[@]}" bash -lc 'QNX_CC=arm-unknown-nto-qnx6.5.0eabi-gcc bash tools/build_mu1440_source.sh /release-out/native/bin/mu1440-source'
"${DOCKER_ARGS[@]}" bash -lc 'QCC=arm-unknown-nto-qnx6.5.0eabi-gcc bash tools/build_altscreen111_gen2.sh /release-out/native/bin/gen2/libaltscreen111.so'
"${DOCKER_ARGS[@]}" bash -lc 'bash tools/build_support_tools.sh /release-out/native/bin/support-tools'
"${DOCKER_ARGS[@]}" bash -lc 'bash tools/build_direct_ts_remux.sh modules/carplay/source/direct-ts-remux/direct_ts_remux.c /release-out/native/bin/direct-ts-remux/direct-ts-remux'

if [[ "$MIBR_MENU_JAR_MODE" == "prebuilt" ]]; then
  # Reuse only hash-pinned reference JARs when every tracked public J9 input
  # is unchanged from their source baseline. Do not bypass the stale gate.
  python3 "$ROOT/tools/release/stage_prebuilt_menu.py" --out "$OUT/hmi"
  echo "PROFILE_MENU_MODE=PREBUILT_SOURCE_MATCH"
else
  for profile in "${PROFILES[@]}"; do
    private_profile="$MIBR_PRIVATE_INPUT_ROOT/$profile"
    lsd="$private_profile/lsd.jar"
    activator="$private_profile/Activator.java"
    widget_factory="$private_profile/WidgetFactoryImpl.java"
  
    profile_out="$WORK/$profile"
    mkdir -p "$profile_out"
    echo "HMI_BUILD_START profile=$profile source_commit=$(git -C "$ROOT" rev-parse HEAD)"
    if ! (
      cd "$ROOT"
      J9_HOME="$J9_HOME" \
        LSD_JAR="$lsd" \
        OEM_ACTIVATOR_SOURCE="$activator" \
        OEM_WIDGET_FACTORY_SOURCE="$widget_factory" \
        PROFILE="$profile" \
        OUT="$profile_out" \
        bash "$BUILD_SCRIPT"
    ) > "$profile_out/private-compiler.log" 2>&1; then
      cat "$profile_out/private-compiler.log" >> "$PRIVATE_LOG"
      echo "HMI_BUILD=FAIL profile=$profile; compiler details retained only on the restricted runner" >&2
      exit 1
    fi
  
    built="$profile_out/MIBR-HMI-CarPlay-Settings-Home.jar"
    [[ -s "$built" ]] || { echo "HMI_BUILD_OUTPUT_MISSING profile=$profile" >&2; exit 29; }
    python3 "$ROOT/modules/menu/source/verify_class_major.py" "$built" --major 46
    mkdir -p "$OUT/hmi/$profile"
    install -m 0644 "$built" "$OUT/hmi/$profile/MIBR-CarPlay.jar"
    sha256sum "$OUT/hmi/$profile/MIBR-CarPlay.jar"
    echo "HMI_BUILD=PASS profile=$profile class_major=46"
  done
  git -C "$ROOT" rev-parse HEAD > "$OUT/hmi/SOURCE_COMMIT.txt"
  echo "PROFILE_MENU_MODE=REBUILT_FROM_CURRENT_SOURCE"
fi

if [[ "$NEEDS_PRIVATE_J9" == 0 ]]; then
  mkdir -p "$OUT/hmi/common"
  install -m 0644 "$MIBR_PREBUILT_EXTENDER_JAR" "$OUT/hmi/common/MIBR-Extender-P1-BootProbe.jar"
  python3 -I "$ROOT/modules/menu/source/extender-p1/toolchain/verify_p1_jar.py" \
    "$OUT/hmi/common/MIBR-Extender-P1-BootProbe.jar"
  echo 'EXTENDER_MODE=PREBUILT_HASH_PINNED_SOURCE_BASELINE_CHECKED'
else
  skoda_lsd="$MIBR_PRIVATE_INPUT_ROOT/skoda-mu1440-p4526/lsd.jar"
  [[ -s "$skoda_lsd" ]] || { echo 'PRIVATE_SKODA_LSD_MISSING_FOR_EXTENDER' >&2; exit 30; }
  extender_out="$WORK/extender"
  mkdir -p "$extender_out"
  if ! (
    cd "$ROOT"
    J9_HOME="$J9_HOME" LSD_JAR="$skoda_lsd" SRC="$ROOT/modules/menu/source/extender-p1" \
      OUT="$extender_out" sh modules/menu/source/extender-p1/toolchain/build_p1.sh
  ) > "$extender_out/private-compiler.log" 2>&1; then
    cat "$extender_out/private-compiler.log" >> "$PRIVATE_LOG"
    echo 'EXTENDER_BUILD=FAIL; compiler details retained only on the restricted runner' >&2
    exit 1
  fi
  extender_jar="$extender_out/MIBR-Extender-P1-BootProbe.jar"
  [[ -s "$extender_jar" ]] || { echo 'EXTENDER_BUILD_OUTPUT_MISSING' >&2; exit 31; }
  python3 -I "$ROOT/modules/menu/source/extender-p1/toolchain/verify_p1_jar.py" "$extender_jar"
  mkdir -p "$OUT/hmi/common"
  install -m 0644 "$extender_jar" "$OUT/hmi/common/MIBR-Extender-P1-BootProbe.jar"
  echo 'EXTENDER_MODE=J9_REBUILT'
fi

NATIVE="$OUT/native"
mkdir -p "$NATIVE/bin/navigation"
QNX_TARGET="$QNX_TARGET" IAP2_LIB="$IAP2_LIB" CLANG="$CLANG" LLD="$LLD" \
  sh "$ROOT/modules/navigation/source/build.sh" "$NATIVE/bin/navigation"
ffmpeg -hide_banner -loglevel error -y -version >/dev/null
python3 "$ROOT/modules/navigation/source/tools/make_calib_clip.py" \
  "$NATIVE/bin/navigation/mibr-calib.avcc" "$FFMPEG"
(cd "$NATIVE" && find bin -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
(cd "$NATIVE" && sha256sum --check --strict SHA256SUMS >/dev/null) || {
  echo 'NATIVE_OUTPUT_MANIFEST_VERIFY_FAIL' >&2
  exit 33
}

git -C "$ROOT" rev-parse HEAD > "$NATIVE/SOURCE_COMMIT.txt"
{
  echo 'QNX native compiler image provenance:'
  cat "$QNX_PROVENANCE"
  echo 'Navigation compiler versions:'
  "$CLANG" --version | head -n 1
  "$LLD" --version | head -n 1
  echo "qnx_target_manifest_sha256=$target_manifest_sha"
  echo "ffmpeg_sha256=$MIBR_FFMPEG_SHA256"
} > "$NATIVE/COMPILER.txt"
{
  echo 'QNX image reference:'
  cat "$ROOT/tools/qnx65-image.lock"
  echo 'QNX image provenance:'
  cat "$QNX_PROVENANCE"
  echo 'Navigation IAP2 input identity:'
  sha256sum "$IAP2_LIB" | awk '{print $1}'
} > "$NATIVE/IMAGE_SOURCE.txt"

# Container builds run as root. Restore ownership before assembling or uploading.
if [[ "$(id -u)" != 0 ]]; then
  command -v sudo >/dev/null || { echo "OUTPUT_OWNERSHIP_REQUIRES_SUDO" >&2; exit 33; }
  sudo -n chown -R "$(id -u):$(id -g)" "$OUT" || { echo "OUTPUT_OWNERSHIP_FAILED" >&2; exit 33; }
fi

# build_modular performs native SHA256SUMS, commit existence and input-freshness
# checks. Deliberately do not pass --allow-stale or --allow-dirty.
python3 "$ROOT/tools/release/build_modular.py" \
  --repo "$ROOT" \
  --native-dir "$NATIVE" \
  --hmi-dir "$OUT/hmi" \
  --out "$OUT/MIBR-CarPlay-three-profile-beta.zip" \
  --require-complete
python3 "$ROOT/tools/validate_modular_package.py" \
  --require-complete "$OUT/MIBR-CarPlay-three-profile-beta.zip"
sha256sum "$OUT/MIBR-CarPlay-three-profile-beta.zip" \
  > "$OUT/MIBR-CarPlay-three-profile-beta.zip.sha256"
(cd "$OUT" && sha256sum --check --strict MIBR-CarPlay-three-profile-beta.zip.sha256 >/dev/null)
echo "MULTIPROFILE_BETA_PACKAGE=PASS menu_mode=$MIBR_MENU_JAR_MODE source_commit=$(git -C "$ROOT" rev-parse HEAD)"
