#!/usr/bin/env python3
"""Deterministic source/target/config identity inputs for future versioned packages.

This does not assemble an installable kit, rewrite existing binaries or claim
a qualified target. External OEM inputs are never included. Only a later
package transaction may assign binary_set_id/package_id from actual bytes.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

BRANDS = frozenset(("GENERIC", "VW", "SKODA", "SEAT"))
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-(?:alpha|beta|rc)\.[0-9]+)?\Z")
COMPONENT = re.compile(r"[a-z][a-z0-9_-]*\Z")
GIT_SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")


def strict_pairs(pairs):
    output = {}
    for key, val in pairs:
        if key in output:
            raise ValueError("DUPLICATE_FIELD " + key)
        output[key] = val
    return output


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate_profile(profile):
    required = {"schema", "id", "brand", "qualification", "firmware_train",
                "mu_version", "cluster_family"}
    if set(profile) != required or type(profile["schema"]) is not int or profile["schema"] != 1:
        raise ValueError("TARGET_PROFILE_SCHEMA")
    if profile["brand"] not in BRANDS or not COMPONENT.fullmatch(profile["id"]):
        raise ValueError("TARGET_PROFILE_ID_OR_BRAND")
    for key in ("firmware_train", "mu_version", "cluster_family"):
        if profile[key] is not None and (not isinstance(profile[key], str) or
                                         not re.fullmatch(r"[A-Za-z0-9_]+", profile[key])):
            raise ValueError("TARGET_FINGERPRINT_FORMAT " + key)
    if profile["qualification"] not in ("unqualified", "source-reference", "vehicle-qualified"):
        raise ValueError("TARGET_QUALIFICATION")
    if profile["brand"] == "GENERIC" and (profile["qualification"] != "unqualified" or
        any(profile[k] is not None for k in ("firmware_train","mu_version","cluster_family"))):
        raise ValueError("GENERIC_CANNOT_ASSERT_TARGET")


def collect_configs(repo, manifest_path, brand):
    data = read_json(manifest_path)
    if set(data) != {"schema", "configurations"} or data["schema"] != 1 or not isinstance(data["configurations"], list):
        raise ValueError("CONFIG_INDEX_SCHEMA")
    result, seen = [], set()
    for item in data["configurations"]:
        if not isinstance(item, dict) or set(item) != {"path", "schema_version", "brand"}:
            raise ValueError("CONFIG_ENTRY_SCHEMA")
        rel = item["path"]
        if (not isinstance(rel, str) or not rel.endswith(".json") or
            rel.startswith("/") or "\\" in rel or any(part in ("", ".", "..") for part in rel.split("/")) or
            rel in seen):
            raise ValueError("CONFIG_PATH_OR_DUPLICATE")
        seen.add(rel)
        if item["brand"] not in BRANDS or item["brand"] not in ("GENERIC", brand):
            raise ValueError("CONFIG_BRAND_MISMATCH")
        if type(item["schema_version"]) is not int or item["schema_version"] < 1:
            raise ValueError("CONFIG_VERSION_INVALID")
        path = repo / rel
        if path.is_symlink() or not path.is_file():
            raise ValueError("CONFIG_MISSING_OR_SYMLINK " + rel)
        raw = path.read_bytes()
        original = json.loads(raw, object_pairs_hook=strict_pairs)
        if not isinstance(original, dict) or original.get("schema") != item["schema_version"]:
            raise ValueError("CONFIG_SCHEMA_DRIFT " + rel)
        result.append({"path": rel, "schema_version": item["schema_version"],
                       "brand": item["brand"], "size": len(raw), "sha256": digest(raw)})
    return sorted(result, key=lambda c: c["path"])


def make_identity(repo, version, source_commit, profile_path, config_index):
    if not VERSION.fullmatch(version) or not GIT_SHA.fullmatch(source_commit):
        raise ValueError("VERSION_OR_COMMIT_INVALID")
    if profile_path.is_symlink() or config_index.is_symlink():
        raise ValueError("INPUT_SYMLINK")
    profile_raw = profile_path.read_bytes()
    profile = json.loads(profile_raw, object_pairs_hook=strict_pairs)
    validate_profile(profile)
    if (repo / "target-profiles" / (profile["id"] + ".json")).resolve() != profile_path.resolve():
        raise ValueError("TARGET_PROFILE_NOT_CANONICAL")
    configs = collect_configs(repo, config_index, profile["brand"])
    return {"schema": 1, "product": "MIBR-CarPlay", "product_version": version,
            "source_commit": source_commit, "target_profile_id": profile["id"],
            "target_brand": profile["brand"], "target_qualification": profile["qualification"],
            "target_profile_sha256": digest(profile_raw), "configurations": configs,
            "binary_set_id": None, "package_id": None, "stage": "SOURCE_ONLY"}


def properties(identity):
    # Deliberately ASCII/Java-Properties-1.2-compatible; no implied installed state.
    keys = {"identity_schema": str(identity["schema"]), "product": identity["product"],
            "product_version": identity["product_version"],
            "source_commit": identity["source_commit"],
            "target_profile_id": identity["target_profile_id"],
            "target_brand": identity["target_brand"],
            "target_qualification": identity["target_qualification"],
            "target_profile_sha256": identity["target_profile_sha256"],
            "config_count": str(len(identity["configurations"])),
            "identity_stage": identity["stage"]}
    lines = [k + "=" + keys[k] + "\n" for k in sorted(keys)]
    for index, entry in enumerate(identity["configurations"]):
        # Path and digest stay in JSON; HMI uses a short, read-only display record.
        prefix = "config." + str(index) + "."
        lines.extend((prefix + "name=" + Path(entry["path"]).name + "\n",
                      prefix + "schema=" + str(entry["schema_version"]) + "\n",
                      prefix + "brand=" + entry["brand"] + "\n",
                      prefix + "sha256=" + entry["sha256"] + "\n"))
    return "".join(lines)


def elf_note(identity, component):
    if not COMPONENT.fullmatch(component):
        raise ValueError("COMPONENT_ID_INVALID")
    info = ("MIBR_BUILD_INFO:product=" + identity["product"] +
            ";version=" + identity["product_version"] + ";component=" + component +
            ";commit=" + identity["source_commit"] +
            ";target=" + identity["target_profile_id"] +
            ";brand=" + identity["target_brand"] + ";schema=1")
    return ('/* Generated source: opt-in for future binaries, not legacy 1.3.2. */\n'
            '__attribute__((used,section(".mibr.ident")))\n'
            'const char mibr_build_identity[] = ' + json.dumps(info) + ';\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--product-version", required=True)
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--target", required=True, type=Path, help="exact target profile JSON")
    ap.add_argument("--config-index", type=Path, default=Path("config-identity.json"))
    ap.add_argument("--component", help="optional future ELF component name")
    ap.add_argument("--out", type=Path, required=True, help="new empty output directory")
    opts = ap.parse_args(argv)
    repo = opts.repo.resolve()
    target = opts.target if opts.target.is_absolute() else repo / opts.target
    config = opts.config_index if opts.config_index.is_absolute() else repo / opts.config_index
    identity = make_identity(repo, opts.product_version, opts.source_commit, target, config)
    if opts.out.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS (never overwrite)")
    opts.out.mkdir(parents=True)
    (opts.out / "build-identity.json").write_text(
        json.dumps(identity, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (opts.out / "build-version.properties").write_text(properties(identity), encoding="ascii")
    if opts.component:
        (opts.out / "mibr_build_identity.c").write_text(elf_note(identity, opts.component), encoding="ascii")


if __name__ == "__main__":
    main()
