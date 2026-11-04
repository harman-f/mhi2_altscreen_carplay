#!/usr/bin/env python3
"""Audit the *frozen legacy SD-root ZIP* without claiming modular R3 compliance.

Host-only. A validated legacy payload is NOT eligible for a new public
release under the current multi-profile/package policy.
"""
from __future__ import annotations

import argparse
import hashlib
import stat
import sys
from pathlib import Path, PurePosixPath
import tempfile
import warnings
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
# Modes as produced by tools/prepare_mu1440_sd.sh + `zip -r` in
# release-mu1440-aid10.yml (zip stores the staged tree's modes): every *.sh and
# the ELF/helper payloads are 0755, jars/receipts/config are 0644.
EXEC_PAYLOAD = {"payload/libaltscreen111.so", "payload/direct-ts-remux",
                "payload/libmibr_isotx2_gate.so", "payload/sha256sum", "payload/tee"}
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


def check_mode(name: str, info: zipfile.ZipInfo) -> None:
    mode = info.external_attr >> 16
    if mode & 0o7002:
        raise ValueError("setuid/setgid/sticky or world-writable ZIP mode %04o: %s" % (mode & 0o7777, name))
    if info.is_dir():
        return
    if mode & 0o170000 not in (0, stat.S_IFREG):
        raise ValueError("non-regular ZIP member: " + name)
    if (name.endswith(".sh") or name in EXEC_PAYLOAD) and (mode & 0o111) != 0o111:
        raise ValueError("script/binary lacks exec bits (mode %04o): %s" % (mode & 0o7777, name))


def audit(path: Path, frozen: dict[str, str] = FROZEN_DIGESTS) -> None:
    try:
        _audit(path, frozen)
    except (zipfile.BadZipFile, EOFError, OSError, UnicodeDecodeError) as exc:
        raise ValueError("corrupt or unreadable ZIP: %s" % exc) from exc


def _audit(path: Path, frozen: dict[str, str]) -> None:
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad is not None:
            raise ValueError("ZIP CRC failure: " + bad)
        for info in z.infolist():
            check_mode(info.filename.removeprefix("./"), info)
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
    for filename, known_hash in frozen.items():
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


def _build(path: Path, modes=None, mutate=None, extra=()) -> dict[str, str]:
    """Synthesize a structurally valid legacy ZIP with its own frozen digests."""
    files = {n: b"#!/bin/ksh\n:\n" for n in
             ("install.sh", "status.sh", "uninstall.sh", "compatibility-report.sh",
              "runtime/deployment/session.sh", "runtime/auto-direct/a.sh", "runtime/isotx2-gate/g.sh")}
    files["README-FIRST.txt"] = b"readme\n"
    files["RELEASE-MANIFEST.txt"] = b"manifest\n"
    for n in PAYLOAD:
        files["payload/" + n] = b"payload " + n.encode()
    frozen = {n: hashlib.sha256(files["payload/" + n]).hexdigest() for n in FROZEN_DIGESTS}
    files["PAYLOAD.sha256"] = "".join("%s  payload/%s\n" % (hashlib.sha256(files["payload/" + n]).hexdigest(), n)
                                      for n in sorted(PAYLOAD)).encode()
    if mutate:
        mutate(files)
    files["RELEASE-SHA256SUMS.txt"] = "".join(
        "%s  ./%s\n" % (hashlib.sha256(v).hexdigest(), k) for k, v in sorted(files.items())
        if k != "RELEASE-SHA256SUMS.txt").encode()
    with warnings.catch_warnings(), zipfile.ZipFile(path, "w") as z:
        warnings.simplefilter("ignore")  # duplicate-name fixture is intentional
        for n, data in list(files.items()) + [(n, d) for n, d, _ in extra]:
            info = zipfile.ZipInfo(n)
            override = {n2: m for n2, _, m in extra}.get(n)
            if override is not None:
                mode = override
            elif modes is None:
                exe = n.endswith(".sh") or n in EXEC_PAYLOAD
                mode = 0o100755 if exe else 0o100644
            else:
                mode = 0o100000 | modes
            info.external_attr = mode << 16
            z.writestr(info, data)
    return frozen


def self_test() -> None:
    def expect_reject(label, **kw):
        with tempfile.TemporaryDirectory(prefix="legacy-zip-reject-") as td:
            p = Path(td) / "case.zip"
            frozen = _build(p, **{k: v for k, v in kw.items() if k != "post"})
            if kw.get("post"):
                kw["post"](p)
            try:
                audit(p, frozen)
            except ValueError:
                return
            raise AssertionError("incorrectly accepted: " + label)

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
        good = Path(td) / "good.zip"
        audit(good, _build(good))  # the modeled genuine layout must pass
    expect_reject("all 0644 (no exec bits)", modes=0o644)
    expect_reject("all 0777 (world-writable)", modes=0o777)
    expect_reject("setuid installer", modes=0o4755)
    expect_reject("tampered payload vs PAYLOAD.sha256",
                  mutate=lambda f: f.__setitem__("payload/tee", b"tampered"))
    expect_reject("missing payload file", mutate=lambda f: f.pop("payload/tee"))
    expect_reject("unlisted extra payload", mutate=lambda f: f.__setitem__("payload/extra", b"x"))
    expect_reject("symlink member", extra=[("runtime/auto-direct/link.sh", b"install.sh", 0o120755)])
    expect_reject("duplicate member", extra=[("status.sh", b"dup", 0o100755)])
    expect_reject("absolute path member", extra=[("/etc/x.sh", b"x", 0o100755)])
    def corrupt(path):
        raw = bytearray(path.read_bytes())
        k = raw.index(b"payload libaltscreen111.so")
        raw[k] ^= 0xFF  # flip a stored byte: CRC32 no longer matches
        path.write_bytes(bytes(raw))
    expect_reject("bad CRC", post=corrupt)
    expect_reject("truncated ZIP", post=lambda p: p.write_bytes(p.read_bytes()[:-30]))
    print("LEGACY_ZIP_SELF_TEST=PASS")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("zip", nargs="?", type=Path)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
    if args.zip:
        try:
            audit(args.zip)
        except ValueError as exc:
            print("LEGACY_ZIP_INTEGRITY=FAIL " + str(exc), file=sys.stderr)
            sys.exit(1)
    if not (args.self_test or args.zip):
        p.error("pass ZIP path and/or --self-test")


if __name__ == "__main__":
    main()
