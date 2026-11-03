#!/usr/bin/env python3
"""A2.3.2b: selected legacy navigation file IO contracts, host evidence only.

Safely pin the eight shell-composed persistent paths and the actual local
reader/writer/value semantics. This DOES NOT verify every installed consumer,
provide a coordinated mount lease, or authorize migration/vehicle changes.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import storage_access_graph

ROOT = Path(__file__).resolve().parents[2]
NAV = "modules/navigation/runtime/gen2_nav_config.sh"
SAFE = "modules/navigation/runtime/gen2_safearea.sh"
ROOT_PATH = "/mnt/app/root"
ASSIGNMENT = re.compile(r"^([A-Z][A-Z0-9_]*)=\$ROOT/([A-Za-z0-9_.-]+)$", re.M)

# One row per actual root+basename from these scripts. Tokens below are
# deliberately local source anchors, NOT an assertion of exclusive ownership.
SPECS = (
    {
        "id": "query", "source": NAV, "variable": "QUERY",
        "basename": "mibr-carplay111-nav-query.enabled",
        "format": "empty-file-presence-enables-URL-query",
        "writer": [': > "$QUERY"', 'rm -f "$QUERY"'],
        "reader": ['[ -e "$QUERY" ]', '[ ! -e "$QUERY" ]'],
        "local_writer_state": "create-empty-or-unlink",
        "local_read_state": "exists-vs-absent",
        "default": "disabled-when-absent",
    },
    {
        "id": "surface", "source": NAV, "variable": "SURFACE",
        "basename": "mibr-carplay111-nav.surface",
        "format": "first-line-string-enum-base-map-instructioncard",
        "writer": ['write_value "$SURFACE" "$1"', 'write_value "$SURFACE" base'],
        "reader": ['[ -r "$SURFACE" ]', 'read_value "$SURFACE" ""'],
        "local_writer_state": "newline-string-via-stage-rename",
        "local_read_state": "temp-override-before-persist-before-legacy-presence",
        "default": "base-unless-legacy-map-marker",
    },
    {
        "id": "eta", "source": NAV, "variable": "ETA",
        "basename": "mibr-carplay111-nav.showETA",
        "format": "first-line-tristate-yes-no-user",
        "writer": ['write_value "$ETA" yes', 'set_tristate "$ETA" "$2"'],
        "reader": ['read_value "$ETA" yes'],
        "local_writer_state": "newline-string-via-stage-rename",
        "local_read_state": "first-line-or-default",
        "default": "yes",
    },
    {
        "id": "speed", "source": NAV, "variable": "SPEED",
        "basename": "mibr-carplay111-nav.showSpeedLimit",
        "format": "first-line-tristate-yes-no-user",
        "writer": ['write_value "$SPEED" user', 'set_tristate "$SPEED" "$2"'],
        "reader": ['read_value "$SPEED" user'],
        "local_writer_state": "newline-string-via-stage-rename",
        "local_read_state": "first-line-or-default",
        "default": "user",
    },
    {
        "id": "compass", "source": NAV, "variable": "COMPASS",
        "basename": "mibr-carplay111-nav.showCompass",
        "format": "first-line-tristate-yes-no-user",
        "writer": ['write_value "$COMPASS" user', 'set_tristate "$COMPASS" "$2"'],
        "reader": ['read_value "$COMPASS" user'],
        "local_writer_state": "newline-string-via-stage-rename",
        "local_read_state": "first-line-or-default",
        "default": "user",
    },
    {
        "id": "maneuver", "source": NAV, "variable": "MANEUVER",
        "basename": "mibr-carplay111-nav.maneuverLayout",
        "format": "first-line-enum-none-left-right-top-normalized-from-aliases",
        "writer": ['write_value "$MANEUVER" "$val"', 'write_value "$MANEUVER" none'],
        "reader": ['read_value "$MANEUVER" none'],
        "local_writer_state": "newline-string-via-stage-rename",
        "local_read_state": "first-line-with-wire-alias-conversion",
        "default": "none",
    },
    {
        "id": "legacy-url-map", "source": NAV, "variable": "LEGACY_MAP",
        "basename": "mibr-carplay111-url-map.enabled",
        "format": "presence-only-fallback-selector",
        "writer": ['rm -f "$LEGACY_MAP"'],
        "reader": ['[ -e "$LEGACY_MAP" ]'],
        "local_writer_state": "only-removal-observed-other-creators-unresolved",
        "local_read_state": "fallback-when-surface-and-temp-override-unset",
        "default": "base-when-absent",
    },
    {
        "id": "safearea", "source": SAFE, "variable": "CONF",
        "basename": "mibr-carplay111-safearea.conf",
        "format": "four-newline-key-value-lines-x-y-w-h-uint-1010x376",
        "writer": ['tmp="$CONF.tmp.$$"', 'mv "$tmp" "$CONF"', 'rm -f "$CONF"'],
        "reader": ['[ -r "$CONF" ]', 'cat "$CONF"'],
        "local_writer_state": "newline-kv-rect-via-stage-rename-or-unlink",
        "local_read_state": "shell-status-displays-raw-file-compiled-consumer-unverified",
        "default": "0,0,1010,376-when-absent",
    },
)


class ContractError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise ContractError(reason)


def load(root):
    return {p: (root / p).read_text(encoding="utf-8") for p in (NAV, SAFE)}


def build(sources, graph):
    require(graph["migration_authorized"] is False,
            "unsafe: source graph claimed migration ready")
    require(graph["status"].startswith("PARTIAL"),
            "unexpected graph completeness")
    expected = {(s["source"], s["variable"]): s["basename"] for s in SPECS}
    require(len(SPECS) == 8 and len(expected) == 8, "duplicate navigation source owners")
    actual = {}
    source_hash = {}
    for file in (NAV, SAFE):
        text = sources[file]
        require(re.search(r"^ROOT=/mnt/app/root$", text, re.M) is not None,
                "persistent root changed: " + file)
        found = ASSIGNMENT.findall(text)
        require(len(found) == (7 if file == NAV else 1),
                "unreviewed added/removed navigation path: " + file)
        for variable, name in found:
            key = (file, variable)
            require(key in expected and name == expected[key],
                    "unknown/changed navigation path: " + file + ":" + variable)
            require(key not in actual, "duplicate navigation shell variable")
            actual[key] = name
        source_hash[file] = hashlib.sha256(text.encode()).hexdigest()
    require(actual == expected, "one or more navigation sources absent")
    known = {row["current_path"]: row for row in graph["records"]}
    require(all(not row["one_actual_writer_verified"]
                and not row["every_reader_verified"]
                for row in graph["records"]),
            "candidate graph already asserts complete runtime provenance")

    nav = sources[NAV]
    safe = sources[SAFE]
    core_nav_tokens = (
        'echo "$value" > "$tmp"', 'mv "$tmp" "$target"',
        "canonical_tristate(){", "yes|no|user)",
        "canonical_maneuver(){", "left|leftAligned)",
        'if [ -r "$VOLATILE_SURFACE" ]; then',
        'if [ -r "$SURFACE" ]; then',
        '[ -e "$LEGACY_MAP" ] && echo map || echo base',
        'target=$1', 'tmp="$target.tmp.$$"',
        'app_rw', 'app_ro', 'mount -uw /mnt/app',
        'mount -ur /mnt/app', 'trap app_ro 0 1 2 15',
    )
    require(all(t in nav for t in core_nav_tokens), "navigation value/root contract changed")
    core_safe_tokens = (
        'echo "x=$x"', 'echo "y=$y"', 'echo "w=$w"', 'echo "h=$h"',
        'validate_rect "$x" "$y" "$w" "$h"',
        '[ $((x+w)) -le "$FULL_W" ]', '[ $((y+h)) -le "$FULL_H" ]',
        'FULL_W=1010', 'FULL_H=376',
        'tmp="$CONF.tmp.$$"', 'mv "$tmp" "$CONF"', 'rm -f "$CONF"',
        'mount -uw /mnt/app', 'mount -ur /mnt/app',
        'apply=next_altScreen_info_handshake',
    )
    require(all(t in safe for t in core_safe_tokens), "safearea writer/format contract changed")

    # Profile writes at least five values before a single exit from app_rw;
    # they are not a cross-file atomic operation, regardless of each mv().
    profile = nav.split("set_profile(){", 1)
    require(len(profile) == 2, "profile writer missing")
    block = profile[1].split("apply_live(){", 1)
    require(len(block) == 2, "cannot bound navigation profile writer")
    for key in ("SURFACE", "ETA", "SPEED", "COMPASS", "MANEUVER"):
        require('write_value "$' + key + '"' in block[0],
                "profile transaction risk changed: " + key)

    source_rows = []
    for spec in SPECS:
        code = sources[spec["source"]]
        for role in ("writer", "reader"):
            for token in spec[role]:
                require(token in code, "missing selected " + role + ": " + spec["id"] + ": " + token)
        path = ROOT_PATH + "/" + spec["basename"]
        require(path in known, "source graph missing composed navigation path: " + path)
        require(known[path]["destination_path"] is None,
                "navigation source path incorrectly qualified for migration")
        source_rows.append({
            "id": spec["id"],
            "current_path": path,
            "source": spec["source"],
            "source_sha256": source_hash[spec["source"]],
            "variable": spec["variable"],
            "source_derived_content_format": spec["format"],
            "local_writer_semantics": spec["local_writer_state"],
            "local_read_semantics": spec["local_read_state"],
            "default_when_absent_or_unset": spec["default"],
            "source_writer_anchors": spec["writer"],
            "source_reader_anchors": spec["reader"],
            "local_writer_and_reader_contract_checked": True,
            "all_compiled_and_installed_consumers_verified": False,
            "single_global_authoritative_writer_verified": False,
            "original_bytes_and_metadata_backup_verified": False,
            "powerloss_and_rollback_verified": False,
            "destination_path": None,
            "migration_authorized": False,
        })
    return {
        "schema_version": 1,
        "kind": "selected-eight-legacy-navigation-local-io-contracts",
        "status": "PARTIAL_LOCAL_SCRIPT_CONTRACTS_ONLY",
        "source_sha256": source_hash,
        "counts": {
            "local_navigation_paths_checked": len(source_rows),
            "content_or_presence_files": len(source_rows),
            "non_atomic_profile_file_group": 5,
            "incomplete_global_reader_writer_paths": len(source_rows),
        },
        "records": source_rows,
        "observed_hazards": [
            "GEN2 navigation profile rewrites five separate files without a cross-file transaction",
            "legacy nav/safearea scripts remount /mnt/app without proven broker/shared RW lease",
            "persistent files receive no source-proven exact-byte backup, postwrite readback or RO verification",
            "legacy-map marker has only a removal writer in this script; other historical creators unresolved",
            "navigation query marker is presence-only; safearea is four newline-separated key-value fields",
            "safearea script displays raw stored file; compiled GEN2 reader and three firmware adapters remain unqualified",
            "navigation URL may be controlled by /tmp override ahead of stored surface and legacy marker",
        ],
        "migration_authorized": False,
    }


def must_be_complete(report):
    if report["migration_authorized"] is not True or report["status"] != "REVIEWED":
        raise ContractError("A2.3.2b not complete: firmware/installed/rollback evidence missing")


def self_test():
    files = load(ROOT)
    graph = storage_access_graph.build(ROOT)
    report = build(files, graph)
    assert report["counts"]["local_navigation_paths_checked"] == 8
    assert len({x["current_path"] for x in report["records"]}) == 8
    assert not report["migration_authorized"]
    assert any(r["id"] == "legacy-url-map"
               and r["local_writer_semantics"].startswith("only-removal")
               for r in report["records"])
    for path, old, new in (
        (NAV, 'SURFACE=$ROOT/mibr-carplay111-nav.surface',
         'SURFACE=$ROOT/mibr-carplay111-nav.wrong'),
        (NAV, '[ -e "$QUERY" ]', '[ -r "$QUERY" ]'),
        (NAV, 'rm -f "$LEGACY_MAP"', 'echo enabled > "$LEGACY_MAP"'),
        (NAV, 'write_value "$SPEED" user', 'write_value "$SPEED" yes'),
        (SAFE, 'mv "$tmp" "$CONF"', 'cp "$tmp" "$CONF"'),
        (SAFE, 'echo "w=$w"', 'echo "w=999"'),
    ):
        corrupt = dict(files)
        require(old in corrupt[path], "test fixture stale")
        corrupt[path] = corrupt[path].replace(old, new)
        try:
            build(corrupt, graph)
        except ContractError:
            pass
        else:
            raise AssertionError("negative source mutation accepted: " + path)
    extra = dict(files)
    extra[NAV] += "\nADDED=$ROOT/mibr-unknown.store\n"
    try:
        build(extra, graph)
    except ContractError:
        pass
    else:
        raise AssertionError("unknown persistent filename accepted")
    try:
        must_be_complete(report)
    except ContractError:
        pass
    else:
        raise AssertionError("local source-only evidence bypassed migration gate")
    print("LEGACY_NAV_STORAGE_SELF_TEST=PASS")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--json-out", type=Path)
    p.add_argument("--require-complete", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
    report = build(load(ROOT), storage_access_graph.build(ROOT))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    if args.require_complete:
        must_be_complete(report)
    print("LEGACY_NAV_STORAGE=PARTIAL " + json.dumps(report["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
