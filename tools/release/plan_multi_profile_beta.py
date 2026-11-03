#!/usr/bin/env python3
"""Host-only common beta profile plan. No on-target operations or release upload."""
import argparse
import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GROUPS = ("hmi", "icons", "display", "input", "integration")
MODULES = ("carplay", "broker", "menu", "navigation")
SHA = re.compile(r"^[a-f0-9]{64}$")


def validate_profile(pid, doc, root=ROOT):
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(pid + ": " + message)
    check(doc.get("schema_version") == 1, "profile schema")
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
    check(digest is None or (isinstance(digest, str) and SHA.fullmatch(digest) is not None),
          "invalid fingerprint (never invent a placeholder)")
    java = doc.get("java", {})
    check(java.get("shared_source") == "modules/menu/source", "shared Java source duplicated")
    check(java.get("firmware_specific_updates_supported") is True, "Java adapter must remain replaceable")
    for group in GROUPS:
        check((root / "modules/profiles" / pid / group / "README.md").is_file(),
              "missing group " + group)
    return errors


def build_plan(root=ROOT):
    index = json.loads((root / "modules/module-index.json").read_text(encoding="utf-8"))
    expected = index["profiles"]
    present = {p.name for p in (root / "modules/profiles").iterdir() if p.is_dir()}
    errors = [] if set(expected) == present else ["profile directory/declared profile mismatch"]
    known = {}
    resolved = []
    for pid in expected:
        path = root / "modules/profiles" / pid / "profile.json"
        if not path.is_file():
            errors.append(pid + ": metadata missing")
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        errors.extend(validate_profile(pid, doc, root))
        digest = doc.get("selector", {}).get("digest")
        if digest:
            if digest in known:
                errors.append("duplicate firmware fingerprints: " + pid + ", " + known[digest])
            known[digest] = pid
        resolved.append({
            "id": pid, "firmware": doc["firmware"], "brand": doc["brand"],
            "source": "modules/profiles/" + pid,
            "package": "profiles/" + pid,
            "lsd_sha256": digest,
            "firmware_sha256_input_needed": not bool(digest),
            "java_adapter_status": doc["java"]["adapter_status"],
            "release_channel": "beta", "include": True,
        })
    skoda = next((x for x in resolved if x["id"] == "skoda-mu1440-p4526"), None)
    legacy = (root / "deployment/mu1440/install.sh").read_text(encoding="utf-8")
    pinned = re.search(r"^EXPECTED_LSD_JXE=([a-f0-9]{64})$", legacy, flags=re.M)
    if not skoda or not pinned or pinned.group(1) != skoda["lsd_sha256"]:
        errors.append("MU1440 pinned original LSD fingerprint mismatch")
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
    # An exact MU1409 hash may be added without changing this test or the release design.
    assert set(plan["missing_exact_firmware_hashes"]) <= {"seat-mu1409-p4708"}
    skoda = json.loads((ROOT / "modules/profiles/skoda-mu1440-p4526/profile.json").read_text())
    for field, val, error in (("release_channel", "stable", "beta release"),
                               ("release_inclusion", "optional", "exclude profile")):
        bad = copy.deepcopy(skoda)
        bad[field] = val
        assert any(error in x for x in validate_profile(skoda["profile_id"], bad))
    bad = copy.deepcopy(skoda)
    bad["selector"]["digest"] = "not-a-hash"
    assert any("invalid fingerprint" in x for x in validate_profile(skoda["profile_id"], bad))
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
