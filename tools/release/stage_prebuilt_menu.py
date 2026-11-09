#!/usr/bin/env python3
"""Stage owner-approved profile menu JARs only when their public build inputs are unchanged.

This is an artifact-to-source *freshness* gate, not evidence of deterministic J9
archive bytes or vehicle acceptance. On Java/registry/profile changes, rebuild
locally with exact private firmware/J9 inputs and review new artifacts and pins.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from verify_profile_menu_artifacts import EXPECTED, main as verify_jars  # noqa: E402

# Release baseline whose public Java inputs were reconciled with the r11b
# reference artifacts. Update only together with independently rebuilt,
# reviewed profile JARs, updated hashes, and an explicit provenance review.
PUBLIC_SOURCE_BASELINE = "420fc46c63594a1a0274ddf6a3da7fb19c33b294"

# Conservative: profile.json also pins the exact API JAR and adapter lineage.
# Include all profile HMI trees (including checked-in reference artifacts) to
# detect any changes before blindly reusing the same baseline.
SOURCE_INPUTS = (
    "modules/menu/source",
    "settings/registry.json",
    "modules/profiles/skoda-mu1440-p4526/hmi",
    "modules/profiles/seat-mu1409-p4708/hmi",
    "modules/profiles/seat-mu1447-p4709/hmi",
    "modules/profiles/skoda-mu1440-p4526/profile.json",
    "modules/profiles/seat-mu1409-p4708/profile.json",
    "modules/profiles/seat-mu1447-p4709/profile.json",
)


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], text=True, capture_output=True,
        check=True,
    ).stdout.strip()


def changed_paths(repo, baseline=PUBLIC_SOURCE_BASELINE, inputs=SOURCE_INPUTS):
    git(repo, "cat-file", "-e", baseline + "^{commit}")
    paths = git(repo, "diff", "--name-only", baseline, "HEAD", "--", *inputs)
    dirty = git(repo, "status", "--porcelain", "--untracked-files=all", "--", *inputs)
    return [p for p in paths.splitlines() if p] + [
        "uncommitted: " + p for p in dirty.splitlines() if p
    ]


def stage(repo, out, check_only=False):
    stale = changed_paths(repo)
    if stale:
        raise ValueError(
            "MENU_PREBUILT_STALE: menu sources/profile/API/registry changed since "
            + PUBLIC_SOURCE_BASELINE[:12] + ": " + ", ".join(stale[:12])
            + "; rebuild affected profile JARs locally with exact private inputs "
            "and update pins/baseline after review"
        )
    verify_jars()
    if check_only:
        print("MENU_PREBUILT_SOURCE=PASS commit=" + PUBLIC_SOURCE_BASELINE)
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
    (target / "SOURCE_COMMIT.txt").write_text(PUBLIC_SOURCE_BASELINE + "\n")
    print("MENU_PREBUILT_SOURCE=PASS commit=" + PUBLIC_SOURCE_BASELINE)


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
