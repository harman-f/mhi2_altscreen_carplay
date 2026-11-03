#!/usr/bin/env python3
"""Audit the *frozen legacy SD-root ZIP* without claiming modular R3 compliance.

Host-only. A validated legacy payload is NOT eligible for a new public
release under the current multi-profile/package policy.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

PAYLOAD = {
    "libaltscreen111.so",
    "direct-ts-remux",
    "libmibr_isotx2_gate.so",
    "sha256sum",
    "tee",
    "MIBR-NavIgnore.jar",
    "MIBR-Most20FPS.jar",
}
REQUIRED = {"install.sh", "status.sh", "uninstall.sh", "compatibility-report.sh",
            "runtime/deployment/session.sh", "PAYLOAD.sha256", "RELEASE-SHA256SUMS.txt",
            "README-FIRST.txt", "RELEASE-MANIFEST.txt"}
FROZEN_DIGESTS = {
    "libaltscreen111.so": "094e3f1abfbf949f8c11b27e048e8213e5fc71178e62efd3c56deed8ee3bf8d8",
    "direct-ts-remux": "b761a8741682e3cbc6e05f5fe1705475c34c4805d1cd1ce09333274a301e735e",
    "libmibr_isotx2_gate.so": "05673010a88c25022145ffb4e75d3715eaf686f4127ac188e91a52f512b9d957",
    "MIBR-NavIgnore.jar": "b065bab0e1c58f8439a3bdd73d2d4cb6060cbac1c943e5b425425eb453c94b34",
    "MIBR-Most20FPS.jar": "dbd45609fe4ba69948d39e9e649b224484f680f6aa7934b68c261a4d360ea5bb",
}


def parse_sha_lines(raw: bytes) -> dict[str, str]:
    rows = {}
    for line in raw.decode("utf-8").splitlines():
        digest, separator, path = line.partition("  ")
        if separator != "  " or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("malformed SHA256 manifest entry")
        path = path.removeprefix("./")  # zip -r . and find . emit ./relative names
        if path in rows:
            raise ValueError("duplicate SHA256 manifest path: " + path)
        rows[path] = digest
    return rows


def audit(path: Path) -> None:
    with zipfile.ZipFile(path) as z:
        members = [i for i in z.infolist() if not i.is_dir()]
        names = [i.filename.removeprefix("./") for i in members]
        if len(names) != len(set(names)):
            raise ValueError("duplicate ZIP file path")
        for name, info in zip(names, members):
            p = PurePosixPath(name)
            if p.is_absolute() or not p.parts or any(part in ("", ".", "..") for part in name.split("/")):
                raise ValueError("unsafe legacy ZIP path: " + info.filename)
            if name.startswith(("MIBR-CarPlay/", "MHI2AltScreen/", "esd/")):
                raise ValueError("unexpected installer wrapper: " + info.filename)
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("symlink ZIP member prohibited: " + info.filename)
        files = {name: z.read(info) for name, info in zip(names, members)}
    if not REQUIRED.issubset(files):
        raise ValueError("missing required deployment or receipt file")
    payload = {n.removeprefix("payload/") for n in files if n.startswith("payload/")}
    if payload != PAYLOAD:
        raise ValueError("legacy payload inventory drift: " + repr(sorted(payload)))
    actual = {f"payload/{x}": hashlib.sha256(files[f"payload/{x}"]).hexdigest() for x in PAYLOAD}
    receipts = parse_sha_lines(files["PAYLOAD.sha256"])
    if receipts != actual:
        raise ValueError("payload manifest mismatch")
    for filename, known_hash in FROZEN_DIGESTS.items():
        if actual["payload/" + filename] != known_hash:
            raise ValueError("frozen vehicle-evidenced media hash changed: " + filename)
    checksum = parse_sha_lines(files["RELEASE-SHA256SUMS.txt"])
    expected = {k: hashlib.sha256(v).hexdigest() for k, v in files.items() if k != "RELEASE-SHA256SUMS.txt"}
    if checksum != expected:
        raise ValueError("unlisted or tampered ZIP file")
    if not any(p.startswith("runtime/auto-direct/") and p.endswith(".sh") for p in files):
        raise ValueError("missing Auto-Direct scripts")
    if not any(p.startswith("runtime/isotx2-gate/") and p.endswith(".sh") for p in files):
        raise ValueError("missing isoTX2 scripts")
    print("LEGACY_ZIP_INTEGRITY=PASS files=" + str(len(files)) + " publication=BLOCKED_R3")


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="legacy-zip-reject-") as td:
        p = Path(td) / "invalid.zip"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("../escape", "unsafe")
        try:
            audit(p)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe ZIP incorrectly passed")
    print("LEGACY_ZIP_SELF_TEST=PASS")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("zip", nargs="?", type=Path)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
    if args.zip:
        audit(args.zip)
    if not (args.self_test or args.zip):
        p.error("pass ZIP path and/or --self-test")


if __name__ == "__main__":
    main()
