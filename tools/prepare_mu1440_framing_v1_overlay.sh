#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-}"
GEN2="${2:-build/framing-v1/libaltscreen111.so}"
REMUX="${3:-build/framing-v1/direct-ts-remux}"

if [[ -z "$DEST" ]]; then
  echo "usage: $0 DEST [GEN2_BINARY] [REMUX_BINARY]"
  exit 2
fi

SHAHELP="$ROOT/artifacts/mu1440/sha256sum-compat/build-confirmed-current/sha256sum"

for f in "$GEN2" "$REMUX" "$SHAHELP"; do
  [[ -f "$f" ]] || { echo "missing required file: $f"; exit 10; }
done

rm -rf "$DEST"
mkdir -p "$DEST/payload" "$DEST/runtime/auto-direct" "$DEST/runtime/navigation" "$DEST/runtime/diagnostics"

cp "$ROOT/deployment/mu1440-framing-v1/install.sh" "$DEST/install.sh"
cp "$ROOT/deployment/mu1440-framing-v1/uninstall.sh" "$DEST/uninstall.sh"
cp "$ROOT/deployment/mu1440-framing-v1/status.sh" "$DEST/status.sh"
cp "$GEN2" "$DEST/payload/libaltscreen111.so"
cp "$REMUX" "$DEST/payload/direct-ts-remux"
cp "$SHAHELP" "$DEST/payload/sha256sum"

for f in common.sh direct_fps.sh direct_source_mode.sh direct_ts_auto_supervisor.sh direct_ts_auto_status.sh; do
  cp "$ROOT/runtime/auto-direct/$f" "$DEST/runtime/auto-direct/$f"
done
cp "$ROOT/runtime/navigation/gen2_safearea.sh" "$DEST/runtime/navigation/gen2_safearea.sh"
cp "$ROOT/runtime/diagnostics/gen2_keyframes.sh" "$DEST/runtime/diagnostics/gen2_keyframes.sh"

chmod +x "$DEST/"*.sh "$DEST/payload/"* "$DEST/runtime/auto-direct/"*.sh "$DEST/runtime/navigation/"*.sh "$DEST/runtime/diagnostics/"*.sh

(
  cd "$DEST"
  sha256sum     payload/libaltscreen111.so     payload/direct-ts-remux     payload/sha256sum     runtime/auto-direct/common.sh     runtime/auto-direct/direct_fps.sh     runtime/auto-direct/direct_source_mode.sh     runtime/auto-direct/direct_ts_auto_supervisor.sh     runtime/auto-direct/direct_ts_auto_status.sh     runtime/navigation/gen2_safearea.sh     runtime/diagnostics/gen2_keyframes.sh     > PAYLOAD.sha256
)

GEN2_SHA=$(sha256sum "$GEN2" | awk '{print $1}')
REMUX_SHA=$(sha256sum "$REMUX" | awk '{print $1}')
SOURCE_HEAD_COMMIT_VALUE=${SOURCE_HEAD_COMMIT:-${GITHUB_SHA:-local}}
CI_MERGE_COMMIT_VALUE=${CI_MERGE_COMMIT:-}
cat > "$DEST/CANDIDATE-MANIFEST.txt" <<EOF
candidate=framing-v1
target=MHI2_ER_SKG13_P4526_MU1440
cluster=AID10-class
source_head_commit=$SOURCE_HEAD_COMMIT_VALUE
gen2_sha256=$GEN2_SHA
direct_ts_remux_sha256=$REMUX_SHA
source_fps_default=30
source_fps_diagnostic=40
source_version_default=1005.8.1
source_version_override=/mnt/app/root/mibr-carplay111-sourceversion
keyframe_timing_default=250,1000,1000
keyframe_timing_control=/mnt/app/root/mibr-carplay111-keyframes.conf
transport_default=raw-annexb
transport_optional=m1au-v1
m1au_header_bytes=56
m1au_timestamp_bytes=8_raw_uninterpreted
pts_pcr=unchanged_cfr
safearea_helper=included
install_type=reversible_overlay
EOF

if [[ -n "$CI_MERGE_COMMIT_VALUE" ]]; then
  echo "ci_merge_commit=$CI_MERGE_COMMIT_VALUE" >> "$DEST/CANDIDATE-MANIFEST.txt"
fi

cat > "$DEST/README-FIRST.txt" <<'EOF'
MHI2 AltScreen — MU1440 framing-v1 candidate overlay
=====================================================

Exact target:
  MHI2_ER_SKG13_P4526_MU1440
  AID10-class Virtual Cockpit

Prerequisite:
  the current MU1440 developer deployment must already be installed and active.

This is NOT the stable release. It replaces only the GEN2 hook, direct-ts-remux and the runtime
helpers needed for source-timing/framing tests. It creates an internal backup before mutation and
can restore that exact pre-candidate state.

Defaults after install:
  source maxFPS: 30
  direct output: 30
  sourceVersion compatibility persona: 1005.8.1
  D2 timing: event delay 250 ms / minimum request gap 1000 ms / watchdog 1000 ms
  local transport: raw Annex-B
  PTS/PCR: existing CFR path

Optional:
  /mnt/app/root/altscreen-u2/scripts/direct_source_mode.sh m1au
  /mnt/app/root/altscreen-u2/scripts/direct_fps.sh 40
  /mnt/app/root/altscreen-u2/scripts/gen2_keyframes.sh timing 250 1000 1000
  /mnt/app/root/altscreen-u2/scripts/gen2_keyframes.sh timing 250 1000 0
  /mnt/app/root/altscreen-u2/scripts/gen2_safearea.sh status

sourceVersion diagnostics:
  no override file                                      -> 1005.8.1
  echo stock   > /mnt/app/root/mibr-carplay111-sourceversion -> preserve stock 210.81
  echo 950.7.1 > /mnt/app/root/mibr-carplay111-sourceversion -> historical compatibility persona
  echo 1005.8.1 > /mnt/app/root/mibr-carplay111-sourceversion -> current development persona
  reconnect CarPlay after changing sourceVersion so a fresh /info negotiation is used

M1AU v1 preserves per-AU stream/codec/consumer generations, sequence/IDR metadata and the exact
eight raw Stream-111 timestamp bytes. Framing-v1 does NOT yet use those bytes for PTS/PCR.

Install:
  ./install.sh --check
  ./install.sh --apply
  reboot
  ./status.sh

Switch transport after reboot:
  /mnt/app/root/altscreen-u2/scripts/direct_source_mode.sh raw
  /mnt/app/root/altscreen-u2/scripts/direct_source_mode.sh m1au
  /mnt/app/root/altscreen-u2/scripts/direct_source_mode.sh status

FPS:
  /mnt/app/root/altscreen-u2/scripts/direct_fps.sh 30
  /mnt/app/root/altscreen-u2/scripts/direct_fps.sh 40
  reconnect CarPlay after changing source maxFPS

Rollback:
  ./uninstall.sh
  reboot

The rollback retains /mnt/app/root/mibr-framing-v1-backup for recovery/evidence.
EOF

(
  cd "$DEST"
  sha256sum $(find . -type f ! -name PACKAGE-SHA256SUMS.txt -print | sort) > PACKAGE-SHA256SUMS.txt
)

echo "prepared framing-v1 overlay: $DEST"
echo "GEN2: $GEN2_SHA"
echo "REMUX: $REMUX_SHA"
