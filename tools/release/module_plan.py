#!/usr/bin/env python3
"""Classify release/build impact using canonical module ownership (HOST ONLY).

The plan is advisory about which existing CI builds are relevant; it is never
an authorization to publish an installer or evidence of target qualification.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from check_module_index import impact, validate  # noqa: E402

ALWAYS_REVIEW = (
    "modules/module-index.json", "modules/profiles/", "settings/",
    "runtime/diagnostics/", "runtime/deployment/",
    "tools/release/", "tools/prepare_mu1440_sd.sh",
    "tools/validate_modular_package.py", "tools/check_mu1440_target_shell.py",
    "deployment/", "artifacts/mu1440/", "release/", "sd/",
    ".github/workflows/release-mu1440-aid10.yml",
)
BUILD_ALL = ("modules/module-index.json", "settings/")
RELEASE_CONTRACT = ("docs/build/PACKAGE_LAYOUT.md", "docs/testing/MU1440_QNX_SHELL_COMPATIBILITY.md")


def classify(index: dict, changed: list[str], all_inputs: bool = False) -> dict:
    modules = sorted(index["modules"])
    changed = sorted(set(changed))
    direct = set()
    affected = set()
    unowned = set()
    for path in changed:
        a, u = impact(index, [path])
        affected.update(a)
        unowned.update(u)
        for name, spec in index["modules"].items():
            owned = sum((spec.get(k, []) for k in ("source", "runtime", "build_scripts", "support_tools")), [])
            if any(path == prefix or path.startswith(prefix.rstrip("/") + "/") for prefix in owned):
                direct.add(name)
    if all_inputs or any(p == "modules/module-index.json" or p.startswith("settings/") for p in changed):
        direct.update(modules)
        affected.update(modules)
        # The module index itself is global metadata, not an unowned module.
        unowned.discard("modules/module-index.json")
    for p in changed:
        if p.startswith(("settings/", "runtime/diagnostics/", "runtime/deployment/")):
            # Registry-generated files, diagnosis and deployment scripts are
            # deliberate shared inputs outside any functional module. Unknown
            # paths in an actual modules/ owner remain hard failures.
            unowned.discard(p)
        if p.startswith("modules/profiles/"):
            unowned.discard(p)  # profile layout metadata, not a ready profile build
        if p == "modules/README.md" or any(
            p == f"modules/{name}/README.md" for name in index["modules"]
        ):
            unowned.discard(p)  # module owner metadata, not a source input
        # Any unowned file inside an actual module remains a hard failure.
    gate = bool(all_inputs or affected or any(
        p == x or p.startswith(x) for p in changed for x in ALWAYS_REVIEW
    ) or any(p in RELEASE_CONTRACT for p in changed))
    return {
        "schema_version": 1,
        "changed_files": changed,
        "direct_modules": sorted(direct),
        "affected_modules": sorted(affected),
        "unknown_owner_paths": sorted(unowned),
        "run_release_checks": gate,
        "r3_publish_qualified": False,
        "note": "Dependency impact is not proof of a build, complete source lineage, or a qualified release.",
    }


def self_test(index: dict) -> None:
    x = classify(index, ["modules/carplay/source/altscreen111-gen2/alt111.c"])
    assert x["affected_modules"] == ["broker", "carplay", "menu", "navigation"], x
    x = classify(index, ["modules/broker/source/mibr-control/mibr_control.c"])
    assert x["affected_modules"] == ["broker", "menu", "navigation"], x
    x = classify(index, ["modules/navigation/runtime/gen2_nav_config.sh"])
    assert x["direct_modules"] == ["navigation"], x
    x = classify(index, ["modules/carplay/source/new-not-declared/new.c"])
    assert x["unknown_owner_paths"], x
    x = classify(index, ["modules/module-index.json"])
    assert x["affected_modules"] == sorted(index["modules"]) and not x["unknown_owner_paths"], x
    x = classify(index, ["settings/registry.json", "settings/hmi-bindings.generated.json",
                         "settings/runtime-basenames.generated.sh"])
    assert x["affected_modules"] == sorted(index["modules"]) and not x["unknown_owner_paths"], x
    x = classify(index, ["runtime/deployment/session.sh", "runtime/diagnostics/gen2_status.sh"])
    assert x["run_release_checks"] and not x["unknown_owner_paths"], x
    x = classify(index, ["modules/README.md", "modules/carplay/README.md"])
    assert not x["unknown_owner_paths"], x
    x = classify(index, ["modules/carplay/unlisted/new.c"])
    assert x["unknown_owner_paths"] == ["modules/carplay/unlisted/new.c"], x
    x = classify(index, ["sd/manifest.json"])
    assert x["run_release_checks"] and not x["unknown_owner_paths"], x
    x = classify(index, ["README.md"])
    assert not x["run_release_checks"], x
    print("RELEASE_MODULE_PLAN_SELF_TEST=PASS")


def diff_names(base: str, head: str) -> list[str]:
    if not base or not head or set(base) == {"0"}:
        raise ValueError("requires non-empty exact base/head git revisions")
    raw = subprocess.check_output(["git", "diff", "--name-only", "--no-renames", "-z", base, head], cwd=ROOT)
    return [p.decode("utf-8") for p in raw.split(b"\0") if p]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base")
    ap.add_argument("--head")
    ap.add_argument("--all", action="store_true", help="manual full-source readiness check")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()
    index = json.loads((ROOT / "modules/module-index.json").read_text())
    errors = validate(index)
    if errors:
        raise SystemExit("Module owner contract invalid: " + "; ".join(errors))
    if args.self_test:
        self_test(index)
    if not (args.base and args.head or args.all):
        if args.self_test:
            return
        ap.error("specify --base and --head, or --all")
    files = diff_names(args.base, args.head) if not args.all else []
    plan = classify(index, files, all_inputs=args.all)
    print(json.dumps(plan, indent=2, sort_keys=True))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write("### Release module impact\n")
            out.write("Direct: " + ", ".join(plan["direct_modules"]) + "\n\n")
            out.write("Dependent: " + ", ".join(plan["affected_modules"]) + "\n\n")
            out.write("R3 qualification: BLOCKED (requires final assembled profile ZIP and hardware evidence)\n")
    if plan["unknown_owner_paths"]:
        raise SystemExit("Fail closed: unowned module paths: " + ", ".join(plan["unknown_owner_paths"]))


if __name__ == "__main__":
    main()
