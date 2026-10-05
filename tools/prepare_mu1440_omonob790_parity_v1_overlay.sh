#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-}"
GEN2="${2:-build/omonob790-parity/libaltscreen111.so}"
BRIDGE="${3:-build/omonob790-parity/direct-ts-parity}"
SESSION="${4:-build/omonob790-parity/parity-session}"

if [[ -z "$DEST" ]]; then
  echo "usage: $0 DEST [GEN2_BINARY] [PARITY_BRIDGE] [PARITY_SESSION]"
  exit 2
fi

SHAHELP="$ROOT/artifacts/mu1440/sha256sum-compat/build-confirmed-current/sha256sum"
for f in "$GEN2" "$BRIDGE" "$SESSION" "$SHAHELP"; do
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
cp "$SHAHELP" "$DEST/payload/sha256sum"

cp "$ROOT/runtime/parity/omonob790_profile.sh" "$DEST/runtime/omonob790_profile.sh"
cp "$ROOT/runtime/parity/omonob790_session.sh" "$DEST/runtime/omonob790_session.sh"
cp "$ROOT/runtime/parity/omonob790_status.sh" "$DEST/runtime/omonob790_status.sh"
cp "$ROOT/runtime/diagnostics/gen2_compat_profile.sh" "$DEST/runtime/gen2_compat_profile.sh"

chmod +x "$DEST/"*.sh "$DEST/payload/"* "$DEST/runtime/"*.sh

(
  cd "$DEST"
  sha256sum     payload/libaltscreen111.so     payload/direct-ts-parity     payload/parity-session     payload/sha256sum     install.sh     uninstall.sh     status.sh     collect-logs.sh     vehicle-install.sh     vehicle-rollback.sh     runtime/omonob790_profile.sh     runtime/omonob790_session.sh     runtime/omonob790_status.sh     runtime/gen2_compat_profile.sh     > PAYLOAD.sha256
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
required_base_gen2_sha256=8cccf1cb1764952acd973cbb4f881cfd70f3312e7f6a29cdef7fec930c83d25c
required_base_remux_sha256=3f0e730523bd290608dc13e186baa962eeb9c46f117d4d4976be523c0cd94c09
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
MHI2 AltScreen — MU1440 Omonob790 functional-parity vehicle candidate
=====================================================================

Scope
-----
One clean media/ownership parity candidate for:
  MHI2_ER_SKG13_P4526_MU1440
  AID10-class Virtual Cockpit

This is NOT ENVFIX2 with more toggles. The candidate deliberately replaces only
the active GEN2 producer binary and adds a separate clean-room parity transport
plus bounded DMDT session owner. The existing direct-ts-remux stays installed
unchanged and is not used during the parity session.

Install behavior
----------------
The overlay requires the exact successful ENVFIX2 base:
  GEN2/hook  8cccf1cb1764952acd973cbb4f881cfd70f3312e7f6a29cdef7fec930c83d25c
  remux      3f0e730523bd290608dc13e186baa962eeb9c46f117d4d4976be523c0cd94c09

It backs up every path it mutates. The only persistent configuration change is:
  /mnt/app/root/mibr-carplay-autodirect = 0
so the legacy writev-gate Auto-Direct path cannot race the DMDT parity path.

A normal IOC reboot is required because the GEN2 libairplay preload changes.

First parity test
-----------------
After reboot and before connecting CarPlay:
  ksh ./status.sh
  ksh /mnt/app/root/altscreen-u2/scripts/omonob790_profile.sh temp

Then connect CarPlay and start Waze/Maps. When Stream111 is reported streaming,
run one bounded parity session:
  ksh /mnt/app/root/altscreen-u2/scripts/omonob790_session.sh 60

The session:
  - requires the exact parity profile;
  - forces M1AU for the new bridge connection;
  - releases ownership with DMDT dc 72 / sc 4 72;
  - starts direct-ts-parity;
  - restores stock with DMDT dc 70 33 / sc 4 70;
  - has an independent restore watchdog.

Collect evidence explicitly:
  ksh ./collect-logs.sh

Parity media contract
---------------------
  complete AU -> one PES
  Stream111 32.32 source clock -> 90-kHz PTS
  no fixed frame pacer
  continuous 12.288-Mbit/s MPEG-TS
  PAT=0x0000 PMT=0x0010 PCR=0x1000 H264=0x0011
  PAT/PMT/PCR cadence ~= 40 ms
  physical write = 64 x 188 = 12032 bytes
  source ordinal owns gap detection and the reference every-20-frame IDR request
  recovery waits for a fresh IDR after a broken predictive chain

Deliberate safety difference
----------------------------
The reference packet-level low-latency flush can truncate an already-started
PES. This candidate never does that. Recovery discards only complete not-yet-
started AUs and preserves the tail of an in-flight PES.

Records larger than the reference 262144-byte transport budget are read within
the bounded safety envelope, dropped as whole AUs and followed by IDR recovery.
Every output is paced on absolute monotonic deadlines. A driver delay greater
than 40 ms or incomplete physical-block acceptance fails the session explicitly.
PTS is checked again at PES emission against the complete transfer budget.
These guards bound software timing; hardware drain and decoder behavior still
require target validation.

Control-plane note
------------------
An already-installed M.I.B. NavIgnore policy may remain loaded. It is not part
of the Omonob media implementation and is explicitly outside this parity proof.
The media ownership path itself uses DMDT, not the M.I.B. writev gate.

Rollback
--------
  ksh ./vehicle-rollback.sh

Rollback restores the exact previous GEN2/hook and persistent Auto-Direct state,
then performs the canonical normal IOC reboot.
EOF

(
  cd "$DEST"
  sha256sum $(find . -type f ! -name PACKAGE-SHA256SUMS.txt -print | sort) > PACKAGE-SHA256SUMS.txt
)

echo "prepared Omonob790 functional-parity overlay: $DEST"
echo "GEN2:   $GEN2_SHA"
echo "BRIDGE: $BRIDGE_SHA"
echo "SESSION:$SESSION_SHA"
