#!/usr/bin/env python3
"""Fail-closed source freshness check for profile menu inputs.

The lock covers every tracked profile HMI file except the exact legacy
prebuilt JAR path. That JAR is a private release input and is intentionally
not stored or staged from this public repository.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = ROOT / "modules/profiles/MENU_SOURCE_LOCK.json"
PROFILES = (
    "skoda-mu1440-p4526",
    "seat-mu1409-p4708",
    "seat-mu1447-p4709",
)
HMI_ROOTS = tuple(f"modules/profiles/{profile}/hmi" for profile in PROFILES)
EXCLUDED_JAR = "prebuilt/MIBR-CarPlay.jar"
REQUIRED_NON_HMI = {
    "modules/menu/source", "settings/registry.json",
    *(f"modules/profiles/{profile}/profile.json" for profile in PROFILES),
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class LockError(ValueError):
    pass


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, text=True,
        capture_output=True,
    ).stdout


def load_lock(path=LOCK_PATH):
    lock = json.loads(Path(path).read_text(encoding="utf-8"))
    if lock.get("schema") != 2:
        raise LockError("MENU_SOURCE_LOCK_SCHEMA_UNSUPPORTED")
    if tuple(lock.get("hmi_roots", ())) != HMI_ROOTS:
        raise LockError("MENU_SOURCE_LOCK_HMI_ROOTS_INVALID")
    objects = lock.get("git_objects")
    if not isinstance(objects, dict) or not objects:
        raise LockError("MENU_SOURCE_LOCK_EMPTY")
    for path, oid in objects.items():
        if (not isinstance(path, str) or path.startswith("/") or
                ".." in Path(path).parts or not HEX40.fullmatch(str(oid))):
            raise LockError("MENU_SOURCE_LOCK_INVALID_ENTRY")
    if not REQUIRED_NON_HMI.issubset(objects):
        raise LockError("MENU_SOURCE_LOCK_REQUIRED_INPUT_MISSING")
    return lock


def expected_hmi_paths(repo, head="HEAD"):
    expected = set()
    for root in HMI_ROOTS:
        try:
            paths = git(repo, "ls-tree", "-r", "--name-only", head, "--", root).splitlines()
        except subprocess.CalledProcessError as exc:
            raise LockError("MENU_SOURCE_PROFILE_MISSING: " + root) from exc
        if not paths:
            raise LockError("MENU_SOURCE_PROFILE_MISSING: " + root)
        excluded = root + "/" + EXCLUDED_JAR
        expected.update(path for path in paths if path != excluded)
    return expected


def verify(repo=ROOT, lock=None):
    lock = lock if lock is not None else load_lock()
    if lock.get("schema") != 2:
        raise LockError("MENU_SOURCE_LOCK_SCHEMA_UNSUPPORTED")
    if tuple(lock.get("hmi_roots", ())) != HMI_ROOTS:
        raise LockError("MENU_SOURCE_LOCK_HMI_ROOTS_INVALID")
    objects = lock["git_objects"]
    hmi_expected = expected_hmi_paths(repo)
    hmi_locked = {path for path in objects if any(path.startswith(root + "/") for root in HMI_ROOTS)}
    if hmi_locked != hmi_expected:
        missing = sorted(hmi_expected - hmi_locked)
        extra = sorted(hmi_locked - hmi_expected)
        raise LockError("MENU_SOURCE_HMI_PATH_SET_MISMATCH missing=" + repr(missing[:8]) +
                        " extra=" + repr(extra[:8]))
    for root in HMI_ROOTS:
        if any(path.startswith(root + "/prebuilt/") for path in objects):
            raise LockError("MENU_SOURCE_LOCK_CONTAINS_PREBUILT_PATH")

    changed = []
    for path, expected in sorted(objects.items()):
        try:
            actual = git(repo, "rev-parse", "--verify", "HEAD:" + path).strip()
        except subprocess.CalledProcessError:
            actual = "<missing>"
        if actual != expected:
            changed.append(path)
    scoped = sorted(set(objects) | set(HMI_ROOTS))
    dirty = git(repo, "status", "--porcelain", "--untracked-files=all", "--", *scoped)
    if dirty:
        changed.extend("working-tree: " + line for line in dirty.splitlines())
    if changed:
        raise LockError("MENU_SOURCE_LOCK_STALE: " + ", ".join(changed[:16]))
    return {"hmi_roots": list(HMI_ROOTS), "locked_objects": len(objects), "status": "PASS"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, default=LOCK_PATH)
    args = parser.parse_args()
    try:
        result = verify(lock=load_lock(args.lock))
    except (LockError, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        raise SystemExit("MENU_SOURCE=BLOCKED " + str(exc)) from exc
    print("MENU_SOURCE=PASS locked_objects=" + str(result["locked_objects"]) +
          " hmi_roots=" + str(len(result["hmi_roots"])))


if __name__ == "__main__":
    main()
