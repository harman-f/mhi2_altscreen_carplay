#!/usr/bin/env python3
"""Host-only common beta profile plan. No on-target operations or release upload."""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import check_profiles  # noqa: E402  (single profile loader/validator)
GROUPS = ("hmi", "icons", "display", "input", "integration")
MODULES = ("carplay", "broker", "menu", "navigation")
SHA = re.compile(r"^[a-f0-9]{64}$")


def validate_profile(pid, doc, root=ROOT):
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(pid + ": " + message)
    check(doc.get("schema_version") == 2, "profile schema")
    check(doc.get("profile_id") == pid, "profile ID/directory mismatch")
    check(doc.get("brand") in ("skoda", "seat"), "unsupported brand")
    check(doc.get("firmware", "").startswith("MHI2_ER_"), "invalid firmware")
    check(doc.get("release_channel") == "beta", "must share beta release")
    check(doc.get("release_inclusion") == "required", "may not exclude profile")
    check(doc.get("structure_acceptance") == "assumed", "structure decision drift")
    check(doc.get("final_system_test") == "pending", "system test status unsupported")
    check(tuple(doc.get("common_modules", ())) == MODULES, "common module boundary")
    check(tuple(doc.get("groups", ())) == GROUPS, "asymmetric profile groups")
    selector = doc.get("selector", {})
    check(selector.get("source") == "/ifs/lsd.jxe" and selector.get("algorithm") == "sha256",
          "original LSD SHA-256 required")
    digest = selector.get("digest")
    check(isinstance(digest, str) and SHA.fullmatch(digest) is not None,
          "invalid fingerprint or missing mandatory beta fingerprint")
    java = doc.get("java", {})
    check(java.get("shared_source") == "modules/menu/source", "shared Java source duplicated")
    check(java.get("firmware_specific_updates_supported") is True, "Java adapter must remain replaceable")
    for group in GROUPS:
        check((root / "modules/profiles" / pid / group / "README.md").is_file(),
              "missing group " + group)
    return errors


def hash_copy_mismatches(profiles, root=ROOT):
    """K8: compare every known copy of the MU1440 selector digest."""
    errors = []
    skoda = profiles.get("skoda-mu1440-p4526", {}).get("selector", {}).get("digest")
    if not skoda:
        return ["MU1440 profile digest missing"]
    root = Path(root)
    copies = {}
    legacy = (root / "deployment/mu1440/install.sh").read_text(encoding="utf-8")
    m = re.search(r"^EXPECTED_LSD_JXE=([a-f0-9]{64})$", legacy, flags=re.M)
    copies["install.sh EXPECTED_LSD_JXE"] = m.group(1) if m else None
    cur = (root / "release/CURRENT.md").read_text(encoding="utf-8")
    m = re.search(r"exact LSD/J9 target hash:\s*`([a-f0-9]{64})`", cur)
    copies["release/CURRENT.md"] = m.group(1) if m else None
    readme = (root / "modules/profiles/README.md").read_text(encoding="utf-8")
    for pid, doc in profiles.items():
        row = re.search(r"^\| `%s` \|.*$" % re.escape(pid), readme, flags=re.M)
        want = doc["selector"]["digest"]
        if not row or want not in row.group(0):
            errors.append("profiles README digest mismatch for " + pid)
    for name, val in copies.items():
        if val != skoda:
            errors.append("K8 hash mismatch: profile.json=%s vs %s=%s" % (skoda, name, val))
    return errors


def build_plan(root=ROOT):
    index = json.loads((root / "modules/module-index.json").read_text(encoding="utf-8"))
    expected = index["profiles"]
    present = {p.name for p in (root / "modules/profiles").iterdir() if p.is_dir()}
    errors = [] if set(expected) == present else ["profile directory/declared profile mismatch"]
    profiles = check_profiles.load_profiles(root)
    errors.extend(check_profiles.validate_all(profiles))
    resolved = []
    for pid in expected:
        doc = profiles.get(pid)
        if doc is None:
            errors.append(pid + ": metadata missing")
            continue
        errors.extend(validate_profile(pid, doc, root))
        digest = doc.get("selector", {}).get("digest")
        resolved.append({
            "id": pid, "firmware": doc["firmware"], "brand": doc["brand"],
            "source": "modules/profiles/" + pid,
            "package": "profiles/" + pid,
            "lsd_sha256": digest,
            "firmware_sha256_input_needed": not bool(digest),
            "java_adapter_status": doc["java"]["adapter_status"],
            "evidence": doc["selector"]["evidence"],
            "install_enabled": doc["selector"]["install_enabled"],
            "release_channel": "beta", "include": True,
        })
    errors.extend(hash_copy_mismatches(profiles, root))
    return {
        "schema_version": 1,
        "release_channel": "beta",
        "profile_ids": expected,
        "common_modules": list(MODULES),
        "profiles": resolved,
        "missing_exact_firmware_hashes": [p["id"] for p in resolved if p["firmware_sha256_input_needed"]],
        "all_three_in_standard_beta_package": len(resolved) == 3 and all(p["include"] for p in resolved),
        "final_system_acceptance": "pending-for-whole-beta",
        "installer_zip_built": False,
        "errors": errors,
    }


def self_test():
    plan = build_plan()
    assert not plan["errors"], plan["errors"]
    assert plan["all_three_in_standard_beta_package"] and plan["release_channel"] == "beta"
    # All three mandatory beta profiles now have exact original LSD fingerprints.
    assert not plan["missing_exact_firmware_hashes"], "unresolved mandatory firmware selector"
    skoda = check_profiles.load_profiles()["skoda-mu1440-p4526"]
    for field, val, error in (("release_channel", "stable", "beta release"),
                               ("release_inclusion", "optional", "exclude profile")):
        bad = copy.deepcopy(skoda)
        bad[field] = val
        assert any(error in x for x in validate_profile(skoda["profile_id"], bad))
    bad = copy.deepcopy(skoda)
    bad["selector"]["digest"] = "not-a-hash"
    assert any("invalid fingerprint" in x for x in validate_profile(skoda["profile_id"], bad))
    bad["selector"]["digest"] = None
    assert any("missing mandatory beta fingerprint" in x for x in validate_profile(skoda["profile_id"], bad))
    profs = check_profiles.load_profiles()
    assert not hash_copy_mismatches(profs)
    profs = copy.deepcopy(profs)
    profs["skoda-mu1440-p4526"]["selector"]["digest"] = "0" * 64
    assert any("K8 hash mismatch" in x for x in hash_copy_mismatches(profs))
    bad = copy.deepcopy(skoda)
    bad["java"]["shared_source"] = "modules/profiles/skoda-mu1440-p4526/hmi"
    assert any("duplicated" in x for x in validate_profile(skoda["profile_id"], bad))
    print("MULTI_PROFILE_BETA_SELF_TEST=PASS")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()
    if args.self_test:
        self_test()
    plan = build_plan()
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(plan, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, sort_keys=True, indent=2))
    if plan["errors"]:
        raise SystemExit("MULTI_PROFILE_BETA_PLAN=FAIL")
    print("MULTI_PROFILE_BETA_PLAN=PASS")


if __name__ == "__main__":
    main()
