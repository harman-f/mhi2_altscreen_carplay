#!/usr/bin/env python3
"""Validate canonical module ownership and report dependency-aware change impact.

This is a source-layout gate, not a QNX build, release packager, or vehicle test.
"""
import argparse
import copy
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "modules" / "module-index.json"
OWNED_FIELDS = ("source", "runtime", "support_tools", "build_scripts")
VALID_STATES = {"indexed", "partially-migrated", "migrated"}


def path_valid(value):
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    p = PurePosixPath(value)
    return not p.is_absolute() and ".." not in p.parts and "." not in value.split("/")


def validate(doc, root=ROOT, check_files=True):
    errors = []
    mods = doc.get("modules")
    if doc.get("schema_version") != 1 or not isinstance(mods, dict) or not mods:
        return ["Expected schema_version=1 and a nonempty modules object"]
    owners = []
    outputs = set()
    for name, mod in mods.items():
        if mod.get("status") not in VALID_STATES:
            errors.append(f"{name}: invalid migration status")
        if not isinstance(mod.get("depends_on"), list):
            errors.append(f"{name}: depends_on must be a list")
        if not isinstance(mod.get("source"), list) or not mod["source"]:
            errors.append(f"{name}: source must be a nonempty list")
        if not isinstance(mod.get("distribution"), str) or not mod["distribution"].startswith("common/"):
            errors.append(f"{name}: missing common distribution owner")
        if not mod.get("build_coverage") or not mod.get("evidence"):
            errors.append(f"{name}: build coverage and evidence are required")
        for field in OWNED_FIELDS:
            for path in mod.get(field, []):
                if not path_valid(path):
                    errors.append(f"{name}: unsafe {field} path {path!r}")
                    continue
                if check_files and not (root / path).exists():
                    errors.append(f"{name}: absent {field} path {path}")
                for prior_owner, prior_path in owners:
                    if prior_owner != name and (
                        path == prior_path or path.startswith(prior_path + "/")
                        or prior_path.startswith(path + "/")
                    ):
                        errors.append(f"duplicate ownership: {prior_owner}/{prior_path} and {name}/{path}")
                owners.append((name, path))
        for output in mod.get("outputs", []):
            if not isinstance(output, str) or "/" in output or not output:
                errors.append(f"{name}: invalid output name {output!r}")
            elif (mod["distribution"], output) in outputs:
                errors.append(f"{name}: duplicated package output {output}")
            outputs.add((mod["distribution"], output))
        for dep in mod.get("depends_on", []):
            if dep not in mods or dep == name:
                errors.append(f"{name}: missing or self dependency {dep}")
    visited, active = set(), set()

    def visit(name):
        if name in active:
            errors.append(f"dependency cycle involving {name}")
            return
        if name in visited:
            return
        active.add(name)
        for dep in mods[name].get("depends_on", []):
            if dep in mods and dep != name:
                visit(dep)
        active.remove(name)
        visited.add(name)

    for name in mods:
        visit(name)
    profiles = doc.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != len(set(profiles)):
        errors.append("profiles must be unique")
    return errors


def impact(doc, files):
    mods = doc["modules"]
    directly = set()
    unowned = []
    for changed in files:
        matches = []
        for name, mod in mods.items():
            owned = [p for f in OWNED_FIELDS for p in mod.get(f, [])]
            if any(changed == p or changed.startswith(p + "/") for p in owned):
                matches.append(name)
        directly.update(matches)
        if not matches and changed.startswith(("src/", "runtime/", "settings/", "modules/")):
            # Ownership of a new or shared file must be explicitly reviewed.
            unowned.append(changed)
    affected = set(directly)
    while True:
        newly = {n for n, m in mods.items() if set(m["depends_on"]) & affected}
        if newly <= affected:
            break
        affected |= newly
    return sorted(affected), sorted(unowned)


def self_test(doc):
    assert not validate(doc), "current canonical module layout invalid"
    altered = copy.deepcopy(doc)
    altered["modules"]["broker"]["source"].append("src/native/altscreen111-gen2")
    assert any("duplicate ownership" in e for e in validate(altered, check_files=False))
    altered = copy.deepcopy(doc)
    altered["modules"]["carplay"]["depends_on"].append("menu")
    assert any("dependency cycle" in e for e in validate(altered, check_files=False))
    altered = copy.deepcopy(doc)
    altered["modules"]["carplay"]["source"].append("../unsafe")
    assert any("unsafe" in e for e in validate(altered, check_files=False))
    affected, unowned = impact(doc, ["src/native/mibr-control/mibr_v3_service.c"])
    assert affected == ["broker", "menu", "navigation"] and not unowned
    affected, unowned = impact(doc, ["src/native/unknown-core/new.c"])
    assert not affected and unowned == ["src/native/unknown-core/new.c"]
    print("MODULE_INDEX_SELF_TEST=PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--changed-files", nargs="+", metavar="PATH")
    args = parser.parse_args()
    doc = json.loads(INDEX.read_text(encoding="utf-8"))
    errors = validate(doc)
    if errors:
        for error in errors:
            print("MODULE_INDEX_ERROR:", error)
        raise SystemExit(1)
    print("MODULE_INDEX_CHECK=PASS")
    if args.self_test:
        self_test(doc)
    if args.changed_files:
        affected, unowned = impact(doc, args.changed_files)
        print("AFFECTED_MODULES=" + ",".join(affected))
        if unowned:
            print("UNOWNED_CHANGED_PATHS=" + ",".join(unowned))
            raise SystemExit(2)


if __name__ == "__main__":
    main()
