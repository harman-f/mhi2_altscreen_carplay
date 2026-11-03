#!/usr/bin/env python3
"""Host-only selected broker CAS, platform defaults and menu CRC source audit.

This checks local C/Java/shell formats and selected operations, not every
installed/firmware consumer or permission to migrate live persistent files.
"""
import argparse
import hashlib
import json
from pathlib import Path

import source_defaults_inventory as defaults
import storage_access_graph as access
import storage_consumer_crosscheck as crosscheck

ROOT = Path(__file__).resolve().parents[2]
BROKER = crosscheck.C
JAVA = crosscheck.J
PLATFORM_JAVA = crosscheck.PLATFORM
MENU_JAVA = crosscheck.JM
MENU_SH = crosscheck.LOADER
GEN2 = crosscheck.GEN2
MOUNT = "modules/broker/source/mibr-control/mibr_v3_qnx_mount.c"
SOURCES = (BROKER, JAVA, PLATFORM_JAVA, MENU_JAVA, MENU_SH, GEN2, MOUNT)

CHECKS = {
    BROKER: (
        "revision=%llu", "value=%s", "int mibr_switch_load(",
        "int mibr_switch_set(", "mibr_switch_valid(def,out->value)",
        "memcmp(raw,want,n)", "same(&now,observed)",
        "guard->enter_rw(guard->context)", "guard->restore_ro(guard->context)",
        "create_file(stage,buf,(size_t)n)||rename(stage,path)",
        "fsync(fd)", "sync_dir(path)", "mibr_switch_load(def,path,&confirm",
        "UNKNOWN_COMMIT", "STALE_REVISION",
        "fopen(mibr_switch_platform_path,",
    ),
    JAVA: (
        "new FileInputStream(f)", "persistedValue()",
        "this.magic=magic+", "revision=", "String parseValue(String text)",
        "if(stamp==fileStamp&&length==fileLength)return fileValue;",
        "if(text==null||!text.startsWith(magic))return defaultValue;",
        "for(int i=magic.length();i<end;i++)",
        "if(!rest.startsWith(", "rest.endsWith(",
    ),
    PLATFORM_JAVA: (
        "mibr-platform-defaults.conf", "if(text==null)text=read();",
        "String prefix=key+", "if(length<=0L||length>4096L)",
        "US-ASCII",
    ),
    MENU_JAVA: (
        "mibr-menu.conf", "MIBR_MENU/1", "TOO_LARGE",
        "crc32(file,at+1)", "CHECKSUM", "current=parse(read(storedPath))",
    ),
    MENU_SH: (
        "MIBR_MENU_DIR:-/mnt/app/root/altscreen-u2/config",
        "MIBR_APP_RW_LOCK:-/tmp/mibr-app-rw.lock",
        "lease_get(){", "mount -uw", "mount -ur",
        'STAGE="$DIR/mibr-menu.conf.new.$$"',
        'cp "$SRC" "$STAGE"', 'mv "$STAGE" "$DIR/mibr-menu.conf"',
    ),
    GEN2: ("mibr-platform-defaults.conf",),
    MOUNT: ("int mibr_v3_qnx_preflight(", "owner_marker()",
            "mibr_v3_recovery_check("),
}


class ContractError(ValueError):
    pass


def require(ok, msg):
    if not ok:
        raise ContractError(msg)


def read_sources(root=ROOT):
    return {p: (root / p).read_text(encoding="utf-8") for p in SOURCES}


def build(sources, canonical, graph, checked):
    require(canonical["counts"]["broker_switches"] == 13, "broker count drift")
    require(graph["migration_authorized"] is False, "migration state unexpectedly ready")
    require(graph["counts"]["canonical_broker_switches"] == 13, "broker access graph drift")
    hashes = {}
    for file, tokens in CHECKS.items():
        body = sources[file]
        for token in tokens:
            require(token in body, "source format/IO drift: " + file + " / " + token)
        hashes[file] = hashlib.sha256(body.encode()).hexdigest()
    c = sources[BROKER]
    j = sources[JAVA]
    # This is a concrete source grammar discrepancy, not an authorization
    # to alter deployed readers without coordinated firmware tests.
    require("if(!n||(n>1&&*s=='0'))return -1;" in c,
            "C canonical revision policy drift")
    require("for(int i=magic.length();i<end;i++)" in j,
            "Java revision digit reader drift")
    pairs = checked["broker_c_java_consistency"]
    require(len(pairs) == 13, "selected C/Java path/operation mismatch")
    by_path = {row["current_path"]: row for row in graph["records"]}
    broker_rows = []
    for pair in sorted(pairs, key=lambda p: p["path"]):
        p = pair["path"]
        require(p in by_path and by_path[p]["kind"] == "broker-durable-switch",
                "broker path missing/wrong owner: " + p)
        require(by_path[p]["destination_path"] is None, "unreviewed destination: " + p)
        broker_rows.append({
            "path": p,
            "magic": pair["magic"],
            "writer": "native-mibr_switch_set guarded CAS",
            "selected_reader": "Java persistedValue and native mibr_switch_load",
            "format": "MAGIC newline revision=N newline value=X newline",
            "native_canonical_revision": "decimal; leading zero rejected except zero",
            "local_writer_source_confirmed": True,
            "local_java_reader_source_confirmed": True,
            "all_firmware_and_legacy_readers_confirmed": False,
            "backup_upgrade_uninstall_confirmed": False,
            "destination": None,
        })
    pdefaults = canonical["broker"]["platform_override"]
    menu = "/mnt/app/root/altscreen-u2/config/mibr-menu.conf"
    require(pdefaults in by_path and menu in by_path,
            "platform/menu source absent from graph")
    return {
        "schema_version": 1,
        "kind": "selected-broker-menu-platform-source-format",
        "status": "PARTIAL_LOCAL_SOURCE_FORMAT_ONLY",
        "counts": {
            "broker_magic_revision_files": len(broker_rows),
            "menu_crc_file": 1,
            "platform_defaults_file": 1,
            "selected_file_contracts": len(broker_rows) + 2,
        },
        "source_sha256": hashes,
        "broker_records": broker_rows,
        "menu": {
            "path": menu,
            "local_reader": "Java MibrMenuLayout CRC32 and magic verification",
            "local_writer": "mibr-menu.ksh SD source stage+rename with app RW lease",
            "format": "MIBR_MENU/1 line-layout plus crc32 trailer",
            "shell_loader_proven_final_byte_readback": False,
            "other_readers_and_restore_complete": False,
        },
        "platform": {
            "path": pdefaults,
            "local_readers": ["broker-C defaults", "Java one-shot MibrPlatformDefaults",
                              "GEN2 native defaults"],
            "format": "capability=value per line with consumer-specific validation",
            "writer_or_platform_source_proven": False,
            "Java_default_reloads_after_start": False,
        },
        "findings": [
            "native C rejects revision 01 while Java parseValue accepts digit-only revision prefix; exact malformed-file handling differs",
            "Java persisted reader caches by file mtime+length, so same-tick same-size external updates can appear stale",
            "Java platform defaults are cached on first get; broker C re-opens per default lookup",
            "C broker writer has revision CAS, file/dir fsync, rename, guarded RW/RO and readback; this protection does not cover independent shell writers",
            "menu shell loader has app RW lock and stage+rename, while Java separately checks CRC; same-byte postwrite proof not shown by this source audit",
            "all installed/firmware readers, format migration, backup, recovery and target names remain unqualified",
        ],
        "migration_authorized": False,
    }


def completion_gate(report):
    if report["migration_authorized"] is not True or report["status"] != "ALL_RUNTIME_CONSUMERS_VERIFIED":
        raise ContractError("A2 broker/menu contracts are selected source evidence, not migration-ready")


def self_test():
    files = read_sources()
    reg = defaults.build(ROOT)
    graph = access.build(ROOT)
    cross = crosscheck.inspect(crosscheck.load(ROOT), reg)
    result = build(files, reg, graph, cross)
    assert result["counts"]["selected_file_contracts"] == 15
    assert len({row["path"] for row in result["broker_records"]}) == 13
    for file, old, new in (
        (BROKER, "sync_dir(path)", "sync_dir_missing(path)"),
        (BROKER, "same(&now,observed)", "same(&now,not_observed)"),
        (JAVA, "if(stamp==fileStamp&&length==fileLength)return fileValue;",
         "if(false)return fileValue;"),
        (PLATFORM_JAVA, "if(text==null)text=read();", "text=read();"),
        (MENU_JAVA, "crc32(file,at+1)", "crc32(file,0)"),
        (MENU_SH, 'STAGE="$DIR/mibr-menu.conf.new.$$"', 'STAGE="/tmp/stage"'),
    ):
        corrupted = dict(files)
        require(old in corrupted[file], "stale negative test input")
        corrupted[file] = corrupted[file].replace(old, new)
        try:
            build(corrupted, reg, graph, cross)
        except ContractError:
            pass
        else:
            raise AssertionError("accepted source drift in " + file)
    try:
        completion_gate(result)
    except ContractError:
        pass
    else:
        raise AssertionError("premature completion permitted")
    print("BROKER_MENU_STORAGE_FORMAT_SELF_TEST=PASS")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--json-out", type=Path)
    p.add_argument("--require-complete", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
    canonical = defaults.build(ROOT)
    report = build(read_sources(), canonical, access.build(ROOT),
                   crosscheck.inspect(crosscheck.load(ROOT), canonical))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                                 encoding="utf-8")
    if args.require_complete:
        completion_gate(report)
    print("BROKER_MENU_STORAGE_FORMAT=PARTIAL " +
          json.dumps(report["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
