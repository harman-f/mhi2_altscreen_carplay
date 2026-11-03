#!/usr/bin/env python3
"""Proposed A2/A3 storage identities; host-only and NOT an installer.

This is a source-derived naming/ownership collision gate for the existing
63-candidate graph. A proposed destination is not a verified active path or
permission to write. Keep legacy native grammars and early-boot consumers
unchanged until a separately qualified coordinated release.
"""
import argparse
import copy
import json
import re
from pathlib import Path

import storage_access_graph as access
import storage_migration_review as review

ROOT = Path(__file__).resolve().parents[2]
OLD = "/mnt/app/root/"
NEW = OLD + "altscreen-u2/"
VALID_RELATIVE = re.compile(
    r"(?:config/(?:carplay|navigation|cockpit|menu|vehicle|platform|features)"
    r"|state/[a-z0-9-]+|version(?:/[a-z0-9-]+)?|backup/[a-z0-9-]+)"
    r"/[a-z0-9][a-z0-9._-]*"
)

# Exactly the 37 *additional candidates*, not a claim of 37 real settings.
# relative old path | proposed relative new path or '-' | owner/role | file policy
# "hold-*" means no automatic migration target exists yet. In particular,
# two opposite bit26 markers must never become competing writers of one file.
ADDITIONAL_SPECS = """
altscreen-u2/config/cpvc-r5.profile|config/cockpit/cpvc-r5.profile|cockpit-profile|preserve-native
altscreen-u2/config/display-scaling.conf|config/cockpit/scaling.conf|display-scaling|preserve-native
altscreen-u2/config/mibr-calib.avcc|config/cockpit/calibration.avcc|carplay-calibration|opaque-format
altscreen-u2/config/mibr-menu-language.conf|config/menu/language.conf|menu-language|preserve-native
altscreen-u2/config/mibr-menu.conf|config/menu/layout.conf|menu-layout|preserve-crc
altscreen-u2/config/mibr-platform-defaults.conf|config/platform/defaults.conf|platform-defaults|preserve-native
altscreen-u2/config/vdata.mode|config/vehicle/data-mode.conf|vehicle-data|preserve-native
altscreen-u2/config/vstatus.mode|config/vehicle/status-mode.conf|vehicle-status|preserve-native
mibr-carplay111-nav-query.enabled|-|legacy-navigation|hold-alias
mibr-carplay111-nav.maneuverLayout|-|legacy-navigation|hold-alias
mibr-carplay111-nav.showCompass|-|legacy-navigation|hold-alias
mibr-carplay111-nav.showETA|-|legacy-navigation|hold-alias
mibr-carplay111-nav.showSpeedLimit|-|legacy-navigation|hold-alias
mibr-carplay111-nav.surface|-|legacy-navigation|hold-alias
mibr-carplay111-safearea.conf|-|legacy-navigation|hold-alias
mibr-carplay111-url-map.enabled|-|legacy-navigation|hold-alias
mibr-alt111-keyframe-policy.enabled|config/features/keyframe-recovery.conf|boot-policy|convert-presence
mibr-carplay-autodirect.enabled|config/features/auto-direct.conf|boot-policy|convert-presence
mibr-carplay111-bit26.force-off|-|conflicting-polarity-markers|hold-conflict
mibr-carplay111-bit26.force-on|-|conflicting-polarity-markers|hold-conflict
mibr-carplay111-viewareas.enabled|config/features/view-areas.conf|legacy-activation|convert-presence
mibr-direct-output-fps|config/carplay/direct-output-fps.conf|legacy-frame-policy|preserve-scalar
mibr-isotx2-gate-disable|config/features/isotx2-gate.conf|early-boot-policy|convert-inverted-presence
mibr-parity-drive.enabled|config/features/parity-drive.conf|runtime-policy|preserve-scalar
mibr-parity-statistics-enabled|config/features/parity-statistics.conf|runtime-policy|convert-presence
mibr-parity-status-enabled|config/features/parity-status.conf|runtime-policy|convert-presence
mibr-rgi/rgi.on|config/features/rgi.conf|navigation-activation|convert-presence
mibr-carplay111-backup|-|legacy-backup-directory|hold-backup
mibr-gen2-backup|-|legacy-backup-directory|hold-backup
mibr-isotx2-gate-backup|-|early-boot-backup-directory|hold-backup
mibr-isotx2-gate-backup/startup.sh.stock|backup/early-boot/isotx2-startup.sh.stock|stock-boot-preimage|preserve-exact-original
mibr-pr93-visual-rollback.ksh|-|test-only-candidate|hold-unproven-runtime
mibr-deploy-most20-owned|version/ownership/most20.marker|installer-ownership-receipt|preserve-presence
mibr-deploy-navignore-owned|version/ownership/navignore.marker|installer-ownership-receipt|preserve-presence
mibr-kit/components.manifest|version/components.manifest|component-version-receipt|preserve-native
mibr-kit/installed-version.properties|version/installed-version.properties|product-version-receipt|preserve-native
altscreen-u2/config/mibr-v3-single-writer.enabled|-|early-boot-safety-gate|hold-exact-two-byte-contract
""".strip()


class PlanError(ValueError):
    pass


def require(ok, msg):
    if not ok:
        raise PlanError(msg)


def source_spec():
    specs = {}
    for line in ADDITIONAL_SPECS.splitlines():
        old, target, owner, policy = line.split("|")
        path = OLD + old
        require(path not in specs, "duplicate additional path")
        specs[path] = {"relative_target": None if target == "-" else target,
                       "owner_role": owner, "format_policy": policy}
    require(len(specs) == 37, "unexpected additional storage candidates")
    return specs


def valid_target(relative):
    return (relative is None
            or (isinstance(relative, str) and
                VALID_RELATIVE.fullmatch(relative) is not None and
                ".." not in relative and not relative.endswith(".tmp")))


def proposed(row, specs):
    path = row["current_path"]
    kind = row["kind"]
    if kind == "carplay-registry-group":
        basename = path.rsplit("/", 1)[-1]
        if basename.startswith("mibr-carplay111-"):
            name = basename[len("mibr-carplay111-"):]
        elif basename == "mibr-carplay-autodirect":
            name = "auto-direct"
        else:
            raise PlanError("unrecognized CarPlay store: " + path)
        require(re.fullmatch(r"[a-z0-9][a-z0-9.-]*", name) is not None,
                "unreviewed CarPlay group basename: " + name)
        relative = "config/carplay/" + (name if name.endswith(".conf")
                                         else name + ".conf")
        return relative, "carplay-registry", "registry-format-unqualified"
    if kind == "broker-durable-switch":
        key = row["logical_id"].removeprefix("broker:")
        require(key in review.BROKER_GROUPS and
                row["logical_id"] == "broker:" + key, "unmapped broker key")
        basename = path.rsplit("/", 1)[-1]
        require(basename.startswith("mibr-") and basename.endswith(".conf"),
                "unreviewed broker source name")
        relative = ("config/" + review.BROKER_GROUPS[key] + "/" +
                    basename[len("mibr-"):])
        return relative, "broker-exclusive-CAS-writer", "preserve-magic-revision-CAS"
    require(path in specs, "unclassified persistent candidate: " + path)
    item = specs[path]
    return item["relative_target"], item["owner_role"], item["format_policy"]


def build(graph, specs=None):
    if specs is None:
        specs = source_spec()
    require(graph["migration_authorized"] is False,
            "graph unexpectedly authorized runtime writes")
    require(len(graph["records"]) == 63, "source candidate count changed")
    require(len({r["current_path"] for r in graph["records"]}) == 63,
            "duplicate current storage paths")
    require(all(r["destination_path"] is None for r in graph["records"]),
            "unexpected independently authorized graph destination")
    require(all(not any(r[k] for k in (
        "one_actual_writer_verified", "every_reader_verified",
        "installed_boot_references_verified", "format_migration_verified",
        "upgrade_uninstall_rollback_verified")) for r in graph["records"]),
        "graph evidence state changed: review new proof before reusing plan")
    expected = {r["current_path"] for r in graph["records"]
                if r["kind"] not in ("carplay-registry-group",
                                     "broker-durable-switch")}
    require(set(specs) == expected and len(specs) == 37,
            "added/removed unreviewed legacy store or source classification")
    rows, targets = [], {}
    for original in sorted(graph["records"], key=lambda r: r["current_path"]):
        relative, owner, policy = proposed(original, specs)
        require(valid_target(relative), "unsafe/noncanonical target for " +
                original["current_path"])
        destination = NEW + relative if relative is not None else None
        if destination is not None:
            require(destination not in targets,
                    "two distinct stores share target: " + original["current_path"] +
                    " and " + targets.get(destination, "?"))
            targets[destination] = original["current_path"]
        if policy == "preserve-magic-revision-CAS":
            require(original["observed_format_identity"].startswith("MIBR_"),
                    "broker format provenance disappeared")
        if policy == "preserve-crc":
            require(original["current_path"].endswith("/mibr-menu.conf"),
                    "menu CRC owner drifted")
        rows.append({
            "current_path_candidate": original["current_path"],
            "source_kind": original["kind"],
            "logical_id": original.get("logical_id"),
            "owner_role": owner,
            "native_format_or_conversion_policy": policy,
            "candidate_destination_path": destination,
            "verified_destination_path": None,
            "requires_joint_reader_writer_cutover": destination is not None,
            "actual_writer_and_every_reader_qualified": False,
            "actual_boot_and_rollback_qualified": False,
            "candidate_not_migration_permission": True,
        })
    # Two names are related but are not the same file or grammar. Reject
    # future refactors which silently collapse them to one target.
    by_source = {r["current_path_candidate"]: r for r in rows}
    registry = by_source[OLD + "mibr-carplay-autodirect"]
    marker = by_source[OLD + "mibr-carplay-autodirect.enabled"]
    require(registry["candidate_destination_path"] !=
            marker["candidate_destination_path"], "Auto-Direct alias collision")
    require(by_source[OLD + "mibr-carplay111-bit26.force-on"]
            ["candidate_destination_path"] is None and
            by_source[OLD + "mibr-carplay111-bit26.force-off"]
            ["candidate_destination_path"] is None,
            "conflicting marker pair cannot be independently mapped")
    output = {
        "schema": 1,
        "kind": "source-derived-proposed-destination-names",
        "status": "PROPOSED_NOT_APPROVED_FOR_RUNTIME_MIGRATION",
        "counts": {
            "input_candidate_paths": len(rows),
            "canonical_carplay_groups": 13,
            "canonical_broker_CAS_files": 13,
            "additional_candidate_paths": len(specs),
            "target_names_proposed": len(targets),
            "held_without_target": len(rows) - len(targets),
            "unresolved_dynamic_source_leads":
                len(graph["unresolved_nonliteral_source_leads"]),
            "external_boot_restore_boundaries":
                len(graph["outside_project_boot_hook_restore_boundaries"]),
        },
        "records": rows,
        "unresolved_cross_layer_dependencies": [
            "installed firmware and generated C/Java/QNX/boot consumer closure",
            "CarPlay registry values versus separate legacy presence markers",
            "legacy nav files versus registry nav group: format and precedence",
            "retained original stock boot preimages and patch ownership",
            "single-writer activation, mount lease, RO/readback and power-loss recovery",
            "three exact firmware-specific profile adapters and installer lifecycle",
        ],
        "final_destination_reviewed": False,
        "migration_authorized": False,
    }
    return output


def require_migration_authorized(plan):
    if plan.get("migration_authorized") is not True or \
            plan.get("final_destination_reviewed") is not True:
        raise PlanError("A2/A3 proposal is not an authorized migration plan")
    raise PlanError("migration execution is intentionally not implemented here")


def self_test():
    graph = access.build(ROOT)
    plan = build(graph)
    assert plan["counts"]["input_candidate_paths"] == 63
    assert plan["counts"]["additional_candidate_paths"] == 37
    assert not plan["migration_authorized"]
    rows = {r["current_path_candidate"]: r for r in plan["records"]}
    assert rows[OLD + "altscreen-u2/config/mibr-menu.conf"][
        "native_format_or_conversion_policy"] == "preserve-crc"
    assert rows[OLD + "mibr-carplay-autodirect"]["candidate_destination_path"] == \
        NEW + "config/carplay/auto-direct.conf"
    assert rows[OLD + "mibr-carplay-autodirect.enabled"][
        "candidate_destination_path"] == NEW + "config/features/auto-direct.conf"
    assert rows[OLD + "mibr-alt111-keyframe-policy.enabled"][
        "native_format_or_conversion_policy"] == "convert-presence"
    assert rows[OLD + "mibr-carplay111-nav.surface"][
        "candidate_destination_path"] is None
    assert rows[OLD + "altscreen-u2/config/mibr-v3-single-writer.enabled"][
        "candidate_destination_path"] is None
    assert all(r["verified_destination_path"] is None for r in plan["records"])
    assert not valid_target("config/carplay/../bad.conf")
    assert not valid_target("/tmp/mibr-danger.conf")
    assert not valid_target("config/carplay/unsafe.tmp")
    for modifier in ("unknown", "collision", "unsafe", "completed"):
        altered = copy.deepcopy(graph)
        specs = copy.deepcopy(source_spec())
        if modifier == "unknown":
            altered["records"][0]["current_path"] = OLD + "unknown-new-file"
        elif modifier == "collision":
            specs[OLD + "altscreen-u2/config/mibr-menu-language.conf"][
                "relative_target"] = "config/menu/layout.conf"
        elif modifier == "unsafe":
            specs[OLD + "altscreen-u2/config/mibr-menu-language.conf"][
                "relative_target"] = "config/menu/../bad.conf"
        else:
            altered["migration_authorized"] = True
        try:
            build(altered, specs)
        except PlanError:
            pass
        else:
            raise AssertionError("unsafe source/target mutation passed: " + modifier)
    try:
        require_migration_authorized(plan)
    except PlanError:
        pass
    else:
        raise AssertionError("unqualified plan allowed file migration")
    print("STORAGE_DESTINATION_PLAN_SELF_TEST=PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--require-migration-ready", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    plan = build(access.build(ROOT))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(plan, sort_keys=True, indent=2) + "\n",
                                 encoding="utf-8")
    if args.require_migration_ready:
        require_migration_authorized(plan)
    print("STORAGE_DESTINATION_PLAN=PROPOSED " +
          json.dumps(plan["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
