#!/usr/bin/env python3
"""Load and validate modules/profiles/*/profile.json (schema_version 2).

Single loader for every tool that needs profile data (generator, release plan).
Owner decision E3: the only automatic selector is the SHA-256 of /ifs/lsd.jxe;
the firmware/train string is a plausibility cross-check, the API lsd.jar hash
is a separate field and never a selector. Host-only; reads source files only.
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEX = re.compile(r"^[a-f0-9]{64}$")
EVIDENCE = ("unit_measured", "firmware_corpus", "profile_source_unverified", "none")
ENABLING = ("unit_measured", "firmware_corpus")
ADAPTER_STATUS = ("none", "source", "built", "unit_tested")
JAR_STATUS = ("to_confirm", "confirmed")
FW_STATUS = ("defined", "to_define")
PID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+$")


def load_profiles(root=ROOT):
    """Return {profile_id: doc} for every modules/profiles/*/profile.json."""
    out = {}
    base = Path(root) / "modules/profiles"
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        f = d / "profile.json"
        if f.is_file():
            out[d.name] = json.loads(f.read_text(encoding="utf-8"))
    return out


def validate_profile(pid, doc):
    e = []
    def chk(cond, msg):
        if not cond:
            e.append(pid + ": " + msg)
    chk(doc.get("schema_version") == 2, "schema_version must be 2")
    chk(doc.get("profile_id") == pid, "profile_id/directory mismatch")
    sel = doc.get("selector")
    sel = sel if isinstance(sel, dict) else {}
    chk(sel.get("source") == "/ifs/lsd.jxe" and sel.get("algorithm") == "sha256", "selector must be sha256 of /ifs/lsd.jxe")
    dg = sel.get("digest")
    chk(isinstance(dg, str) and HEX.fullmatch(dg) is not None, "selector.digest must be 64 lowercase hex")
    ev = sel.get("evidence")
    chk(ev in EVIDENCE, "selector.evidence invalid")
    en = sel.get("install_enabled")
    chk(isinstance(en, bool), "selector.install_enabled must be bool")
    if isinstance(en, bool):
        chk(not en or ev in ENABLING, "install_enabled inconsistent with evidence")
    fc = doc.get("firmware_check")
    fc = fc if isinstance(fc, dict) else {}
    chk(fc.get("status") in FW_STATUS, "firmware_check.status invalid")
    if fc.get("status") == "defined":
        chk(isinstance(fc.get("source"), str) and fc["source"], "firmware_check.source required when defined")
        chk(isinstance(fc.get("expected"), str) and fc["expected"].startswith("MHI2_ER_"), "firmware_check.expected invalid")
    else:
        chk(fc.get("source") is None, "firmware_check.source must be null when to_define")
    if en is True:
        chk(fc.get("status") == "defined", "install_enabled requires a defined firmware_check")
    chk(fc.get("expected") in (None, doc.get("firmware")), "firmware_check.expected differs from firmware")
    hmi = doc.get("hmi")
    hmi = hmi if isinstance(hmi, dict) else {}
    jar = hmi.get("api_jar_sha256")
    chk(jar is None or (isinstance(jar, str) and HEX.fullmatch(jar) is not None), "hmi.api_jar_sha256 must be null or 64 hex")
    chk(hmi.get("api_jar_status") in JAR_STATUS, "hmi.api_jar_status invalid")
    if hmi.get("api_jar_status") == "confirmed":
        chk(jar is not None, "confirmed api jar needs a hash")
    chk(hmi.get("adapter") is None or isinstance(hmi.get("adapter"), str), "hmi.adapter must be null or class name")
    chk(hmi.get("adapter_from") is None or isinstance(hmi.get("adapter_from"), str), "hmi.adapter_from must be null or profile id")
    off = hmi.get("image_index_offset")
    chk(off is None or (isinstance(off, int) and not isinstance(off, bool)), "hmi.image_index_offset must be null or int")
    chk(doc.get("java", {}).get("adapter_status") in ADAPTER_STATUS, "java.adapter_status invalid")
    chk("adapter_note" in doc.get("java", {}), "java.adapter_note missing")
    items = doc.get("evidence")
    chk(isinstance(items, list) and items, "evidence list required")
    for it in items if isinstance(items, list) else []:
        ok = isinstance(it, dict) and isinstance(it.get("path"), str) and isinstance(it.get("kind"), str) \
            and (it.get("sha256") is None or (isinstance(it["sha256"], str) and HEX.fullmatch(it["sha256"])))
        chk(ok, "evidence entry needs path, kind, sha256 null|hex")
    if ev in ENABLING:
        chk(any(isinstance(i, dict) and i.get("sha256") == dg and i.get("kind") == ev for i in (items or [])),
            "enabling evidence must carry the selector digest with matching kind")
    return e


def validate_all(profiles):
    e = []
    seen = {}
    for pid, doc in profiles.items():
        e.extend(validate_profile(pid, doc))
        dg = doc.get("selector", {}).get("digest")
        if dg in seen:
            e.append("duplicate selector digest: %s, %s" % (seen[dg], pid))
        seen[dg] = pid
        af = doc.get("hmi", {}).get("adapter_from")
        if af is not None and (af not in profiles or af == pid):
            e.append(pid + ": hmi.adapter_from does not name another existing profile")
    for pid, doc in profiles.items():
        jar = doc.get("hmi", {}).get("api_jar_sha256")
        if jar and jar in seen:
            e.append(pid + ": api jar hash equals selector digest of " + seen[jar])
    return e


def self_test():
    profiles = load_profiles()
    assert profiles and not validate_all(profiles), validate_all(profiles)
    base = copy.deepcopy(profiles)
    sk, s9, s8 = "skoda-mu1440-p4526", "seat-mu1447-p4709", "seat-mu1409-p4708"
    def bad(fn, needle):
        p = copy.deepcopy(base)
        fn(p)
        errs = validate_all(p)
        assert any(needle in x for x in errs), (needle, errs)
    bad(lambda p: p[s9]["selector"].update(evidence="bogus"), "evidence invalid")
    bad(lambda p: p[s8]["selector"].update(evidence="profile_source_unverified", install_enabled=True), "inconsistent")
    disabled = copy.deepcopy(base)
    disabled[sk]["selector"]["install_enabled"] = False
    assert not validate_all(disabled), "verified evidence must not force installation enablement"
    bad(lambda p: p[sk]["selector"].update(digest="XYZ"), "64 lowercase hex")
    bad(lambda p: p[s8]["selector"].update(digest=p[sk]["selector"]["digest"]), "duplicate selector digest")
    bad(lambda p: p[s9]["hmi"].update(adapter_from="nope"), "adapter_from")
    bad(lambda p: p[s9]["hmi"].update(adapter_from=s9), "adapter_from")
    bad(lambda p: p[sk]["hmi"].update(api_jar_sha256=p[s9]["selector"]["digest"]), "equals selector digest")
    bad(lambda p: p[sk]["hmi"].update(api_jar_sha256="abc"), "api_jar_sha256")
    bad(lambda p: p[sk]["hmi"].update(api_jar_status="confirmed", api_jar_sha256=None), "needs a hash")
    bad(lambda p: p[sk]["java"].update(adapter_status="free text"), "adapter_status")
    bad(lambda p: p[sk].update(evidence=[]), "evidence list")
    bad(lambda p: p[sk].update(schema_version=1), "schema_version")
    def nofw(p):
        p[sk]["firmware_check"] = {"source": None, "expected": None, "status": "to_define"}
    bad(nofw, "requires a defined firmware_check")
    print("PROFILES_SELF_TEST=PASS")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    errors = validate_all(load_profiles())
    for x in errors:
        print("ERROR " + x, file=sys.stderr)
    if errors:
        raise SystemExit("PROFILES_CHECK=FAIL")
    if a.self_test:
        self_test()
    print("PROFILES_CHECK=PASS")


if __name__ == "__main__":
    main()
