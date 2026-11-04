#!/usr/bin/env python3
"""A2.3.2: source-linked MMX storage access/rollback ledger, host only.

This is a consolidated *work graph*, NOT a verified complete on-unit inventory.
Lexical references are never automatically promoted to verified writer/reader
roles. Unknown historical binaries and generated boot hooks fail release review.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import sys

# Sibling tools are imported by name; keep that working under `python3 -I`,
# which drops the script directory from sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import source_defaults_inventory as inventory
import storage_migration_review as storage
import storage_path_triage as triage
import storage_consumer_crosscheck as consumers
import legacy_marker_contract as markers

ROOT = Path(__file__).resolve().parents[2]
BASE = "/mnt/app/root/"
NAV_SCRIPTS = (
    "modules/navigation/runtime/gen2_nav_config.sh",
    "modules/navigation/runtime/gen2_safearea.sh",
)
NAV_VARIABLE = re.compile(r"^([A-Z][A-Z0-9_]*)=\$ROOT/([a-zA-Z0-9_.-]+)$", re.M)
OUTSIDE_MOUNT = (
    {"path": "/mnt/app/eso/hmi/lsd/lsd.sh",
     "source": "modules/carplay/runtime/auto-direct/direct_ts_auto_enable.sh",
     "reason": "generated conditional boot code with legacy marker path"},
    {"path": "/mnt/system/etc/boot/startup.sh",
     "source": "modules/carplay/runtime/isotx2-gate/install_preload.sh",
     "reason": "generated DisplayManager preload/stock fallback branch"},
)


class GraphError(ValueError):
    pass


def require(test, message):
    if not test:
        raise GraphError(message)


def legal_path(path):
    return (isinstance(path, str) and path.startswith(BASE)
            and path != BASE and not path.endswith("/")
            and ".." not in path and
            re.fullmatch(r"/[A-Za-z0-9_./-]+", path) is not None)


def new_row(path, kind, source_certainty, category, evidence):
    require(legal_path(path), "unsafe persistent source path: " + str(path))
    return {
        "current_path": path,
        "kind": kind,
        "source_certainty": source_certainty,
        "original_category": category,
        "evidence": evidence,
        "one_actual_writer_verified": False,
        "every_reader_verified": False,
        "installed_boot_references_verified": False,
        "format_migration_verified": False,
        "upgrade_uninstall_rollback_verified": False,
        "destination_path": None,
        "disposition": "REVIEW_REQUIRED",
    }


def build(root=ROOT):
    base = inventory.build(root)
    rev = storage.compile_review(base)
    tri = triage.build(rev, root)
    checked = consumers.inspect(consumers.load(root), base)
    marker_paths = {p for case in markers.CASES for p, _, _ in case["evidence"]}
    marker_src = {p: (root / p).read_text(encoding="utf-8") for p in marker_paths}
    marker_report = markers.build(marker_src)
    require(not any(x.get("migration_authorized") for x in (base, rev, tri, checked, marker_report)),
            "a partial source tool claims migration is authorized")
    require(len(checked["broker_c_java_consistency"]) == 13,
            "missing validated broker C/Java source pairs")
    require(marker_report["case_count"] == 6, "marker provenance drift")

    rows = {}
    def add(row):
        path = row["current_path"]
        require(path not in rows, "duplicate source path / logical owner: " + path)
        rows[path] = row

    for record in rev["records"]:
        is_broker = record["id"].startswith("broker:")
        path = (record["exact_declared_persistent_path"] if is_broker
                else record["source_derived_candidate_persistent_path"])
        entry = new_row(
            path, "broker-durable-switch" if is_broker else "carplay-registry-group",
            record["path_certainty"],
            "revisioned-magic-CAS" if is_broker else "registry-layered-group",
            [{"source": record["source"], "role": "canonical-declaration"}]
        )
        entry["logical_id"] = record["id"]
        entry["setting_keys"] = record["keys"]
        entry["candidate_destination_directory"] = record["proposed_destination_directory"]
        entry["reported_lexical_references"] = record["lexical_locations"]
        if is_broker:
            pair = next((x for x in checked["broker_c_java_consistency"]
                         if x["path"] == path), None)
            require(pair is not None, "C/Java pair missing for " + path)
            require(pair["magic"] == record["magic_and_format_owner"],
                    "C/Java broker format mismatch")
            entry["observed_format_identity"] = pair["magic"]
            entry["observed_writer_api"] = pair["observed_broker_writer_api"]
            entry["observed_reader_api"] = pair["observed_java_reader"]
            entry["evidence"].append({
                "source": consumers.J, "role": "verified-selected-Java-reader-contract"
            })
            entry["evidence"].append({
                "source": consumers.C, "role": "verified-selected-broker-CAS-contract"
            })
        else:
            require(path.startswith(BASE + "mibr-carplay111-")
                    or path == BASE + "mibr-carplay-autodirect",
                    "unapproved CarPlay file-group path")
            entry["corresponding_volatile_path"] = "/tmp/" + path[len(BASE):]
            entry["observed_reader_api"] = "alt111_settings_paths: group_name()"
            entry["observed_persistent_write_state"] = "POLICY_BLOCKED"
            entry["evidence"].append({
                "source": consumers.SETTINGS,
                "role": "verified-selected-dynamic-read-layer-join"
            })
        add(entry)

    # Include EVERY exact persistent lexical fragment outside the canonical
    # registry, not just a preselected set of interesting or safe-looking files.
    excluded = []
    for rec in tri["fragment_groups"]:
        path, category = rec["literal_fragment"], rec["category"]
        if path in rows:
            rows[path]["reported_lexical_references"].extend(rec["source_locations"])
            continue
        if (not path.startswith(BASE) or category in (
                "noncanonical-fragment", "project-directory", "installed-runtime",
                "legacy-installed-runtime", "durable-log")):
            excluded.append({
                "fragment": path, "category": category,
                "reason": "not-a-proven-standalone-user-configuration-file",
                "source_locations": rec["source_locations"],
            })
            continue
        # A lexical path may still be a test fixture, directory, status,
        # bare prefix, or only a stage/backup location: no inferred writer.
        entry = new_row(
            path, "additional-persistent-path-candidate",
            "lexical-reference-not-verified-runtime-file", category,
            [{"source": x["source"], "line": x["line"], "role": "lexical-reference-only"}
             for x in rec["source_locations"]],
        )
        entry["observed_semantics"] = "UNDETERMINED"
        entry["candidate_destination_directory"] = None
        add(entry)

    # Shell $ROOT + filename constructions are invisible to the lexical
    # absolute-path scanner. Record each proven literal suffix as a path lead.
    dynamic = []
    for filename in NAV_SCRIPTS:
        source = (root / filename).read_text(encoding="utf-8")
        require(re.search(r"^ROOT=/mnt/app/root$", source, re.M) is not None,
                "navigation persistent ROOT changed: " + filename)
        matches = NAV_VARIABLE.findall(source)
        require(matches, "navigation ROOT filename consumers disappeared: " + filename)
        for variable, basename in matches:
            path = BASE + basename
            require(legal_path(path), "unsafe navigation ROOT suffix: " + path)
            lead = {
                "source": filename, "variable": variable,
                "current_path": path, "role": "shell-dynamic-root-composition",
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            }
            dynamic.append(lead)
            if path not in rows:
                entry = new_row(
                    path, "legacy-navigation-shell-store",
                    "source-verified-shell-root-concatenation",
                    "legacy-script-specific-grammar",
                    [lead],
                )
                entry["candidate_destination_directory"] = None
                entry["observed_writer_api"] = "navigation-script (audit each command)"
                add(entry)
            else:
                rows[path]["evidence"].append(lead)

    require(len(rev["records"]) == 26, "known 26-record registry drift")
    require(len(dynamic) >= 7, "incomplete legacy navigation root scan")

    # Named high-risk marker contracts anchor interpretations but cannot
    # prove absence of OTHER readers, writers or prior on-unit hook versions.
    marker_index = []
    for item in marker_report["cases"]:
        case_path = item["current_path"]
        require(legal_path(case_path), "unsafe marker path")
        require(case_path in rows, "high-risk marker not inventoried: " + case_path)
        rows[case_path]["observed_semantics"] = item["observed_semantics"]
        rows[case_path]["high_risk_marker_id"] = item["id"]
        rows[case_path]["evidence"].extend(item["exact_source_evidence"])
        marker_index.append(case_path)
        for related in item["related_paths"]:
            if related.startswith(BASE):
                require(related in rows, "related persistent marker missing: " + related)

    nonliteral = tri["nonliteral_source_contexts"]
    require(len(nonliteral) == rev["counts"]["unresolved_source_lines"],
            "dynamic-source lead disappeared")
    report = {
        "schema_version": 1,
        "kind": "source-linked-storage-access-review-graph",
        "status": "PARTIAL_REQUIRES_COMPLETE_READER_WRITER_AND_RESTORE_AUDIT",
        "counts": {
            "canonical_carplay_groups": 13, "canonical_broker_switches": 13,
            "persistent_path_rows": len(rows),
            "additional_candidate_rows": len(rows) - 26,
            "nav_composed_path_leads": len(dynamic),
            "external_boot_hook_paths": len(OUTSIDE_MOUNT),
            "high_risk_marker_contracts": len(marker_index),
            "other_lexical_fragments_separately_classified": len(excluded),
            "nonliteral_root_or_env_leads": len(nonliteral),
            "pending_final_destinations": sum(x["destination_path"] is None
                                              for x in rows.values()),
        },
        "source_contracts": base["source_sha256"],
        "records": [rows[key] for key in sorted(rows)],
        "excluded_or_nonconfiguration_lexical_fragments": excluded,
        "unresolved_nonliteral_source_leads": nonliteral,
        "navigation_composed_path_leads": dynamic,
        "outside_project_boot_hook_restore_boundaries": list(OUTSIDE_MOUNT),
        "blocking_evidence": [
            "every actual installed boot/patch/legacy binary reader and single writer",
            "file grammar, layer precedence, CRC/revision/CAS and stage/restore format",
            "complete source-compiled/generated path and target-profile adapter closure",
            "exact destination names and owner-reviewed collision/alias conversion",
            "backup originals/metadata, format-aware upgrade, uninstall and power-loss rollback",
            "real QNX MMX mount and readback qualification on explicit separate approval",
        ],
        "migration_authorized": False,
    }
    require(report["counts"]["pending_final_destinations"] == len(rows),
            "unreviewed destination unexpectedly present")
    return report


def require_complete(report):
    if (report["migration_authorized"] is not True
            or report["status"] != "REVIEWED_ALL_CONSUMERS_AND_ROLLBACK"
            or report["counts"]["pending_final_destinations"] != 0):
        raise GraphError("A2.3.2 not approved: incomplete path/owner/rollback coverage")


def self_test():
    report = build()
    counts = report["counts"]
    assert counts["canonical_carplay_groups"] == 13
    assert counts["canonical_broker_switches"] == 13
    assert counts["high_risk_marker_contracts"] == 6
    assert counts["nav_composed_path_leads"] >= 7
    assert not report["migration_authorized"]
    assert len({x["current_path"] for x in report["records"]}) == counts["persistent_path_rows"]
    must_include = [
        "/mnt/app/root/mibr-carplay111-viewareas.conf",
        "/mnt/app/root/mibr-carplay111-nav.surface",
        "/mnt/app/root/mibr-carplay111-safearea.conf",
        "/mnt/app/root/mibr-carplay-autodirect.enabled",
        "/mnt/app/root/mibr-parity-drive.enabled",
        "/mnt/app/root/altscreen-u2/config/mibr-carplay-nav.conf",
    ]
    assert set(must_include) <= {x["current_path"] for x in report["records"]}
    assert all(x["destination_path"] is None for x in report["records"])
    for path in ("/mnt/app/root/../evil", "/tmp/not-persistent",
                 "/mnt/app/root/unsafe%2fpath", "/mnt/app/root/"):
        assert not legal_path(path)
    try:
        require_complete(report)
    except GraphError:
        pass
    else:
        raise AssertionError("incomplete consumer matrix accepted")
    print("STORAGE_ACCESS_GRAPH_SELF_TEST=PASS")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--json-out", type=Path)
    p.add_argument("--require-complete", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
    data = build()
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n",
                                 encoding="utf-8")
    if args.require_complete:
        require_complete(data)
    print("STORAGE_ACCESS_GRAPH=PARTIAL " + json.dumps(data["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
