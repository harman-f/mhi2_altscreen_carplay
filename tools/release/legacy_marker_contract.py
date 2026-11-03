#!/usr/bin/env python3
"""A2.3 host-only evidence for legacy MMX activation and safety markers.

Exact-source tokens demonstrate selected boot/reader/writer statements, NOT
all possible readers, target qualification, or permission to migrate them.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTO = "modules/carplay/runtime/auto-direct/"
PARITY = "modules/carplay/runtime/parity/"
ISOTX = "modules/carplay/runtime/isotx2-gate/"
BROKER = "modules/broker/"
DEPLOY = "deployment/mu1440/"
CASES = (
    {
        "id": "auto-direct", "path": "/mnt/app/root/mibr-carplay-autodirect.enabled",
        "semantics": "persistent-file-existence", "migration_hazard": "generated-lsd.sh-boot-hook",
        "evidence": [
            (AUTO+"direct_ts_auto_enable.sh", "writer-create", 'touch "$ENABLED"'),
            (AUTO+"direct_ts_auto_enable.sh", "generated-boot-reader",
             "if [ -e /mnt/app/root/mibr-carplay-autodirect.enabled ]; then"),
            (AUTO+"direct_ts_auto_disable.sh", "writer-remove", 'rm -f "$ENABLED"'),
            (AUTO+"direct_ts_auto_start.sh", "session-reader", '[ -e "$ENABLED" ]'),
        ],
    },
    {
        "id": "legacy-D2", "path": "/mnt/app/root/mibr-alt111-keyframe-policy.enabled",
        "semantics": "persistent-presence-mirrored-to-volatile-presence",
        "migration_hazard": "old-GEN2-binary-temp-marker-consumer",
        "evidence": [
            (DEPLOY+"install.sh", "installer-writer",
             ": > /mnt/app/root/mibr-alt111-keyframe-policy.enabled"),
            (DEPLOY+"uninstall.sh", "uninstall-removal",
             "/mnt/app/root/mibr-alt111-keyframe-policy.enabled"),
            (AUTO+"direct_ts_auto_start.sh", "persistent-reader",
             'if [ -e "$D2_PERSIST" ]; then'),
            (AUTO+"direct_ts_auto_start.sh", "volatile-bridge-writer",
             'touch "$D2_SESSION"'),
        ],
    },
    {
        "id": "parity-drive", "path": "/mnt/app/root/mibr-parity-drive.enabled",
        "semantics": "content-value-1-or-0", "migration_hazard": "boot-supervisor-reads-value",
        "evidence": [
            (PARITY+"parity_drive_enable.sh", "writer-1", 'echo 1 > "$ENABLE"'),
            (PARITY+"parity_drive_disable.sh", "writer-0", 'echo 0 > "$ENABLE"'),
            (PARITY+"parity_drive_supervisor.sh", "runtime-reader",
             'V=$(cat "$ENABLE" 2>/dev/null)'),
            (PARITY+"parity_drive_supervisor.sh", "enabled-value-validator",
             '[ "$V" = "1" ]'),
        ],
    },
    {
        "id": "isotx2-disable", "path": "/mnt/app/root/mibr-isotx2-gate-disable",
        "semantics": "inverted-presence-disables-preload",
        "migration_hazard": "embedded-DisplayManager-boot-patch",
        "evidence": [
            (ISOTX+"preload_control.sh", "writer-disable",
             ': > "$MARKER"'),
            (ISOTX+"preload_control.sh", "writer-enable",
             'rm -f "$MARKER"'),
            (ISOTX+"install_preload.sh", "generated-startup-reader",
             "if [ -f /mnt/app/root/mibr-isotx2-gate-disable ]"),
        ],
    },
    {
        "id": "broker-durable-allow", "path":
        "/mnt/app/root/altscreen-u2/config/mibr-v3-single-writer.enabled",
        "semantics": "strict-2-byte-1-newline-read-gate",
        "migration_hazard": "permission-to-enable-broker-persistent-writes",
        "evidence": [
            (BROKER+"runtime/mibr-control/mibr-v3-boot.ksh", "boot-reader",
             '[ "$(cat "$MARK" 2>/dev/null)" = 1 ]'),
            (BROKER+"source/mibr-control/mibr_v3_qnx_mount.c", "strict-length",
             "before.st_size!=2"),
            (BROKER+"source/mibr-control/mibr_v3_qnx_mount.c", "strict-bytes",
             r"value[0]!='1'||value[1]!='\n'"),
        ],
    },
    {
        "id": "parity-diagnostics", "path": "/mnt/app/root/mibr-parity-status-enabled",
        "related_paths": ["/mnt/app/root/mibr-parity-statistics-enabled",
                          "/tmp/mibr-parity-status-enabled",
                          "/tmp/mibr-parity-statistics-enabled"],
        "semantics": "value-with-temp-before-persistent-before-default",
        "migration_hazard": "writer-and-supervisor-must-preserve-priority",
        "evidence": [
            (PARITY+"parity_drive_status.sh", "root-declarations",
             "STATUS_P=/mnt/app/root/mibr-parity-status-enabled"),
            (PARITY+"parity_drive_status.sh", "statistics-declaration",
             "STATS_P=/mnt/app/root/mibr-parity-statistics-enabled"),
            (PARITY+"parity_drive_status.sh", "temporary-precedence",
             'if [ -r "$T" ]; then V=$(cat "$T"'),
            (PARITY+"parity_drive_status.sh", "persistent-writer",
             'echo "$VALUE" > "$P"'),
            (PARITY+"parity_drive_supervisor.sh", "runtime-consumer",
             'STATUS_CFG_PERSIST=/mnt/app/root/mibr-parity-status-enabled'),
        ],
    },
)


def require(test, reason):
    if not test:
        raise ValueError(reason)


def build(sources):
    seen, report = set(), []
    for case in CASES:
        require(case["id"] not in seen, "duplicate logical marker")
        seen.add(case["id"])
        evidences = []
        for path, role, token in case["evidence"]:
            require(path in sources, "source missing: " + path)
            require(token in sources[path], "stale source contract: " + case["id"] + " " + role)
            evidences.append({
                "source": path, "role_observed": role,
                "source_exact_token": token,
                "sha256": hashlib.sha256(sources[path].encode()).hexdigest(),
            })
        report.append({
            "id": case["id"], "current_path": case["path"],
            "related_paths": case.get("related_paths", []),
            "observed_semantics": case["semantics"],
            "migration_hazard": case["migration_hazard"],
            "exact_source_evidence": evidences,
            "all_readers_and_writers_verified": False,
            "target_path": None, "format_conversion_approved": False,
            "unit_verified": False,
        })
    return {
        "schema_version": 1, "kind": "legacy-marker-source-contract",
        "cases": report, "case_count": len(report),
        "status": "PARTIAL_REQUIRES_FULL_CONSUMER_AND_ROLLBACK_MAPPING",
        "migration_authorized": False,
    }


def test(sources):
    good = build(sources)
    assert good["case_count"] == 6 and not good["migration_authorized"]
    for case in CASES:
        p, role, token = case["evidence"][0]
        corrupted = dict(sources)
        corrupted[p] = corrupted[p].replace(token, "CONTRACT_MISSING")
        try:
            build(corrupted)
        except ValueError as e:
            assert "stale source contract" in str(e)
        else:
            raise AssertionError("did not reject changed source: " + case["id"])
    print("LEGACY_MARKER_CONTRACT_SELF_TEST=PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    paths = {p for case in CASES for p, _, _ in case["evidence"]}
    sources = {p: (ROOT/p).read_text(encoding="utf-8") for p in paths}
    if args.self_test:
        test(sources)
    report = build(sources)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print("LEGACY_MARKER_CONTRACT=PARTIAL cases=" + str(report["case_count"]))


if __name__ == "__main__":
    main()
