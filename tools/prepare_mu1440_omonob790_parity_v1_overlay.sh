#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-}"
GEN2="${2:-build/omonob790-parity/libaltscreen111.so}"
BRIDGE="${3:-build/omonob790-parity/direct-ts-parity}"
SESSION="${4:-build/omonob790-parity/parity-session}"
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
  cp "$ROOT/deployment/mu1440-omonob790-parity-v1/$f" "$DEST/$f"
done

cp "$GEN2" "$DEST/payload/libaltscreen111.so"
cp "$BRIDGE" "$DEST/payload/direct-ts-parity"
cp "$SESSION" "$DEST/payload/parity-session"
cp "$SETTINGS" "$DEST/payload/alt111-settings"
cp "$GUARD" "$DEST/payload/libmibr_isotx2_guard.so"
cp "$SHAHELP" "$DEST/payload/sha256sum"

cp "$ROOT/runtime/parity/omonob790_profile.sh" "$DEST/runtime/omonob790_profile.sh"
cp "$ROOT/runtime/parity/omonob790_session.sh" "$DEST/runtime/omonob790_session.sh"
cp "$ROOT/runtime/parity/omonob790_status.sh" "$DEST/runtime/omonob790_status.sh"
cp "$ROOT/runtime/diagnostics/gen2_compat_profile.sh" "$DEST/runtime/gen2_compat_profile.sh"
cp "$ROOT/settings/runtime-basenames.generated.sh" "$DEST/runtime/settings-basenames.sh"
cp "$ROOT/settings/hmi-bindings.generated.json" "$DEST/HMI-BINDINGS.json"

chmod +x "$DEST/"*.sh "$DEST/payload/"* "$DEST/runtime/"*.sh

(
  cd "$DEST"
  sha256sum     payload/libaltscreen111.so     payload/direct-ts-parity     payload/parity-session     payload/alt111-settings     payload/libmibr_isotx2_guard.so     payload/sha256sum     install.sh     uninstall.sh     status.sh     collect-logs.sh     vehicle-install.sh     vehicle-rollback.sh     runtime/omonob790_profile.sh     runtime/omonob790_session.sh     runtime/omonob790_status.sh     runtime/gen2_compat_profile.sh     runtime/settings-basenames.sh     HMI-BINDINGS.json     > PAYLOAD.sha256
)

GEN2_SHA=$(sha256sum "$GEN2" | awk '{print $1}')
BRIDGE_SHA=$(sha256sum "$BRIDGE" | awk '{print $1}')
SESSION_SHA=$(sha256sum "$SESSION" | awk '{print $1}')
SOURCE_HEAD_COMMIT_VALUE=${SOURCE_HEAD_COMMIT:-${GITHUB_SHA:-local}}
CI_MERGE_COMMIT_VALUE=${CI_MERGE_COMMIT:-}

cat > "$DEST/CANDIDATE-MANIFEST.txt" <<EOF
candidate=omonob790-functional-parity-v1
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
profile_legacy_d2=disabled
input=m1au_complete_au
source_clock=stream111_32.32
pts_clock=source_derived_90khz
frame_pacer=none
transport_pacer=absolute_monotonic_all_outputs
transport_late_limit_us=40000
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
ownership=dmdt_dc72_sc4_72_restore_dc70_33_sc4_70
dmdt_timeout_ms=5000
session_watchdog_margin_seconds=20
reference_producer_payload_limit=262144
bridge_safety_payload_limit=3145728
recovery=au_pes_boundary_safe
reference_mid_pes_flush=deliberately_not_reproduced
navignore=existing_control_plane_substrate_not_part_of_media_parity
runtime_state=flat_tmp_files
sd_log_export=/net/mmx/fs/sda0/esd/carplay-test/logs/omonob790-parity
EOF

if [[ -n "$CI_MERGE_COMMIT_VALUE" ]]; then
  echo "ci_merge_commit=$CI_MERGE_COMMIT_VALUE" >> "$DEST/CANDIDATE-MANIFEST.txt"
fi

cat > "$DEST/README-FIRST.txt" <<'EOF'
MHI2 AltScreen — MU1440 master candidate
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

After reboot, before connecting CarPlay:
  ksh ./status.sh
  ksh /mnt/app/root/altscreen-u2/scripts/omonob790_profile.sh dual-temp

The dual preset advertises both areas. Keep selected area 0 for ownership/media
qualification. The reference one-area preset is available through 'temp'.
Preset application is one shared transaction and requires real CarPlay reconnect.
Connect CarPlay, open Maps/Waze, confirm Stream-111 streaming, then:
  ksh /mnt/app/root/altscreen-u2/scripts/omonob790_session.sh 60

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
  ksh /mnt/app/root/altscreen-u2/scripts/omonob790_session.sh stop
  ksh /mnt/app/root/altscreen-u2/scripts/omonob790_session.sh restore-stock

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
continuous independently paced 12.288-Mbit/s TS, 12032-byte physical blocks,
PAT/PMT/PCR/video PIDs 0/0x10/0x1000/0x11. No CFR frame pacer.
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

echo "prepared Omonob790 functional-parity overlay: $DEST"
echo "GEN2:   $GEN2_SHA"
echo "BRIDGE: $BRIDGE_SHA"
echo "SESSION:$SESSION_SHA"
