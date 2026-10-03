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
mkdir -p "$DEST/payload" "$DEST/runtime/auto-direct" "$DEST/runtime/navigation" "$DEST/runtime/diagnostics" "$DEST/runtime/experimental"

cp "$ROOT/deployment/mu1440-framing-v1/install.sh" "$DEST/install.sh"
cp "$ROOT/deployment/mu1440-framing-v1/uninstall.sh" "$DEST/uninstall.sh"
cp "$ROOT/deployment/mu1440-framing-v1/status.sh" "$DEST/status.sh"
cp "$GEN2" "$DEST/payload/libaltscreen111.so"
cp "$REMUX" "$DEST/payload/direct-ts-remux"
cp "$SHAHELP" "$DEST/payload/sha256sum"

for f in common.sh direct_fps.sh direct_source_mode.sh direct_ts_auto_supervisor.sh direct_ts_auto_status.sh direct_ts_auto_start.sh direct_ts_auto_watchdog.sh direct_ts_auto_enable.sh direct_ts_auto_disable.sh; do
  cp "$ROOT/runtime/auto-direct/$f" "$DEST/runtime/auto-direct/$f"
done
cp "$ROOT/runtime/navigation/gen2_safearea.sh" "$DEST/runtime/navigation/gen2_safearea.sh"
cp "$ROOT/runtime/navigation/gen2_nav_config.sh" "$DEST/runtime/navigation/gen2_nav_config.sh"
cp "$ROOT/runtime/diagnostics/gen2_keyframes.sh" "$DEST/runtime/diagnostics/gen2_keyframes.sh"
cp "$ROOT/runtime/diagnostics/gen2_sourceversion.sh" "$DEST/runtime/diagnostics/gen2_sourceversion.sh"
cp "$ROOT/runtime/experimental/viewarea_mode.sh" "$DEST/runtime/experimental/viewarea_mode.sh"

chmod +x "$DEST/"*.sh "$DEST/payload/"* "$DEST/runtime/auto-direct/"*.sh "$DEST/runtime/navigation/"*.sh "$DEST/runtime/diagnostics/"*.sh "$DEST/runtime/experimental/"*.sh

(
  cd "$DEST"
  sha256sum \
    payload/libaltscreen111.so \
    payload/direct-ts-remux \
    payload/sha256sum \
    runtime/auto-direct/common.sh \
    runtime/auto-direct/direct_fps.sh \
    runtime/auto-direct/direct_source_mode.sh \
    runtime/auto-direct/direct_ts_auto_supervisor.sh \
    runtime/auto-direct/direct_ts_auto_status.sh \
    runtime/auto-direct/direct_ts_auto_start.sh \
    runtime/auto-direct/direct_ts_auto_watchdog.sh \
    runtime/auto-direct/direct_ts_auto_enable.sh \
    runtime/auto-direct/direct_ts_auto_disable.sh \
    runtime/navigation/gen2_safearea.sh \
    runtime/navigation/gen2_nav_config.sh \
    runtime/diagnostics/gen2_keyframes.sh \
    runtime/diagnostics/gen2_sourceversion.sh \
    runtime/experimental/viewarea_mode.sh     > PAYLOAD.sha256
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
runtime_config_precedence=/tmp_then_/mnt/app/root_then_default
fps_default=30
fps_values=20,25,30,40
fps_config_name=mibr-carplay111-fps
source_version_default=1005.8.1
source_version_config_name=mibr-carplay111-sourceversion
keyframe_default=enabled:1,event_delay_ms:250,min_gap_ms:1000,watchdog_ms:1000
keyframe_config_name=mibr-carplay111-keyframes.conf
framing_default=raw
framing_config_name=mibr-carplay111-framing
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

Runtime configuration contract:
  /tmp/<name>          = temporary override (highest priority, lost on reboot)
  /mnt/app/root/<name> = persistent override
  neither              = compiled/config default

The basename is identical in both layers.

Reference defaults:
  Auto-Direct: 1
  FPS source+direct output: 30
  framing: raw Annex-B
  sourceVersion: 1005.8.1
  ViewAreas: 1
  SafeArea: full 1010x376
  D2: enabled=1, event_delay_ms=250, min_gap_ms=1000, watchdog_ms=1000
  nav query: 0; surface=base; ETA=yes; speed=user; compass=user; maneuver=none
  PTS/PCR: existing CFR path

Safe temporary tests:
  direct_fps.sh 20
  direct_source_mode.sh m1au
  gen2_keyframes.sh off
  gen2_keyframes.sh timing 250 2000 0
  gen2_sourceversion.sh 950.7.1
  gen2_nav_config.sh use-temp map-clean
  gen2_safearea.sh set 0 58 1010 248
  viewarea_mode.sh off

Persistent variants use the explicit "persist" / "persist-profile" commands.

Install:
  ./install.sh --check
  ./install.sh --apply
  reboot
  ./status.sh

Rollback:
  ./uninstall.sh
  reboot

M1AU v1 preserves the exact eight raw Stream-111 timestamp bytes. They do not yet drive PTS/PCR.
Bit26, the old url-map marker and autoshow.disabled are not part of the active runtime contract.
EOF

(
  cd "$DEST"
  sha256sum $(find . -type f ! -name PACKAGE-SHA256SUMS.txt -print | sort) > PACKAGE-SHA256SUMS.txt
)

echo "prepared framing-v1 overlay: $DEST"
echo "GEN2: $GEN2_SHA"
echo "REMUX: $REMUX_SHA"
