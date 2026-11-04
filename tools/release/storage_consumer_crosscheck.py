#!/usr/bin/env python3
"""Cross-check selected actual C/Java/QNX consumers. Partial, host-only evidence."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import sys

# Sibling tools are imported by name; keep that working under `python3 -I`,
# which drops the script directory from sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import source_defaults_inventory as inv

ROOT = Path(__file__).resolve().parents[2]
C = "modules/broker/source/mibr-control/mibr_durable_switch.c"
J = "modules/menu/source/java/de/mibr/hmi/MibrDurableSwitch.java"
PLATFORM = "modules/menu/source/java/de/mibr/hmi/MibrPlatformDefaults.java"
JM = "modules/menu/source/java/de/mibr/hmi/MibrMenuLayout.java"
LOADER = "modules/broker/runtime/mibr-control/mibr-menu.ksh"
SETTINGS = "modules/carplay/source/alt111-settings/settings_posix.c"
CLIENTS = ("modules/carplay/source/alt111-settings/settings_cli.c",
           "modules/broker/source/mibr-control/mibr_control.c",
           "modules/broker/source/mibr-control/mibr_v3_service.c")
GEN2 = "modules/carplay/source/altscreen111-gen2/libaltscreen111_gen2.c"
PARITY = "modules/carplay/source/parity-session/parity_session.c"
ENABLE = "modules/carplay/runtime/parity/parity_drive_enable.sh"
DISABLE = "modules/carplay/runtime/parity/parity_drive_disable.sh"
INPUTS = (C, J, PLATFORM, JM, LOADER, SETTINGS, *CLIENTS, GEN2, PARITY, ENABLE, DISABLE)
PATTERN = re.compile(
    r'new\s+MibrDurableSwitch\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*'
    r'"([^"]+)"\s*,\s*"([^"]+)"', re.S)
PAIR = re.compile(r'\{\s*"/tmp"\s*,\s*"/mnt/app/root"\s*\}')


class ContractError(ValueError):
    pass


def check(ok, why):
    if not ok:
        raise ContractError(why)


def load(root):
    return {p: (root / p).read_text(encoding="utf-8") for p in INPUTS}


def inspect(source, inventory):
    original = inventory["broker"]["switches"]
    j = source[J]
    matches = PATTERN.findall(j)
    check(len(original) == 13 and len(matches) == 13, "broker/Java count drift")
    by_id = {item[3]: item for item in matches}
    check(len(by_id) == 13, "duplicate Java capability")
    check("new FileInputStream(f)" in j and "persistedValue()" in j,
          "Java direct reader absent")
    check(not any(t in j for t in ("FileOutputStream", "FileWriter", "RandomAccessFile")),
          "Java switch class may have gained a writer")
    c = source[C]
    check("int mibr_switch_set(" in c and "guard->enter_rw" in c
          and "guard->restore_ro" in c, "broker write guard missing")
    rows = []
    for item in sorted(original, key=lambda x: x["key"]):
        key = item["key"]
        check(key in by_id, "missing Java switch: " + key)
        path, magic, verb, capability = by_id[key]
        check(path == item["current_path"], "C/Java path mismatch: " + key)
        check(magic == item["magic"], "C/Java magic mismatch: " + key)
        check(verb + "_GET" == item["get_operation"]
              and verb + "_SET" == item["set_operation"],
              "C/Java operations mismatch: " + key)
        rows.append({
            "capability": capability, "path": path, "magic": magic,
            "observed_broker_writer_api": "mibr_switch_set()",
            "observed_java_reader": "MibrDurableSwitch.persistedValue()",
            "other_consumers_exhaustively_audited": False,
        })
    platform = inventory["broker"]["platform_override"]
    check(all(platform in source[p] for p in (C, PLATFORM, GEN2)),
          "platform defaults consumer drift")
    menu = "/mnt/app/root/altscreen-u2/config/mibr-menu.conf"
    check('STORED="' + menu + '"' in source[JM], "Java menu path drift")
    loader = source[LOADER]
    check("MIBR_MENU_DIR:-/mnt/app/root/altscreen-u2/config" in loader
          and '"$DIR/mibr-menu.conf"' in loader
          and 'STAGE="$DIR/mibr-menu.conf.new.$$"' in loader,
          "shell menu loader path drift")
    cp = source[SETTINGS]
    check(all(s in cp for s in (
        "path_for(path, sizeof(path), p->persistent, group_name(group))",
        "path_for(path, sizeof(path), p->temp, group_name(group))",
        "POLICY_BLOCKED persistent_backup_powerloss_gate"
    )), "layered CarPlay settings or hard stop drift")
    check(all(PAIR.search(source[p]) for p in CLIENTS),
          "broker/settings CLI CarPlay roots drift")
    check('#define MIBR_CFG_PERSIST_ROOT "/mnt/app/root"' in source[GEN2],
          "GEN2 CarPlay root drift")
    check('#define SETTINGS_PERSIST_ROOT "/mnt/app/root"' in source[PARITY],
          "parity CarPlay root drift")
    check('echo 1 > "$ENABLE"' in source[ENABLE]
          and 'echo 0 > "$ENABLE"' in source[DISABLE],
          "parity value-bearing .enabled toggle drift")
    return {
        "schema_version": 1, "kind": "selected-consumer-evidence-not-exhaustive",
        "source_sha256": {p: hashlib.sha256(source[p].encode()).hexdigest()
                          for p in sorted(source)},
        "broker_c_java_consistency": rows,
        "shared_reader_paths": [
            {"path": platform, "source_evidence": [C, PLATFORM, GEN2],
             "all_readers_verified": False},
            {"path": menu, "source_evidence": [JM, LOADER],
             "all_readers_verified": False}
        ],
        "carplay_grouped_store": {
            "layered_roots": ["/tmp", "/mnt/app/root"],
            "path_joiner": SETTINGS,
            "selected_consumer_sources": [*CLIENTS, GEN2, PARITY],
            "persistent_mutation": "POLICY_BLOCKED",
            "dynamic_paths_fully_audited": False,
        },
        "risk": {
            "path": "/mnt/app/root/mibr-parity-drive.enabled",
            "source_evidence": [ENABLE, DISABLE],
            "written_values": ["1", "0"],
            "note": ".enabled filename does not imply presence-only semantics"
        },
        "counts": {"matched_broker_switches": len(rows),
                   "cross_checked_other_paths": 2,
                   "carplay_root_consumers": len(CLIENTS) + 2},
        "migration_authorized": False, "completeness": "PARTIAL"
    }


def self_test(files, inventory):
    result = inspect(files, inventory)
    assert result["counts"]["matched_broker_switches"] == 13
    for file, old, new in (
        (J, "/mnt/app/root/altscreen-u2/config/mibr-carplay-nav.conf",
         "/mnt/app/root/altscreen-u2/config/wrong-nav.conf"),
        (JM, "/mnt/app/root/altscreen-u2/config/mibr-menu.conf",
         "/mnt/app/root/altscreen-u2/config/wrong-menu.conf"),
        (SETTINGS, "POLICY_BLOCKED persistent_backup_powerloss_gate", "REMOVED"),
    ):
        bad = dict(files)
        assert old in bad[file]
        # For a repeated guard, remove every occurrence: a single surviving
        # call must not mask a missing check on another persistent path.
        bad[file] = bad[file].replace(old, new)
        try:
            inspect(bad, inventory)
        except ContractError:
            pass
        else:
            raise AssertionError("negative contract fixture accepted: " + file)
    print("STORAGE_CONSUMER_CROSSCHECK_SELF_TEST=PASS")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--json-out", type=Path)
    args = p.parse_args()
    files, data = load(ROOT), inv.build(ROOT)
    if args.self_test:
        self_test(files, data)
    out = inspect(files, data)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")
    print("STORAGE_CONSUMER_CROSSCHECK=PARTIAL " +
          json.dumps(out["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
