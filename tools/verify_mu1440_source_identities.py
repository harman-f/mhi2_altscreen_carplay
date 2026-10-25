#!/usr/bin/env python3
"""Verify MU1440 source-build identities for release and explicit review refs."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys


PRODUCTION_IDENTITIES = {
    "libaltscreen111.so": "304b5079374a08ed9a763528217476b29ad49e000ba25d0372ed4147cbb9a705",
    "alt111-settings": "b0d61578452a93b966f268e2bd400029bb1b6fa249dfd18e8895f851ca89073c",
    "direct-ts-parity": "3098cdd4469a4a3b4ee92c583518b3af362e02e41921ed3d80641853ced0827b",
    "libmibr_isotx2_guard.so": "cad06d69c698c8940dec9596b96c6b90ec822bdd437c4b0d02a35881ad71fae4",
    "libmibr_isotx2_gate.so": "05673010a88c25022145ffb4e75d3715eaf686f4127ac188e91a52f512b9d957",
    "mibr-control/mibr-v3-service-QNX65-ARMv7-NOT-INSTALL-READY": "97177ddbfe78d49dc0d672c5b70e717a87c0aeebb6ac65ab4e1b7df12e60bb58",
    "mibr-control/mibrctl-v3-QNX65-ARMv7-NOT-INSTALL-READY": "fa4a580337a6a0a1d67e15ee1abc7f809591978cbfdecada5b87259fb8a5f351",
    "mibr-control/mibr-v3-genkey-QNX65-ARMv7-NOT-INSTALL-READY": "328837d6df6daaeec25197d8cb9f7e9070c194e012f86dfc3c75256cb36d5474",
    "mibr-control/mibr-key40d-QNX65-ARMv7-NOT-INSTALL-READY": "3612c686a6de43c7cfbcb4e96645bca83ba9db33f8c03b19e33c0c73efbaf9d2",
}

# This exact branch has one deliberate libaltscreen111.so source change. Its
# QNX output was rebuilt locally with the pinned 6.5 toolchain; every other
# artifact continues to use PRODUCTION_IDENTITIES above.
BRANCH_OVERRIDES = {
    "work/suggestui-root-advertisement-review-20261025": {
        "libaltscreen111.so": "f6064f1eb4deabf280a502ce2742c3b366e44edec60966c6e400fbbcd4e8860e",
    },
}
OVERRIDABLE_ARTIFACTS = frozenset({"libaltscreen111.so"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def select_expected_identities(source_ref, production=None, branch_overrides=None):
    """Return (profile, expected hashes), defaulting to frozen production pins."""
    if not isinstance(source_ref, str) or not source_ref.strip():
        raise ValueError("source ref must be an explicit non-empty branch/ref name")

    base = dict(PRODUCTION_IDENTITIES if production is None else production)
    overrides_by_ref = BRANCH_OVERRIDES if branch_overrides is None else branch_overrides
    overrides = dict(overrides_by_ref.get(source_ref, {}))
    unexpected = set(overrides) - OVERRIDABLE_ARTIFACTS
    if unexpected:
        raise ValueError(f"branch override may not change identities for: {sorted(unexpected)}")
    if not set(overrides).issubset(base):
        raise ValueError("branch override refers to an artifact without a production pin")
    for name, digest in {**base, **overrides}.items():
        if not SHA256_RE.fullmatch(digest):
            raise ValueError(f"invalid SHA-256 for {name}")
    base.update(overrides)
    profile = "review-candidate" if overrides else "production-baseline"
    return profile, base


def verify_identity_files(output_dir, source_ref, production=None, branch_overrides=None):
    profile, expected = select_expected_identities(source_ref, production, branch_overrides)
    root = Path(output_dir)
    failures = []
    print(f"SOURCE_IDENTITY_PROFILE={profile} source_ref={source_ref}")
    for relative, wanted in expected.items():
        path = root / relative
        if not path.is_file():
            failures.append(f"missing identity artifact: {relative}")
            print(f"MISSING {relative}", file=sys.stderr)
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != wanted:
            failures.append(relative)
            print(f"SHA-256 mismatch for {relative}: expected {wanted}, got {digest}", file=sys.stderr)
        else:
            print(f"{relative} SHA256={digest}")
    if failures:
        print(f"SOURCE_IDENTITIES=FAIL count={len(failures)}", file=sys.stderr)
        return 1
    print(f"SOURCE_IDENTITIES=PASS count={len(expected)}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-ref", required=True)
    args = parser.parse_args(argv)
    try:
        return verify_identity_files(args.output_dir, args.source_ref)
    except (OSError, ValueError) as exc:
        print(f"SOURCE_IDENTITIES=ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
