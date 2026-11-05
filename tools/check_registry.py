#!/usr/bin/env python3
"""Validate settings/registry.json (schema 3) and gate absolute storage paths.

Modes
  (default)      validate the registry, including drift against the durable
                 switch table in mibr_durable_switch.c
  --write        also (re)write settings/storage-paths.generated.json
  --check        also verify that file is current
  --scan-paths   scan source trees for absolute /mnt/app/root and /tmp/mibr
                 literals; each must be declared in the registry

Evidence: every storage group carries evidence {writer, format, ref}.
"source" means the writing code / format parser was read; "inferred" is a
best guess. Inferred entries must be confirmed before the group's M2 cutover.
The summary counts them but never fails on them.

Validation never uses assert, so it is unchanged under python3 -O.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "settings/registry.json"
C_TABLE = ROOT / "modules/broker/source/mibr-control/mibr_durable_switch.c"
STORAGE_OUT = ROOT / "settings/storage-paths.generated.json"

LAYER_ORDER = ["temp", "persistent", "preset", "compiled"]
EVIDENCE_WRITER = {"source", "inferred", "none-in-source"}
EVIDENCE_FORMAT = {"source", "inferred"}
FORMATS = {"presence", "value01", "keyvalue", "cas", "crc", "binary",
           "registry_group"}
NEW_ROOT = "/mnt/app/root/mibr/"
TARGET_PREFIXES = (NEW_ROOT, "/tmp/mibr-")
CURRENT_PREFIXES = ("/mnt/app/root/", "/tmp/mibr-")
GROUP_ID = re.compile(r"[a-z0-9_]+(?:\.[a-z0-9_]+)+")
SCAN_DIRS = ("modules", "tools", "deployment", "runtime")
SCAN_EXT = {".c", ".h", ".java", ".sh", ".ksh", ".py", ".awk", ".lua"}
SCAN_SKIP_DIRS = {".git", "build", "__pycache__", "node_modules"}
LITERAL = re.compile(r"(?:/mnt/app/root|/tmp/mibr)[A-Za-z0-9_./%*@+-]*")
ROW = re.compile(
    r'\{"(MIBR_[A-Z_]+/\d+)",(NULL|"[^"]*"),"([^"]*)",MIBR_CONFIG_DIR "([^"]+)",'
    r'"(\w+)","(\w+)","(\w+)"', re.S)
MAP_FILE = ROOT / "installer/config/root-migration.list"
LEGACY_ROOT = "/mnt/app/root/"


def load_json(path):
    def no_dupes(pairs):
        keys = [k for k, _ in pairs]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate JSON key in " + str(path))
        return dict(pairs)
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=no_dupes)


def parse_c_table(text):
    """Rows of mibr_switch_defs[] keyed by capability (== switch id)."""
    config = NEW_ROOT + "config"  # MIBR_CONFIG_DIR of mibr_paths.h
    rows = {}
    for m in ROW.finditer(text):
        magic, values, default, base, get_op, set_op, cap = m.groups()
        rows[cap] = {
            "magic": magic,
            "allowed": None if values == "NULL" else values.strip('"').split("|"),
            "default": default, "path": config + base,
            "basename": base.rsplit("/", 1)[-1],
            "get_op": get_op, "set_op": set_op}
    return rows


def load_map(path=None):
    """Rows of installer/config/root-migration.list: legacy_rel -> new_rel."""
    rows = {}
    for line in Path(path or MAP_FILE).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 3:
            rows[parts[0]] = parts[1]
    return rows


def check_map(reg, groups, rows=None):
    """Every group whose current_path is a map row must have exactly the map
    row's target; a group still on target "tbd" gets the map target."""
    errors = []
    try:
        rows = load_map() if rows is None else rows
    except OSError:
        return errors
    for gid, g in sorted(groups.items()):
        cur = g.get("current_path")
        if not isinstance(cur, str) or not cur.startswith(LEGACY_ROOT):
            continue
        rel = cur[len(LEGACY_ROOT):]
        if rel not in rows:
            continue
        want = NEW_ROOT + rows[rel]
        if g.get("target_path") != want:
            errors.append("%s: target_path %r != M1 map target %r (%s)"
                          % (gid, g.get("target_path"), want, rel))
    return errors


def _is_abs(path):
    return isinstance(path, str) and path.startswith("/") and "//" not in path \
        and "/../" not in path and not path.endswith("/..")


def validate(reg, c_text=None):
    """Return a list of error strings; empty means valid."""
    errors = []
    err = errors.append
    if type(reg.get("schema")) is not int or reg.get("schema") != 3:
        err("schema must be 3")
    if reg.get("layer_order") != LAYER_ORDER:
        err("layer_order must be %s" % LAYER_ORDER)
    for name, kind in (("settings", list), ("switches", list),
                       ("switches_pending", list), ("storage_groups", list),
                       ("oem_paths", list), ("migration_sources", list),
                       ("profile_defaults", dict), ("volatile_paths", list),
                       ("deployed_paths", list), ("path_templates", list),
                       ("scan_exempt", list)):
        if not isinstance(reg.get(name), kind):
            err("missing or mistyped top-level '%s'" % name)
    if errors and any("top-level" in e for e in errors):
        return errors
    if reg["profile_defaults"] != {}:
        err("profile_defaults must be empty until firmware profiles are defined")

    # storage groups
    groups, cur_seen, tgt_seen = {}, {}, {}
    for g in reg["storage_groups"]:
        gid = g.get("id") if isinstance(g, dict) else None
        if not isinstance(gid, str) or not GROUP_ID.fullmatch(gid):
            err("storage group with invalid id: %r" % (gid,))
            continue
        if gid in groups:
            err("duplicate storage group id: " + gid)
            continue
        groups[gid] = g
        cur, tgt = g.get("current_path"), g.get("target_path")
        if not _is_abs(cur) or not cur.startswith(CURRENT_PREFIXES):
            err("%s: current_path must be absolute under /mnt/app/root/ or "
                "/tmp/mibr-: %r" % (gid, cur))
        elif cur in cur_seen:
            err("%s and %s share current_path %s" % (cur_seen[cur], gid, cur))
        else:
            cur_seen[cur] = gid
        if tgt is None:
            if g.get("target") != "tbd":
                err("%s: null target_path needs \"target\": \"tbd\"" % gid)
        elif not _is_abs(tgt) or not tgt.startswith(TARGET_PREFIXES):
            err("%s: target_path must be under %s or /tmp/mibr-: %r"
                % (gid, NEW_ROOT, tgt))
        elif tgt in tgt_seen:
            err("%s and %s share target_path %s" % (tgt_seen[tgt], gid, tgt))
        else:
            tgt_seen[tgt] = gid
        if g.get("format") not in FORMATS:
            err("%s: format must be one of %s" % (gid, sorted(FORMATS)))
        ev = g.get("evidence")
        if not isinstance(ev, dict) or ev.get("writer") not in EVIDENCE_WRITER \
                or ev.get("format") not in EVIDENCE_FORMAT \
                or not isinstance(ev.get("ref"), str) or not ev["ref"]:
            err("%s: evidence needs writer in %s, format in %s and a ref"
                % (gid, sorted(EVIDENCE_WRITER), sorted(EVIDENCE_FORMAT)))
        elif (ev["writer"] == "none-in-source") != (g.get("writer") == "none-in-source"):
            err("%s: evidence.writer none-in-source must match writer" % gid)
        if "writers" in g or isinstance(g.get("writer"), (list, tuple, dict)):
            err("%s: exactly one writer allowed" % gid)
        elif not isinstance(g.get("writer"), str) or not g["writer"]:
            err("%s: exactly one writer required" % gid)

    # settings
    seen = set()
    for s in reg["settings"]:
        key = s.get("key")
        if key in seen:
            err("duplicate setting key: %r" % (key,))
        seen.add(key)
        if s.get("storage_group") not in groups:
            err("setting %r references unknown storage_group %r"
                % (key, s.get("storage_group")))

    # switches
    ids = set()
    for sw in reg["switches"]:
        sid = sw.get("id")
        if sid in ids:
            err("duplicate switch id: %r" % (sid,))
        ids.add(sid)
        grp = groups.get(sw.get("storage_group"))
        if grp is None:
            err("switch %r references unknown storage_group %r"
                % (sid, sw.get("storage_group")))
            continue
        if sw.get("writer") != grp.get("writer"):
            err("switch %r writer %r differs from group %s writer %r"
                % (sid, sw.get("writer"), grp["id"], grp.get("writer")))
        if grp.get("format") != sw.get("format"):
            err("switch %r format differs from its storage group" % (sid,))
    for pend in reg["switches_pending"]:
        if not isinstance(pend, dict) or not pend.get("id") or not pend.get("reason"):
            err("switches_pending entries need id and reason")
        elif pend["id"] in ids:
            err("switch %r is both active and pending" % pend["id"])
    pending = {p.get("id") for p in reg["switches_pending"] if isinstance(p, dict)}

    # consistency with the C table
    if c_text is not None:
        table = parse_c_table(c_text)
        if not table:
            err("no switch rows parsed from the C table")
        by_id = {sw.get("id"): sw for sw in reg["switches"]}
        for cap in sorted(set(table) - set(by_id) - pending):
            err("C table switch %s missing from registry switches" % cap)
        for sid in sorted(set(by_id) - set(table)):
            err("registry switch %s not in C table" % sid)
        for cap, row in table.items():
            sw = by_id.get(cap)
            if sw is None:
                continue
            for field in ("magic", "default", "get_op", "set_op", "basename"):
                if sw.get(field) != row[field]:
                    err("switch %s drifts from C table: %s %r != %r"
                        % (cap, field, sw.get(field), row[field]))
            if sw.get("allowed") != row["allowed"]:
                err("switch %s drifts from C table: allowed %r != %r"
                    % (cap, sw.get("allowed"), row["allowed"]))
            grp = groups.get(sw.get("storage_group"))
            if grp is not None and grp.get("target_path") != row["path"]:
                err("switch %s path drifts from C table: %r != %r"
                    % (cap, grp.get("target_path"), row["path"]))

    # M1 map <-> storage group agreement (location only)
    for msg in check_map(reg, groups):
        err(msg)

    # path lists
    for name in ("oem_paths", "migration_sources", "volatile_paths",
                 "deployed_paths", "path_templates"):
        for p in reg[name]:
            if not _is_abs(p):
                err("%s entry is not an absolute path: %r" % (name, p))
    for p in reg["oem_paths"]:
        if isinstance(p, str) and p.startswith(NEW_ROOT):
            err("oem_paths entry inside the project root: " + p)
    for p in reg["volatile_paths"]:
        if isinstance(p, str) and not p.startswith("/tmp/mibr"):
            err("volatile_paths entry outside /tmp/mibr: " + p)
    for p in reg["migration_sources"]:
        if isinstance(p, str) and p.startswith(NEW_ROOT):
            err("migration_sources entry inside the new root: " + p)
    return errors


def evidence_summary(reg):
    count = {"writer": {}, "format": {}}
    for g in reg["storage_groups"]:
        for k in count:
            v = g["evidence"][k]
            count[k][v] = count[k].get(v, 0) + 1
    return count


def storage_paths(reg):
    out = {}
    for g in reg["storage_groups"]:
        out[g["id"]] = {"current": g["current_path"], "target": g["target_path"],
                        "format": g["format"], "writer": g["writer"]}
    doc = {"schema": 1, "authority": "settings/registry.json (schema 3)",
           "groups": out}
    return json.dumps(doc, indent=2) + "\n"


# ---- path gate -----------------------------------------------------------

def normalize(literal):
    """Strip trailing separators so '/a/b/' and '/a/b.' compare as '/a/b'."""
    return literal.rstrip("./") or literal


def allowed_lookup(reg):
    exact = set(reg["volatile_paths"]) | set(reg["path_templates"])
    # A legacy location is a literal only while the group has no M1 target
    # (it stays where it is); otherwise it may be named solely in scan-exempt
    # legacy code (frozen release line, migrator).
    exact |= {g["current_path"] for g in reg["storage_groups"] if not g["target_path"]}
    exact |= {g["target_path"] for g in reg["storage_groups"] if g["target_path"]}
    exact |= set(reg["deployed_paths"])
    exact = {normalize(p) for p in exact}
    dirs = {normalize(g["current_path"]) for g in reg["storage_groups"]
            if g.get("is_dir")}
    dirs |= {normalize(g["target_path"]) for g in reg["storage_groups"]
             if g.get("is_dir") and g["target_path"]}
    dirs |= {normalize(p) for p in reg["deployed_paths"]}
    return exact, dirs


def is_allowed(literal, exact, dirs):
    lit = normalize(literal)
    if lit in exact:
        return True
    if any(lit.startswith(d + "/") for d in dirs):
        return True
    # A directory that is an ancestor of a declared path is just a root.
    return any(p.startswith(lit + "/") for p in exact)


def exempt(rel, reg):
    return any(rel.startswith(e["prefix"]) for e in reg["scan_exempt"])


def scan_files(root, reg):
    for top in SCAN_DIRS:
        for base, dirnames, files in os.walk(root / top):
            dirnames[:] = sorted(d for d in dirnames if d not in SCAN_SKIP_DIRS)
            for name in sorted(files):
                if os.path.splitext(name)[1] not in SCAN_EXT:
                    continue
                path = Path(base) / name
                rel = path.relative_to(root).as_posix()
                if not exempt(rel, reg):
                    yield rel, path


def scan_literals(root, reg):
    found = {}
    for rel, path in scan_files(root, reg):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for lit in LITERAL.findall(line):
                found.setdefault(lit, []).append((rel, lineno))
    return found


def scan_paths(reg, root=ROOT):
    exact, dirs = allowed_lookup(reg)
    offenders = []
    for lit, where in sorted(scan_literals(root, reg).items()):
        if not is_allowed(lit, exact, dirs):
            offenders.append((lit, where))
    return offenders


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--scan-paths", action="store_true")
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    args = ap.parse_args(argv)
    try:
        reg = load_json(args.registry)
        errors = validate(reg, C_TABLE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print("REGISTRY_CHECK=FAIL " + str(exc))
        return 1
    if errors:
        for e in errors:
            print("registry: " + e)
        print("REGISTRY_CHECK=FAIL errors=%d" % len(errors))
        return 1
    status = 0
    if args.scan_paths:
        offenders = scan_paths(reg)
        for lit, where in offenders:
            print("undeclared path %s (%s:%d%s)" % (
                lit, where[0][0], where[0][1],
                " +%d more" % (len(where) - 1) if len(where) > 1 else ""))
        if offenders:
            print("PATH_SCAN=FAIL offenders=%d" % len(offenders))
            return 1
        print("PATH_SCAN=PASS")
    data = storage_paths(reg)
    if args.write:
        STORAGE_OUT.write_text(data, encoding="utf-8", newline="\n")
    elif args.check:
        if not STORAGE_OUT.exists() or STORAGE_OUT.read_text(encoding="utf-8") != data:
            print("stale generated metadata: settings/storage-paths.generated.json")
            status = 1
    summ = evidence_summary(reg)
    print("EVIDENCE writer: %s; format: %s" % (
        ", ".join("%s=%d" % kv for kv in sorted(summ["writer"].items())),
        ", ".join("%s=%d" % kv for kv in sorted(summ["format"].items()))))
    if not status:
        print("REGISTRY_CHECK=PASS groups=%d switches=%d settings=%d" % (
            len(reg["storage_groups"]), len(reg["switches"]), len(reg["settings"])))
    return status


if __name__ == "__main__":
    sys.exit(main())
