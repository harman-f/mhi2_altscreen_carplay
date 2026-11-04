#!/usr/bin/env python3
"""Host-only review queue for the future MMX persistent-storage migration.

Consumes the canonical source inventory. This deliberately does NOT classify
lexical path matches as proven readers/writers, choose destination filenames,
or declare that a configuration migration is safe to execute.
"""
import argparse
import copy
import json
from pathlib import Path

import sys

# Sibling tools are imported by name; keep that working under `python3 -I`,
# which drops the script directory from sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import source_defaults_inventory as source_inventory

CARPLAY_PERSISTENT_ROOT = "/mnt/app/root/"
CARPLAY_VOLATILE_ROOT = "/tmp/"
PROJECT_ROOT = "/mnt/app/root/altscreen-u2/"
DESTINATION_ROOT = PROJECT_ROOT + "config/"
BROKER_GROUPS = {
    "carplay_nav": "navigation",
    "nav_line": "navigation",
    "nav_night": "navigation",
    "nav_source": "navigation",
    "nav_display": "navigation",
    "nav_bottom": "navigation",
    "nav_side": "navigation",
    "nav_lanes": "navigation",
    "safe_voll": "cockpit",
    "safe_wide": "cockpit",
    "safe_center": "cockpit",
    "sd_log": "features",
    "expert_mode": "features",
}


class ReviewError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ReviewError(message)


def references_for_path(path, references):
    """Lexical locations only: may be reads, writes, tests, or comments."""
    return [
        {"source": ref["source"], "line": ref["line"]}
        for ref in references
        if ref["literal_fragment"] == path
    ]


def compile_review(inventory):
    counts = inventory["counts"]
    require(counts["carplay_settings"] == 48, "CarPlay registry count drift")
    require(counts["carplay_storage_groups"] == 13, "CarPlay file-group count drift")
    require(counts["broker_switches"] == 13, "broker switch count drift")
    require(inventory.get("migration_authorized") is False,
            "source inventory unexpectedly authorizes migration")
    paths = inventory["unit_path_evidence"]
    require(paths["evidence_grade"] == "literal-source-reference-only",
            "source path evidence has an unreviewed meaning")
    references = paths["references"]
    require(all({"literal_fragment", "source", "line"} <= set(ref)
                for ref in references), "incomplete lexical reference")

    records = []
    for basename, keys in sorted(inventory["carplay"]["file_groups"].items()):
        require(isinstance(basename, str) and basename.startswith("mibr-")
                and "/" not in basename and ".." not in basename,
                "invalid CarPlay basename")
        require(isinstance(keys, list) and keys, "empty CarPlay file group")
        current = CARPLAY_PERSISTENT_ROOT + basename
        temp = CARPLAY_VOLATILE_ROOT + basename
        records.append({
            "id": "carplay:" + basename,
            "owner_declared_in_source": "carplay-registry",
            "keys": sorted(keys),
            "source": inventory["carplay"]["source"],
            "source_derived_candidate_persistent_path": current,
            "source_derived_candidate_volatile_path": temp,
            "path_certainty": "constructed-from-registry-basename-not-runtime-proof",
            "lexical_locations": references_for_path(current, references),
            "proposed_destination_directory": DESTINATION_ROOT + "carplay/",
            "final_destination_file": None,
            "format_and_writer_verified": False,
            "all_readers_verified": False,
            "boot_and_rollback_verified": False,
            "review_state": "PENDING",
        })

    switches = inventory["broker"]["switches"]
    require(set(BROKER_GROUPS) == {item["key"] for item in switches},
            "broker switch categories need explicit review")
    seen_paths = set()
    for item in sorted(switches, key=lambda value: value["key"]):
        current = item["current_path"]
        require(isinstance(current, str)
                and current.startswith(PROJECT_ROOT + "config/")
                and current not in seen_paths,
                "unsafe or duplicate broker source path")
        seen_paths.add(current)
        records.append({
            "id": "broker:" + item["key"],
            "owner_declared_in_source": "broker-single-writer-CAS",
            "keys": [item["key"]],
            "source": inventory["broker"]["source"],
            "exact_declared_persistent_path": current,
            "path_certainty": "broker-source-declaration",
            "magic_and_format_owner": item["magic"],
            "lexical_locations": references_for_path(current, references),
            "proposed_destination_directory":
                DESTINATION_ROOT + BROKER_GROUPS[item["key"]] + "/",
            "final_destination_file": None,
            "format_and_writer_verified": False,
            "all_readers_verified": False,
            "boot_and_rollback_verified": False,
            "review_state": "PENDING",
        })

    require(len(records) == 26, "unexpected record count")
    require(len({record["id"] for record in records}) == len(records),
            "duplicate logical configuration identity")
    known_paths = {
        record.get("exact_declared_persistent_path",
                   record.get("source_derived_candidate_persistent_path"))
        for record in records
    }
    known_paths.update(
        record["source_derived_candidate_volatile_path"] for record in records
        if "source_derived_candidate_volatile_path" in record
    )

    unmatched = [ref for ref in references
                 if ref["literal_fragment"] not in known_paths]
    # These are investigation targets, NOT evidence of additional active stores.
    unresolved = paths["unresolved_source_lines"]
    require(isinstance(unresolved, list), "missing dynamic-path audit queue")
    return {
        "schema_version": 1,
        "status": "REVIEW_REQUIRED_NOT_MIGRATION_READY",
        "source_inventory_kind": inventory["kind"],
        "source_sha256": inventory["source_sha256"],
        "counts": {
            "carplay_file_groups": 13,
            "broker_switches": 13,
            "review_records": len(records),
            "unmatched_lexical_references": len(unmatched),
            "unresolved_source_lines": len(unresolved),
        },
        "records": records,
        "unmatched_literal_references": unmatched,
        "unresolved_dynamic_or_nonliteral_source_lines": unresolved,
        "review_requirements": [
            "prove every actual reader, single writer and boot/restore consumer",
            "resolve literal fragments, concatenated paths and generated output",
            "preserve broker magic/revision/CAS and menu CRC grammars",
            "distinguish persistent user intent, platform defaults and /tmp IPC",
            "review explicit destination filenames and update/uninstall behavior",
            "require exact-byte backup, readback, RW->RO, rollback and power-loss tests",
        ],
        "migration_authorized": False,
    }


def migration_ready(review):
    """A pending review must not become a permissive release/install gate."""
    return (
        review.get("status") == "REVIEWED"
        and not review.get("unmatched_literal_references")
        and not review.get("unresolved_dynamic_or_nonliteral_source_lines")
        and bool(review.get("records"))
        and all(
            record.get("final_destination_file")
            and record.get("format_and_writer_verified") is True
            and record.get("all_readers_verified") is True
            and record.get("boot_and_rollback_verified") is True
            and record.get("review_state") == "REVIEWED"
            for record in review["records"]
        )
    )


def self_test():
    inventory = source_inventory.build()
    review = compile_review(inventory)
    assert review["counts"]["review_records"] == 26
    assert review["migration_authorized"] is False
    assert not migration_ready(review)
    ids = {row["id"] for row in review["records"]}
    assert "broker:carplay_nav" in ids
    assert "carplay:mibr-carplay111-viewareas.conf" in ids
    assert len([r for r in review["records"] if r["id"].startswith("broker:")]) == 13
    assert len([r for r in review["records"] if r["id"].startswith("carplay:")]) == 13
    bad = copy.deepcopy(inventory)
    bad["broker"]["switches"][0]["current_path"] = (
        bad["broker"]["switches"][1]["current_path"]
    )
    try:
        compile_review(bad)
    except ReviewError:
        pass
    else:
        raise AssertionError("duplicate source path accepted")
    bad = copy.deepcopy(inventory)
    bad["broker"]["switches"][0]["key"] = "unreviewed_future_switch"
    try:
        compile_review(bad)
    except ReviewError:
        pass
    else:
        raise AssertionError("new unmapped broker switch accepted")
    ready = copy.deepcopy(review)
    ready["status"] = "REVIEWED"
    assert not migration_ready(ready), "status-only flip bypassed review"
    print("STORAGE_MIGRATION_REVIEW_SELF_TEST=PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--require-migration-ready", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    result = compile_review(source_inventory.build())
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.require_migration_ready and not migration_ready(result):
        parser.error("migration not approved: source paths/owners still require review")
    print("STORAGE_MIGRATION_REVIEW=PARTIAL " +
          json.dumps(result["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
