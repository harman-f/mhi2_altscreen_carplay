#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-}"
GEN2="${2:-build/mu1440-parity-drive/libaltscreen111.so}"
BRIDGE="${3:-build/mu1440-parity-drive/direct-ts-parity}"
SESSION="${4:-build/mu1440-parity-drive/parity-session}"
SETTINGS="${5:-$(dirname "$GEN2")/alt111-settings}"
GUARD="${6:-$(dirname "$GEN2")/libmibr_isotx2_guard.so}"

if [[ -z "$DEST" ]]; then
  echo "usage: $0 DEST [GEN2_BINARY] [PARITY_BRIDGE] [PARITY_SESSION]"
  exit 2
fi

SHAHELP="$ROOT/artifacts/mu1440/sha256sum-compat/build-confirmed-current/sha256sum"
for f in "$GEN2" "$BRIDGE" "$SESSION" "$SETTINGS" "$GUARD" "$SHAHELP"; do
  [[ -f "$f" ]] || { echo "missing required file: $f"; exit 10; }
done

[[ ! -e "$DEST" ]] || { echo "refusing to overwrite an existing candidate: $DEST"; exit 11; }
mkdir -p "$DEST/payload" "$DEST/runtime"

for f in install.sh uninstall.sh status.sh collect-logs.sh vehicle-install.sh vehicle-rollback.sh; do
  cp "$ROOT/deployment/mu1440-parity-drive-v1/$f" "$DEST/$f"
done

cp "$GEN2" "$DEST/payload/libaltscreen111.so"
cp "$BRIDGE" "$DEST/payload/direct-ts-parity"
cp "$SESSION" "$DEST/payload/parity-session"
cp "$SETTINGS" "$DEST/payload/alt111-settings"
cp "$GUARD" "$DEST/payload/libmibr_isotx2_guard.so"
cp "$SHAHELP" "$DEST/payload/sha256sum"

cp "$ROOT/deployment/mu1440-parity-drive-v1/session-logging.sh" "$DEST/runtime/session-logging.sh"
cp "$ROOT/deployment/mu1440-parity-drive-v1/package-logging.sh" "$DEST/runtime/package-logging.sh"
cp "$ROOT/runtime/parity/parity_profile.sh" "$DEST/runtime/parity_profile.sh"
cp "$ROOT/runtime/parity/parity_session.sh" "$DEST/runtime/parity_session.sh"
cp "$ROOT/runtime/parity/parity_status.sh" "$DEST/runtime/parity_status.sh"
cp "$ROOT/runtime/parity/parity_drive_supervisor.sh" "$DEST/runtime/parity_drive_supervisor.sh"
cp "$ROOT/runtime/parity/parity_drive_enable.sh" "$DEST/runtime/parity_drive_enable.sh"
cp "$ROOT/runtime/parity/parity_drive_disable.sh" "$DEST/runtime/parity_drive_disable.sh"
cp "$ROOT/runtime/parity/parity_drive_status.sh" "$DEST/runtime/parity_drive_status.sh"
cp "$ROOT/runtime/diagnostics/gen2_compat_profile.sh" "$DEST/runtime/gen2_compat_profile.sh"
cp "$ROOT/runtime/master/master_settings.sh" "$DEST/runtime/master_settings.sh"
cp "$ROOT/runtime/master/direct_fps.sh" "$DEST/runtime/direct_fps.sh"
cp "$ROOT/runtime/master/gen2_sourceversion.sh" "$DEST/runtime/gen2_sourceversion.sh"
cp "$ROOT/runtime/master/gen2_enabled.sh" "$DEST/runtime/gen2_enabled.sh"
cp "$ROOT/runtime/master/gen2_display.sh" "$DEST/runtime/gen2_display.sh"
cp "$ROOT/runtime/master/gen2_keyframes.sh" "$DEST/runtime/gen2_keyframes.sh"
cp "$ROOT/runtime/master/gen2_viewareas.sh" "$DEST/runtime/gen2_viewareas.sh"
cp "$ROOT/runtime/master/gen2_safearea.sh" "$DEST/runtime/gen2_safearea.sh"
cp "$ROOT/runtime/master/gen2_nav_config.sh" "$DEST/runtime/gen2_nav_config.sh"
cp "$ROOT/runtime/master/gen2_url.sh" "$DEST/runtime/gen2_url.sh"
cp "$ROOT/runtime/master/gen2_ui_urls.sh" "$DEST/runtime/gen2_ui_urls.sh"
cp "$ROOT/runtime/parity/master-script-basenames.sh" "$DEST/runtime/master-script-basenames.sh"
cp "$ROOT/settings/runtime-basenames.generated.sh" "$DEST/runtime/settings-basenames.sh"
cp "$ROOT/settings/hmi-bindings.generated.json" "$DEST/HMI-BINDINGS.json"

chmod +x "$DEST/"*.sh "$DEST/payload/"* "$DEST/runtime/"*.sh

(
  cd "$DEST"
  sha256sum     payload/libaltscreen111.so     payload/direct-ts-parity     payload/parity-session     payload/alt111-settings     payload/libmibr_isotx2_guard.so     payload/sha256sum     install.sh     uninstall.sh     status.sh     collect-logs.sh     vehicle-install.sh     vehicle-rollback.sh     runtime/parity_profile.sh     runtime/parity_session.sh     runtime/parity_status.sh     runtime/parity_drive_supervisor.sh     runtime/parity_drive_enable.sh     runtime/parity_drive_disable.sh     runtime/parity_drive_status.sh     runtime/gen2_compat_profile.sh     runtime/settings-basenames.sh     runtime/session-logging.sh     runtime/package-logging.sh     runtime/master-script-basenames.sh     runtime/master_settings.sh runtime/direct_fps.sh runtime/gen2_sourceversion.sh runtime/gen2_enabled.sh runtime/gen2_display.sh runtime/gen2_keyframes.sh runtime/gen2_viewareas.sh runtime/gen2_safearea.sh runtime/gen2_nav_config.sh runtime/gen2_url.sh runtime/gen2_ui_urls.sh     HMI-BINDINGS.json     > PAYLOAD.sha256
)

GEN2_SHA=$(sha256sum "$GEN2" | awk '{print $1}')
BRIDGE_SHA=$(sha256sum "$BRIDGE" | awk '{print $1}')
SESSION_SHA=$(sha256sum "$SESSION" | awk '{print $1}')
SOURCE_HEAD_COMMIT_VALUE=${SOURCE_HEAD_COMMIT:-${GITHUB_SHA:-local}}
CI_MERGE_COMMIT_VALUE=${CI_MERGE_COMMIT:-}

cat > "$DEST/CANDIDATE-MANIFEST.txt" <<EOF
candidate=mu1440-parity-drive-v1
target=MHI2_ER_SKG13_P4526_MU1440
cluster=AID10-class
source_head_commit=$SOURCE_HEAD_COMMIT_VALUE
gen2_sha256=$GEN2_SHA
direct_ts_parity_sha256=$BRIDGE_SHA
parity_session_sha256=$SESSION_SHA
alt111_settings_sha256=$(sha256sum "$SETTINGS" | awk '{print $1}')
native_guard_sha256=$(sha256sum "$GUARD" | awk '{print $1}')
native_guard_process=displaymanager
ownership_initial=writev_gate
dmdt_reference=probe_only_no_custom_payload_until_independent_target_proof
required_base_gen2_sha256=8cccf1cb1764952acd973cbb4f881cfd70f3312e7f6a29cdef7fec930c83d25c
accepted_vehicle_current_base_gen2_sha256=0406c607ef4e3b32a9b793cc83a7baffd7228437d18fd4671a464c2bf74439ac
base_gen2_hook_rule=hook_sha_must_equal_active_gen2_sha
required_base_remux_sha256=3f0e730523bd290608dc13e186baa962eeb9c46f117d4d4976be523c0cd94c09
required_base_gate_sha256=05673010a88c25022145ffb4e75d3715eaf686f4127ac188e91a52f512b9d957
required_libairplay_sha256=193a4fd9101ec2aa05e7159cfa307b96500810d379ca74a194f172adc13a46b5
install_type=reversible_overlay_over_envfix2
legacy_direct_ts_remux=unchanged
legacy_autodirect_persistent_during_candidate=0
parity_profile_recommended_layer=temp
profile_sourceversion=950.7.1
profile_type=111
profile_maxfps=40
profile_geometry=1010x376
profile_physical_mm=202x75
profile_features=10
profile_primary_input=3
profile_initial_url=maps:/car/instrumentcluster/map
profile_viewarea=1010x376@0,0
profile_safearea=606x344@202,16
profile_keyframe_policy=source_frames_20_legacy_timer_removed
input=m1au_complete_au
source_clock=stream111_32.32
pts_clock=source_derived_90khz
frame_pacer=none
transport_pacer=qnx_device_backpressure_regular_file_absolute
device_transport_late_fatal=disabled_vehicle_qualified
regular_file_transport_late_limit_us=40000
write_timeout_us=500000
pts_emission_guard=complete_pes_budget_plus_margin
profile_persistence=disabled
rollback_backups=retained_hash_verified
transport_bps=12288000
pat_pid=0x0000
pmt_pid=0x0010
pcr_pid=0x1000
video_pid=0x0011
pat_pmt_interval_packets=327
pcr_interval_packets=327
most_write_bytes=12032
device_open_mode=write_only_nonblock
ownership=validated_shared_settings_snapshot_writev_gate_initial
dmdt_timeout_ms=5000
session_watchdog_margin_seconds=20
session_until_stop_supported=1
drive_default_session_seconds=0
drive_sd_log_root=/net/mmx/fs/sda0/esd/carplay-test/logs/parity-drive
drive_sd_write_required=1
diagnostics_status_default=1
diagnostics_statistics_default=1
diagnostics_statistics_requires_status=1
reference_producer_payload_limit=262144
bridge_safety_payload_limit=3145728
recovery=au_pes_boundary_safe
reference_mid_pes_flush=deliberately_not_reproduced
navignore=existing_control_plane_substrate_not_part_of_media_parity
runtime_state=flat_tmp_files
sd_log_export=/net/mmx/fs/sda0/esd/carplay-test/logs/parity
EOF

if [[ -n "$CI_MERGE_COMMIT_VALUE" ]]; then
  echo "ci_merge_commit=$CI_MERGE_COMMIT_VALUE" >> "$DEST/CANDIDATE-MANIFEST.txt"
fi

cat > "$DEST/README-FIRST.txt" <<'EOF'
MHI2 AltScreen â€” MU1440 master candidate
========================================

Target: MHI2_ER_SKG13_P4526_MU1440 / AID10-class Virtual Cockpit.
This package is an offline build candidate until its exact hardware gates pass.
Draft harman-f/mhi2_altscreen_carplay#15 must remain unmerged.

The overlay requires the exact ENVFIX2 base hashes in CANDIDATE-MANIFEST.txt.
It backs up GEN2/hook, bridge, owner, shared settings helper, guard library,
runtime scripts, the DisplayManager boot script, persistent Auto-Direct state
and all 13 temporary configuration files, including exact ABSENT records.
The historical gate and direct-ts-remux bytes remain unchanged.

A normal IOC reboot loads the guard into DisplayManager, before the frozen gate,
and loads GEN2 into smartphone_integrator. The guard is a separate library;
GEN2 cannot observe DisplayManager's native writes from another process.
No live process restart is performed.

Use vehicle-install.sh / vehicle-rollback.sh for console + SD logs.
Each wrapper prepares SD write access and uses the bundled M.I.B. tee path;
logging bootstrap or logger failure prevents a successful result.

After reboot, before connecting CarPlay:
  ksh ./status.sh
  ksh /mnt/app/root/altscreen-u2/scripts/parity_profile.sh dual-temp

The dual preset advertises both areas. Keep selected area 0 for ownership/media
qualification. The reference one-area preset is available through 'temp'.
Preset application is one shared transaction and requires real CarPlay reconnect.
Connect CarPlay, open Maps/Waze, confirm Stream-111 streaming, then:
  ksh /mnt/app/root/altscreen-u2/scripts/parity_session.sh 60

For a guarded until-stop manual session:
  ksh /mnt/app/root/altscreen-u2/scripts/parity_session.sh 0

The native owner reads one validated backend snapshot. writev_gate is initial:
it requires current native FD tracking, completed in-flight writes and a new
positive suppression count for its own request token before opening the exec
barrier. It monitors this proof throughout the run. Driver queue/drain and
decoder behavior still require target qualification. Inherited descriptors,
fcntl aliases and direct resource-manager messages must be excluded by the
target ABI audit; tracked wrappers alone are not a universal ownership proof.

dmdt_reference executes the exact dc72/sc4-72 sequence and 500-ms pause as a
bounded routing probe. It NEVER starts custom payload in this candidate.
Its result is OWNERSHIP_UNPROVEN, followed by dc70-33/sc4-70 restore.
No automatic gate fallback or composed DMDT+gate comparison is provided.

Stop and explicit reconciliation:
  ksh /mnt/app/root/altscreen-u2/scripts/parity_session.sh stop
  ksh /mnt/app/root/altscreen-u2/scripts/parity_session.sh restore-stock

Guarded long-run/drive mode (optional, disabled until explicitly enabled):
  ksh /mnt/app/root/altscreen-u2/scripts/parity_drive_enable.sh
  ksh /mnt/app/root/altscreen-u2/scripts/parity_drive_status.sh
  ksh /mnt/app/root/altscreen-u2/scripts/parity_drive_disable.sh

Drive mode launches no stock-process restart. It waits for Stream-111, then
runs the same token-bound parity owner in until-stop mode and re-enters only
after a confirmed stock handback. The owner/watchdog remain fail-safe: bridge
exit, gate-proof loss, explicit token stop or supervisor failure restores stock.

Drive evidence is SD-only. The supervisor remounts
/net/mmx/fs/sda0 writable and verifies a real write before starting parity.
Logs are stored under:
  /net/mmx/fs/sda0/esd/carplay-test/logs/parity-drive/
The SD is synced periodically and remounted read-only on supervisor cleanup.

Raw status snapshots and compact one-second statistics are independently
switchable for future sessions:
  ksh /mnt/app/root/altscreen-u2/scripts/parity_drive_status.sh all-on persistent
  ksh /mnt/app/root/altscreen-u2/scripts/parity_drive_status.sh status-off persistent
  ksh /mnt/app/root/altscreen-u2/scripts/parity_drive_status.sh statistics-off persistent
  ksh /mnt/app/root/altscreen-u2/scripts/parity_drive_status.sh clear-temp
With status enabled the SD keeps current.status plus per-session
status-snapshots.log. With statistics enabled it keeps current.statistics plus
per-session telemetry.tsv. Statistics require the live parity status producer,
so enabling statistics also enables status. They record source FPS, GEN2
source/IDR counters, parity IDR/non-IDR and passive H.264 P/B/I slice classes
through accepted TS output, queue/MOST counters and driver-backpressure timing.

Stop uses the current owner ticket; PID hints never authorize signals.
Parent and independent watchdog retain the exact bridge process identity.
Unconfirmed writer death or handback leaves a quarantined lock.

Shared settings:
  /mnt/app/root/altscreen-u2/bin/alt111-settings list
  /mnt/app/root/altscreen-u2/bin/alt111-settings status
  /mnt/app/root/altscreen-u2/bin/alt111-settings set --key keyframe.interval_frames --value 20
  /mnt/app/root/altscreen-u2/bin/alt111-settings set --key viewarea.selected --value 1
  /mnt/app/root/altscreen-u2/bin/alt111-settings clear-temp

Settings storage is distinct from runtime completion. Read GEN2 active/pending
status and successful current-generation UI acknowledgements. Geometry/persona
remain frozen until renegotiation. Persistent setting writes are POLICY_BLOCKED.
HMI-BINDINGS.json uses the same generated registry; no new HMI menu is claimed.

Media: complete AU -> canonical AUD/SPS/PPS -> one PES; source 32.32 -> PTS;
continuous 12.288-Mbit/s TS, 12032-byte physical blocks,
PAT/PMT/PCR/video PIDs 0/0x10/0x1000/0x11. The real QNX device path is paced
by bounded driver backpressure; regular-file tests retain absolute pacing.
No CFR frame pacer.
Recovery preserves any PES already started and waits for IDR after chain loss.
M1AU presence flags distinguish a real initial timestamp zero from missing time.

Evidence and rollback:
  ksh ./collect-logs.sh
  ksh ./vehicle-rollback.sh

Rollback validates all backups before persistent mutation, confirms owner stop,
restores exact hashes/ABSENT states and restores the original boot command.
A volatile rollback barrier prevents current GEN2 from applying intermediate
legacy settings until the canonical normal reboot. Backups are retained.
Auto-Direct remains temporarily suppressed until that reboot.
The historical standstill cause remains unmeasured; offline success does not
prove vehicle P-frame motion, actual MOST drain or hardware decoder behavior.
EOF

(
  cd "$DEST"
  sha256sum $(find . -type f ! -name PACKAGE-SHA256SUMS.txt -print | sort) > PACKAGE-SHA256SUMS.txt
)

echo "prepared MU1440 parity-drive overlay: $DEST"
echo "GEN2:   $GEN2_SHA"
echo "BRIDGE: $BRIDGE_SHA"
echo "SESSION:$SESSION_SHA"
