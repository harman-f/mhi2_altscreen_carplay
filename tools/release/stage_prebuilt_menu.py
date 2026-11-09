#!/usr/bin/env python3
"""Stage reviewed profile menu JARs only when their source Git objects still match.

Git tree/blob IDs are content fingerprints: unlike a baseline commit diff,
they work with shallow checkouts and after squash merges. This proves *source
freshness*, not an OEM/J9 deterministic rebuild or vehicle approval.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from verify_profile_menu_artifacts import EXPECTED, LOCK, main as verify_jars  # noqa: E402


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], text=True, capture_output=True, check=True,
    ).stdout.strip()


def changed_inputs(repo, expected_objects):
    """Compare complete tracked HMI/profile inputs, without needing an old commit."""
    if not expected_objects:
        raise ValueError("MENU_SOURCE_LOCK_EMPTY")
    changes = []
    for path, expected in sorted(expected_objects.items()):
        if not isinstance(path, str) or not isinstance(expected, str) or len(expected) != 40:
            raise ValueError("MENU_SOURCE_LOCK_INVALID_ENTRY")
        try:
            actual = git(repo, "rev-parse", "--verify", "HEAD:" + path)
        except subprocess.CalledProcessError:
            actual = "<missing>"
        if actual != expected:
            changes.append(path + " (expected " + expected[:12] + ", actual " + actual[:12] + ")")
    dirty = git(repo, "status", "--porcelain", "--untracked-files=all", "--", *expected_objects)
    changes.extend("uncommitted: " + p for p in dirty.splitlines() if p)
    return changes


def stage(repo, out, check_only=False):
    stale = changed_inputs(repo, LOCK["git_objects"])
    if stale:
        raise ValueError(
            "MENU_PREBUILT_STALE: reviewed Java/profile/API/registry content differs: "
            + ", ".join(stale[:12])
            + "; rebuild the affected profile JARs with the matching private J9 inputs, "
              "verify exact classes and update approved Git object + SHA-256 pins together"
        )
    verify_jars()
    if check_only:
        print("MENU_PREBUILT_SOURCE=PASS locked_git_objects=" + str(len(LOCK["git_objects"])))
        return
    if out is None:
        raise ValueError("output directory required unless --check-only")
    target = out.resolve()
    root = repo.resolve()
    if target == root or root in target.parents:
        raise ValueError("MENU_PREBUILT_OUTPUT_INSIDE_PUBLIC_REPOSITORY")
    target.mkdir(parents=True, exist_ok=True)
    for profile in sorted(EXPECTED):
        source = root / "modules/profiles" / profile / "hmi/prebuilt/MIBR-CarPlay.jar"
        destination = target / profile / "MIBR-CarPlay.jar"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        print("MENU_PREBUILT_STAGED profile=" + profile + " sha256=" + EXPECTED[profile])
    # The assembler's source freshness receipt identifies the *checked* checkout
    # snapshot, not the historic time each prebuilt archive was compiled.
    (target / "SOURCE_COMMIT.txt").write_text(git(repo, "rev-parse", "HEAD") + "\n")
    print("MENU_PREBUILT_SOURCE=PASS exact_checkout_with_reviewed_git_objects")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        stage(ROOT, args.out, args.check_only)
    except (ValueError, subprocess.CalledProcessError, OSError) as e:
        raise SystemExit("MENU_PREBUILT=BLOCKED " + str(e)) from e


if __name__ == "__main__":
    main()
