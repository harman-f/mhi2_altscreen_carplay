#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Host-only structural release gate; no firmware or toolchain needed."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

PREFIX = "MIBR-CarPlay/"
PROFILES = {"skoda-mu1440-p4526", "seat-mu1409-p4708", "seat-mu1447-p4709"}


def validate(path):
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        assert len(names) == len(set(names)), "duplicate archive members"
        assert all(n.startswith(PREFIX) and ".." not in n.split("/") for n in names), "unsafe archive path"
        files = {n[len(PREFIX):]: z.read(n) for n in names}
    assert not any(n.startswith(("files/", "config/", "bin/")) for n in files), "legacy flat payload tree"
    meta = json.loads(files["package.json"])
    assert set(meta["profiles"]) == PROFILES, "unexpected profile set"
    assert set(meta["modules"]) == {"carplay", "broker", "menu", "navigation"}, "module ownership drift"
    assert "common/menu/config/mibr-menu.conf" in files, "missing deployed default menu"
    assert "tools/menu-editor/mibr-menu-editor.html" in files, "missing shared editor"
    records = meta["files"]
    assert len({r["path"] for r in records}) == len(records), "duplicate inventory rows"
    assert {r["path"] for r in records} == set(files) - {"package.json", "PACKAGE.sha256"}, "unlisted package bytes"
    for r in records:
        assert hashlib.sha256(files[r["path"]]).hexdigest() == r["sha256"], r["path"]
    selectors = [line.split() for line in files["installer/config/profiles.list"].decode().splitlines()[1:] if line]
    assert {r[0] for r in selectors} == PROFILES and len(selectors) == 3
    assert len({r[1] for r in selectors}) == 3, "ambiguous selectors"
    index_sha = hashlib.sha256(files["installer/config/profiles.list"]).hexdigest()
    assert index_sha in files["installer/mibr-kit.ksh"].decode(), "unpinned profile index"
    common = files["installer/config/payload.manifest"].decode()
    for pid in PROFILES:
        root = "profiles/" + pid + "/"
        for group in ("hmi", "icons", "display", "input", "integration"):
            assert any(n.startswith(root + group + "/") for n in files), (pid, group)
        targets = set()
        overlay = files[root + "payload.manifest"].decode()
        for line in (common + overlay).splitlines():
            if not line or line.startswith("#"):
                continue
            digest, mode, target, source = line.split()
            assert target not in targets, (pid, "duplicate target", target)
            targets.add(target)
            assert hashlib.sha256(files[source]).hexdigest() == digest, source
            if line in overlay.splitlines():
                assert source.startswith(root), (pid, "cross-profile payload", source)
        for line in files[root + "integration/variants.list"].decode().splitlines():
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            assert fields[3].startswith(root + "integration/"), "cross-profile OEM variant"
            assert hashlib.sha256(files[fields[3]]).hexdigest() == fields[2]
    source = json.loads(files["source/SOURCE_MANIFEST.json"])
    assert source["coverage"] == "PARTIAL", "do not silently promote source coverage"
    assert source["files"], "empty source inventory"
    for row in source["files"]:
        assert hashlib.sha256(files[row["path"]]).hexdigest() == row["sha256"], row["path"]
    print("MODULAR_PACKAGE_GATE=PASS profiles=3 files=" + str(len(files)))


def self_test():
    # Regression: flat payload roots and archive traversal must never be accepted.
    with tempfile.TemporaryDirectory(prefix="modular-gate-negative-") as td:
        for name in ("MIBR-CarPlay/files/profiles/old/file", "MIBR-CarPlay/../escape", "other/file"):
            path = Path(td) / "invalid.zip"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr(name, b"invalid layout")
            try:
                validate(path)
            except AssertionError:
                continue
            raise AssertionError("accepted invalid layout: " + name)
    print("MODULAR_PACKAGE_GATE_SELF_TEST=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("zip", nargs="?")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
    if args.zip:
        validate(args.zip)
    if not args.self_test and not args.zip:
        p.error("supply a ZIP and/or --self-test")
