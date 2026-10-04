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
cp "$ROOT/deployment/mu1440-framing-v1/collect-logs.sh" "$DEST/collect-logs.sh"
cp "$GEN2" "$DEST/payload/libaltscreen111.so"
cp "$REMUX" "$DEST/payload/direct-ts-remux"
cp "$SHAHELP" "$DEST/payload/sha256sum"
cp "$ROOT/deployment/mu1440-framing-v1/common.sh" "$DEST/runtime/auto-direct/common.sh"

for f in   direct_fps.sh direct_source_mode.sh direct_autodirect.sh gen2_video.sh   direct_ts_auto_supervisor.sh direct_ts_auto_status.sh   direct_ts_auto_start.sh direct_ts_auto_watchdog.sh   direct_ts_auto_enable.sh direct_ts_auto_disable.sh
do
  cp "$ROOT/runtime/auto-direct/$f" "$DEST/runtime/auto-direct/$f"
done

for f in gen2_nav_config.sh gen2_url.sh gen2_ui_urls.sh gen2_viewareas.sh gen2_safearea.sh; do
  cp "$ROOT/runtime/navigation/$f" "$DEST/runtime/navigation/$f"
done

for f in gen2_keyframes.sh gen2_sourceversion.sh gen2_display.sh gen2_enabled.sh; do
  cp "$ROOT/runtime/diagnostics/$f" "$DEST/runtime/diagnostics/$f"
done

cp "$ROOT/runtime/experimental/viewarea_mode.sh" "$DEST/runtime/experimental/viewarea_mode.sh"

chmod +x "$DEST/"*.sh "$DEST/payload/"*   "$DEST/runtime/auto-direct/"*.sh   "$DEST/runtime/navigation/"*.sh   "$DEST/runtime/diagnostics/"*.sh   "$DEST/runtime/experimental/"*.sh

(
  cd "$DEST"
  sha256sum     payload/libaltscreen111.so     payload/direct-ts-remux     payload/sha256sum     collect-logs.sh     runtime/auto-direct/common.sh     runtime/auto-direct/direct_fps.sh     runtime/auto-direct/direct_source_mode.sh     runtime/auto-direct/direct_autodirect.sh     runtime/auto-direct/gen2_video.sh     runtime/auto-direct/direct_ts_auto_supervisor.sh     runtime/auto-direct/direct_ts_auto_status.sh     runtime/auto-direct/direct_ts_auto_start.sh     runtime/auto-direct/direct_ts_auto_watchdog.sh     runtime/auto-direct/direct_ts_auto_enable.sh     runtime/auto-direct/direct_ts_auto_disable.sh     runtime/navigation/gen2_nav_config.sh     runtime/navigation/gen2_url.sh     runtime/navigation/gen2_ui_urls.sh     runtime/navigation/gen2_viewareas.sh     runtime/navigation/gen2_safearea.sh     runtime/diagnostics/gen2_keyframes.sh     runtime/diagnostics/gen2_sourceversion.sh     runtime/diagnostics/gen2_display.sh     runtime/diagnostics/gen2_enabled.sh     runtime/experimental/viewarea_mode.sh     > PAYLOAD.sha256
)

GEN2_SHA=$(sha256sum "$GEN2" | awk '{print $1}')
REMUX_SHA=$(sha256sum "$REMUX" | awk '{print $1}')
SOURCE_HEAD_COMMIT_VALUE=${SOURCE_HEAD_COMMIT:-${GITHUB_SHA:-local}}
CI_MERGE_COMMIT_VALUE=${CI_MERGE_COMMIT:-}

cat > "$DEST/CANDIDATE-MANIFEST.txt" <<EOF
candidate=classic111-runtime-contract-v1
target=MHI2_ER_SKG13_P4526_MU1440
cluster=AID10-class
source_head_commit=$SOURCE_HEAD_COMMIT_VALUE
gen2_sha256=$GEN2_SHA
direct_ts_remux_sha256=$REMUX_SHA
runtime_config_precedence=/tmp_then_/mnt/app/root_then_default
altscreen_enabled_default=1
autodirect_default=1
fps_default=30
fps_values=20,25,30,40
fps_config_name=mibr-carplay111-fps
framing_default=raw
framing_config_name=mibr-carplay111-framing
video_default=pace:1,pace_buffer:3
video_config_name=mibr-carplay111-video.conf
source_version_default=1005.8.1
source_version_config_name=mibr-carplay111-sourceversion
raw_url_default=auto
raw_url_config_name=mibr-carplay111-url
ui_urls_default=base,map,instructioncard
ui_urls_config_name=mibr-carplay111-ui-urls.conf
nav_default=query:0,surface:base,showETA:yes,showSpeedLimit:user,showCompass:user,maneuverLayout:none
nav_config_name=mibr-carplay111-nav.conf
display_default=1010x376,200x74
display_config_name=mibr-carplay111-display.conf
viewareas_default=count:2,initial:0,transition_ms:0
viewarea0_default=area:0,0,1010,376,safe:0,0,1010,376
viewarea1_default=area:0,0,1010,376,safe:0,58,1010,248
viewareas_config_name=mibr-carplay111-viewareas.conf
keyframe_default=enabled:1,event_delay_ms:250,min_gap_ms:1000,watchdog_ms:1000
keyframe_config_name=mibr-carplay111-keyframes.conf
transport_default=raw-annexb
transport_optional=m1au-v1
m1au_header_bytes=56
m1au_timestamp_bytes=8_raw_uninterpreted
source_arrival_timing=clock_monotonic
pts_pcr=unchanged_cfr
apply_live=keyframes,viewarea_select
apply_presentation=url,nav
apply_bridge=framing,video
apply_reconnect=enabled,fps,sourceversion,ui_urls,display,viewarea_definition
media_scope=excluded
ultra_scope=excluded
install_type=reversible_overlay
runtime_log_root=/tmp/mibr-altscreen-logs
sd_log_export=/net/mmx/fs/sda0/esd/carplay-test/logs/classic111
sd_write_bootstrap=apps/mounts_-usb_plus_write_test
EOF

if [[ -n "$CI_MERGE_COMMIT_VALUE" ]]; then
  echo "ci_merge_commit=$CI_MERGE_COMMIT_VALUE" >> "$DEST/CANDIDATE-MANIFEST.txt"
fi

cat > "$DEST/README-FIRST.txt" <<'EOF'
MHI2 AltScreen — MU1440 Classic Type-111 runtime-contract vehicle candidate
===========================================================================

Exact target:
  MHI2_ER_SKG13_P4526_MU1440
  AID10-class Virtual Cockpit

Configuration precedence:
  /tmp/<name>          temporary override, highest priority, lost on reboot
  /mnt/app/root/<name> persistent override
  neither              compiled/configured default

Tomorrow's baseline:
  AltScreen master: 1
  Auto-Direct: 1
  FPS: 30 (advertised maxFPS + direct output pacing)
  framing: raw Annex-B
  video pacing: pace=1, pace_buffer=3
  sourceVersion: 1005.8.1
  raw URL: auto
  navigation: base URL, query off
  two ViewAreas:
    0 MAP_FULL      SafeArea 0,0,1010,376
    1 GAUGE_REDUCED SafeArea 0,58,1010,248
  D2 keyframe recovery: enabled, delay 250 ms, min gap 1000 ms, watchdog 1000 ms
  PTS/PCR: CFR unchanged

Apply classes:
  live          keyframe policy; select already-advertised ViewArea
  presentation  raw URL/nav: bounded stopUI -> showUI -> forceKeyFrame
  bridge        framing/video pacing
  reconnect     master/FPS/sourceVersion/UI URL list/display/ViewArea definitions

Do NOT hard-restart smartphone_integrator/dio_manager to apply reconnect-class values.
Disconnect/reconnect CarPlay so the next negotiation reads the new values.

Source timing:
  GEN2 measures actual Stream-111 arrival cadence with CLOCK_MONOTONIC.
  M1AU v1 preserves the exact 8 raw Stream-111 timestamp bytes per AU.
  Those timestamp bytes intentionally do NOT drive PTS/PCR yet.

Media/Now Playing, Ultra/NextGen, PassengerDisplay, GaugeCluster, HEVC,
Enhanced Siri, bit26, bit37, HID/input and appearance experiments are excluded.

Runtime evidence:
  live logs/status remain in /tmp while the projection path is running.
  Nothing in the running runtime remounts SD writable for logging.
  Export evidence explicitly with:
    ksh ./collect-logs.sh
  The collector uses the existing M.I.B./U2 apps/mounts -usb helper,
  performs a real SD write test, then copies the /tmp evidence into:
    /net/mmx/fs/sda0/esd/carplay-test/logs/classic111/<timestamp>/

Install:
  ksh ./install.sh --check
  ksh ./install.sh --apply
  sync; sync; sync; on -f rcc /usr/apps/mib2_ioc_flash reboot
  ksh ./status.sh

Rollback:
  ksh ./uninstall.sh
  sync; sync; sync; on -f rcc /usr/apps/mib2_ioc_flash reboot
EOF

(
  cd "$DEST"
  sha256sum $(find . -type f ! -name PACKAGE-SHA256SUMS.txt -print | sort) > PACKAGE-SHA256SUMS.txt
)

echo "prepared Classic Type-111 runtime-contract overlay: $DEST"
echo "GEN2: $GEN2_SHA"
echo "REMUX: $REMUX_SHA"
