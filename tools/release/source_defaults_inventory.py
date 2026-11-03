#!/usr/bin/env python3
"""Host-only source-defined settings and literal on-unit path inventory.

This does not read effective values from a unit, migrate storage, or build an
installer. It records source ownership before any coordinated path migration.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = "settings/registry.json"
BROKER_C = "modules/broker/source/mibr-control/mibr_durable_switch.c"
BROKER_H = "modules/broker/source/mibr-control/mibr_durable_switch.h"
CATALOG = "tools/menu-editor/function-catalog.json"
MENU = "tools/menu-editor/standard-menu.txt"
INDEX = "modules/module-index.json"
INPUTS = (REGISTRY, BROKER_C, BROKER_H, CATALOG, MENU, INDEX)
LIFECYCLES = {"live", "session", "presentation", "reconnect", "unit_reboot"}
BROKER_LINE = re.compile(
    r'^[ \t]*\{"(?P<magic>MIBR_[A-Z0-9_]+/\d+)",'
    r'(?P<allowed>NULL|"[^"\n]*"),"(?P<default>[^"\n]+)",'
    r'CONFIG "(?P<file>[^"\n]+)","(?P<get>[A-Z0-9_]+)",'
    r'"(?P<set>[A-Z0-9_]+)","(?P<id>[a-z0-9_]+)",',
    re.M,
)
LITERAL_PATH = re.compile(
    r"/(?:mnt/app/root|tmp)/(?:mibr|altscreen-u2)[A-Za-z0-9_.$/{}/%+\-]*"
)
SCAN_ROOTS = ("modules", "runtime", "deployment", "src", "settings", "tools")
SCAN_EXTS = {".c", ".h", ".java", ".sh", ".ksh", ".py"}
# Audit generators contain documentation examples, not installed QNX paths.
SELF_AUDIT_TOOLS = {"tools/release/storage_migration_review.py",
                    "tools/release/storage_path_triage.py",
                    "tools/release/storage_consumer_crosscheck.py"}


class InventoryError(ValueError):
    pass


def require(test, message):
    if not test:
        raise InventoryError(message)


def read(root, relative):
    return (root / relative).read_text(encoding="utf-8")


def registry_inventory(data):
    require(data.get("schema") == 2, "unsupported CarPlay registry schema")
    require(data.get("layer_order") == ["temp", "persistent", "profile", "compiled"],
            "CarPlay setting precedence changed")
    entries = data.get("settings")
    require(isinstance(entries, list) and entries, "empty settings registry")
    presets = tuple(entries[0].get("default", {}))
    require(len(presets) == 3, "expected three explicit CarPlay presets")
    seen_keys, seen_fields, groups, records = set(), set(), {}, []
    for item in entries:
        key, base = item.get("key"), item.get("basename")
        field = item.get("field", "")
        require(isinstance(key, str) and key and key not in seen_keys,
                "duplicate or invalid registry key")
        require(isinstance(base, str) and re.fullmatch(r"[A-Za-z0-9_.-]+", base),
                "unsafe CarPlay storage basename: " + str(key))
        require(isinstance(field, str), "invalid field for " + key)
        require((base, field) not in seen_fields,
                "duplicate storage basename/field for " + key)
        defaults = item.get("default")
        require(isinstance(defaults, dict) and tuple(defaults) == presets,
                "incomplete preset defaults for " + key)
        require(item.get("apply") in LIFECYCLES,
                "missing or unknown apply lifecycle for " + key)
        require(item.get("read_only") in (True, False),
                "invalid read-only flag for " + key)
        allowed = item.get("allowed")
        if allowed is not None:
            require(isinstance(allowed, list) and bool(allowed),
                    "invalid allowed-values list for " + key)
        for preset, value in defaults.items():
            require(isinstance(value, str) and bool(value),
                    "empty/non-string default for " + key + "/" + preset)
            if allowed is not None:
                require(value in allowed, "disallowed default for " + key + "/" + preset)
            if item.get("type") == "integer":
                require(re.fullmatch(r"-?\d+", value) is not None,
                        "noninteger default for " + key)
                number = int(value)
                require(item.get("min", number) <= number <= item.get("max", number),
                        "integer default outside range for " + key)
        seen_keys.add(key)
        seen_fields.add((base, field))
        groups.setdefault(base, []).append(key)
        records.append({
            "key": key, "owner": "carplay", "current_basename": base,
            "field": field, "data_type": item.get("type"),
            "defaults_by_carplay_preset": defaults,
            "apply": item["apply"], "hmi": item.get("hmi"),
            "read_only": item["read_only"],
        })
    return {
        "layer_order": data["layer_order"], "carplay_presets": list(presets),
        "settings": records, "file_groups": dict(sorted(groups.items())),
        "source": REGISTRY,
    }


def broker_rectangle_valid(value):
    """Mirror mibr_durable_switch.c rect_valid() on the supported 1010x376 output."""
    parts = value.split(",")
    if len(parts) != 4:
        return False
    if any(re.fullmatch(r"(0|[1-9][0-9]*)", part) is None
           or len(part) > 5 for part in parts):
        return False
    x, y, width, height = (int(part) for part in parts)
    return (width >= 100 and height >= 60
            and x + width <= 1010 and y + height <= 376)


def broker_inventory(source, header):
    root = re.search(r'^#define CONFIG "([^"\n]+)"', source, re.M)
    count = re.search(r"^#define MIBR_SWITCH_COUNT (\d+)u$", header, re.M)
    require(root is not None and root.group(1).startswith("/mnt/app/root/"),
            "missing broker persistent config root")
    require(count is not None, "broker switch count not declared")
    entries = []
    used = set()
    for match in BROKER_LINE.finditer(source):
        m = match.groupdict()
        values = None if m["allowed"] == "NULL" else m["allowed"][1:-1].split("|")
        if values is not None:
            require(m["default"] in values, "invalid broker compiled default: " + m["id"])
        else:
            require(broker_rectangle_valid(m["default"]),
                    "invalid broker rectangle default: " + m["id"])
        require(m["id"] not in used, "duplicate broker capability: " + m["id"])
        require(re.fullmatch(r"[a-z0-9-]+\.conf", m["file"]) is not None,
                "invalid broker filename: " + m["id"])
        used.add(m["id"])
        entries.append({
            "key": m["id"], "owner": "broker",
            "magic": m["magic"], "compiled_default": m["default"],
            "allowed": values, "current_path": root.group(1) + m["file"],
            "get_operation": m["get"], "set_operation": m["set"],
            "storage_semantics": "broker-single-writer-revision-CAS",
        })
    require(len(entries) == int(count.group(1)),
            "broker declarations do not match MIBR_SWITCH_COUNT")
    require(len({e["current_path"] for e in entries}) == len(entries),
            "two broker switches share a storage file")
    return {
        "source": BROKER_C, "header": BROKER_H,
        "current_root": root.group(1),
        "platform_override": root.group(1) + "mibr-platform-defaults.conf",
        "switches": entries,
    }


def menu_inventory(menu, catalog, carplay, broker):
    lines = menu.splitlines()
    require(lines and lines[0] == "MIBR_MENU/1", "unsupported menu format")
    functions = catalog.get("functions")
    require(isinstance(functions, list), "missing menu function catalog")
    catalog_ids = [f["id"] for f in functions]
    require(len(set(catalog_ids)) == len(catalog_ids), "duplicate catalog IDs")
    ids = [line.split("\t", 1)[0] for line in lines if "\t" in line]
    require(len(ids) == len(set(ids)), "duplicate menu layout entries")
    require(set(ids) <= set(catalog_ids), "menu references unknown function IDs")
    cp_keys = {s["key"] for s in carplay["settings"]}
    broker_keys = {s["key"] for s in broker["switches"]}
    return {
        "source": MENU, "catalog_source": CATALOG,
        "brand_hint": next((line.split("=", 1)[1] for line in lines
                            if line.startswith("brand=")), "unknown"),
        "layout_entries": len(ids),
        "direct_carplay_bindings": sorted(set(ids) & cp_keys),
        "direct_broker_bindings": sorted(set(ids) & broker_keys),
        "other_menu_ids_no_direct_registry_key": sorted(
            set(ids) - cp_keys - broker_keys
        ),
        "note": "Menu presence, actions and aliases are not default values.",
    }


def literal_path_inventory(root):
    references, unresolved = [], []
    for dirname in SCAN_ROOTS:
        start = root / dirname
        if not start.is_dir():
            continue
        for path in sorted(start.rglob("*")):
            if not path.is_file() or path.suffix not in SCAN_EXTS:
                continue
            if path.resolve() == Path(__file__).resolve():
                continue
            if path.stat().st_size > 1_000_000:
                raise InventoryError("source unexpectedly large: " + str(path))
            relative = path.relative_to(root).as_posix()
            if relative in SELF_AUDIT_TOOLS:
                continue
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                if "/mnt/app/root" not in line and "/tmp/mibr" not in line:
                    continue
                paths = sorted(set(LITERAL_PATH.findall(line)))
                for match in paths:
                    references.append({
                        "literal_fragment": match,
                        "source": relative, "line": line_number,
                    })
                if not paths:
                    unresolved.append({"source": relative, "line": line_number})
    references.sort(key=lambda r: (r["literal_fragment"], r["source"], r["line"]))
    return {
        "evidence_grade": "literal-source-reference-only",
        "references": references, "unresolved_source_lines": unresolved,
        "warning": "Concatenated/generated paths and reader/writer roles require manual review.",
    }


def build(root=ROOT):
    source = {path: read(root, path) for path in INPUTS}
    registry = registry_inventory(json.loads(source[REGISTRY]))
    broker = broker_inventory(source[BROKER_C], source[BROKER_H])
    menu = menu_inventory(
        source[MENU], json.loads(source[CATALOG]), registry, broker
    )
    index = json.loads(source[INDEX])
    profiles = index["profiles"]
    require(len(profiles) == 3 and len(set(profiles)) == 3,
            "three mandatory firmware profiles not declared")
    return {
        "schema_version": 1,
        "kind": "source-defined-configuration-and-literal-path-inventory",
        "source_sha256": {
            p: hashlib.sha256(source[p].encode("utf-8")).hexdigest()
            for p in sorted(source)
        },
        "counts": {
            "carplay_settings": len(registry["settings"]),
            "carplay_storage_groups": len(registry["file_groups"]),
            "broker_switches": len(broker["switches"]),
            "menu_entries": menu["layout_entries"],
        },
        "firmware_profiles": profiles,
        "carplay": registry, "broker": broker, "menu": menu,
        "unit_path_evidence": literal_path_inventory(root),
        "effective_default_on_a_vehicle": "unknown-until-profile-preset-and-persisted-overrides-read",
        "migration_authorized": False,
    }


def rejects(action):
    try:
        action()
    except InventoryError:
        return
    raise AssertionError("negative fixture was accepted")


def self_test(root=ROOT):
    registry = json.loads(read(root, REGISTRY))
    broker = read(root, BROKER_C)
    header = read(root, BROKER_H)
    valid = build(root)
    assert valid["counts"]["carplay_settings"] == 48
    assert valid["counts"]["carplay_storage_groups"] == 13
    assert valid["counts"]["broker_switches"] == 13
    duplicate = copy.deepcopy(registry)
    duplicate["settings"].append(copy.deepcopy(duplicate["settings"][0]))
    rejects(lambda: registry_inventory(duplicate))
    invalid = copy.deepcopy(registry)
    invalid["settings"][1]["default"]["mibr_legacy"] = "bad-default"
    rejects(lambda: registry_inventory(invalid))
    rejects(lambda: broker_inventory(broker, header.replace("13u", "14u")))
    rejects(lambda: broker_inventory(
        broker.replace('"MIBR_CARPLAY_NAV/1","on|off","off"',
                       '"MIBR_CARPLAY_NAV/1","on|off","invalid"'), header
    ))
    original = '"MIBR_SAFE_VOLL/1",NULL,"0,58,1010,248"'
    for rejected_rect in ("0,58,1,1", "900,58,200,248", "00,58,100,248"):
        corrupted = broker.replace(
            original, '"MIBR_SAFE_VOLL/1",NULL,"' + rejected_rect + '"'
        )
        assert corrupted != broker
        rejects(lambda text=corrupted: broker_inventory(text, header))
    assert LITERAL_PATH.search("/mnt/app/root/mibr-carplay111-enabled") is not None
    assert LITERAL_PATH.search("/tmp/mibr-status") is not None
    assert not any(r["source"] in SELF_AUDIT_TOOLS
                   for r in valid["unit_path_evidence"]["references"])
    assert not any(r["source"] in SELF_AUDIT_TOOLS
                   for r in valid["unit_path_evidence"]["unresolved_source_lines"])
    print("SOURCE_DEFAULTS_INVENTORY_SELF_TEST=PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
    inventory = build()
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(inventory, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    print("SOURCE_DEFAULTS_INVENTORY=PASS " + json.dumps(inventory["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
