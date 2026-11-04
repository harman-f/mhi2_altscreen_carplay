#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Host-only structural release gate; no firmware or toolchain needed.

Every check raises PackageError (never ``assert``, which ``python -O`` strips)
and the command line exits non-zero with ``MODULAR_PACKAGE_GATE=FAIL <reason>``.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import warnings
import zipfile

PREFIX = "MIBR-CarPlay/"
PROFILES = {"skoda-mu1440-p4526", "seat-mu1409-p4708", "seat-mu1447-p4709"}
GROUPS = ("hmi", "icons", "display", "input", "integration")


class PackageError(Exception):
    """The archive violates the modular package contract."""


def check(condition, message):
    if not condition:
        raise PackageError(str(message))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(files, name):
    if name not in files:
        raise PackageError("missing package file: " + name)
    return files[name]


def parse_package_sha(raw):
    rows = {}
    for line in raw.decode("utf-8").splitlines():
        digest, sep, path = line.partition("  ")
        check(sep == "  " and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest),
              "malformed PACKAGE.sha256 entry")
        check(path not in rows, "duplicate PACKAGE.sha256 path: " + path)
        rows[path] = digest
    return rows


def load_json(files, name):
    try:
        return json.loads(need(files, name))
    except ValueError as exc:
        raise PackageError("invalid JSON in %s: %s" % (name, exc)) from exc


def read_archive(path):
    """Return {relative path: bytes} after integrity and path-safety checks."""
    try:
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
            check(bad is None, "ZIP CRC failure: " + str(bad))
            infos = z.infolist()
            for i in infos:
                if (i.external_attr >> 16) & 0o170000 == stat.S_IFLNK:
                    raise PackageError("symlink archive member prohibited: " + i.filename)
            members = [i for i in infos if not i.filename.endswith("/")]
            names = [i.filename for i in members]
            check(len(names) == len(set(names)), "duplicate archive members")
            for n in names:
                check(n.startswith(PREFIX) and not n.startswith("/") and "\\" not in n
                      and all(p not in ("", ".", "..") for p in n.split("/")), "unsafe archive path: " + n)
            return {i.filename[len(PREFIX):]: z.read(i) for i in members}
    except (zipfile.BadZipFile, EOFError, OSError) as exc:
        raise PackageError("corrupt or unreadable ZIP: %s" % exc) from exc


def validate(path):
    files = read_archive(path)
    check(not any(n.startswith(("files/", "config/", "bin/")) for n in files), "legacy flat payload tree")
    meta = load_json(files, "package.json")
    try:
        check(set(meta["profiles"]) == PROFILES, "unexpected profile set")
        check(set(meta["modules"]) == {"carplay", "broker", "menu", "navigation"}, "module ownership drift")
        records = meta["files"]
        listed = [r["path"] for r in records]
        wanted = {r["path"]: r["sha256"] for r in records}
    except (KeyError, TypeError) as exc:
        raise PackageError("malformed package.json: %r" % (exc,)) from exc
    check("common/menu/config/mibr-menu.conf" in files, "missing deployed default menu")
    check("tools/menu-editor/mibr-menu-editor.html" in files, "missing shared editor")
    check(len(set(listed)) == len(listed), "duplicate inventory rows")
    for p in listed:
        need(files, p)
    check(set(listed) == set(files) - {"package.json", "PACKAGE.sha256"}, "unlisted package bytes")
    for p, digest in wanted.items():
        check(sha(files[p]) == digest, "hash mismatch: " + p)
    receipts = parse_package_sha(need(files, "PACKAGE.sha256"))
    actual = {n: sha(v) for n, v in files.items() if n != "PACKAGE.sha256"}
    check(receipts == actual, "PACKAGE.sha256 does not match package bytes")
    selectors = [line.split() for line in need(files, "installer/config/profiles.list").decode().splitlines()[1:] if line]
    check(len(selectors) == 3 and all(len(r) >= 2 for r in selectors) and {r[0] for r in selectors} == PROFILES,
          "profile index mismatch")
    check(len({r[1] for r in selectors}) == 3, "ambiguous selectors")
    index_sha = sha(files["installer/config/profiles.list"])
    check(index_sha in need(files, "installer/mibr-kit.ksh").decode(), "unpinned profile index")
    common = need(files, "installer/config/payload.manifest").decode()
    for pid in sorted(PROFILES):
        root = "profiles/" + pid + "/"
        for group in GROUPS:
            check(any(n.startswith(root + group + "/") for n in files), "missing group %s/%s" % (pid, group))
        targets = set()
        overlay = need(files, root + "payload.manifest").decode()
        overlay_lines = overlay.splitlines()
        for line in (common + overlay).splitlines():
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            check(len(fields) == 4, "malformed payload manifest line: " + line)
            digest, _mode, target, source = fields
            check(target not in targets, "%s duplicate target %s" % (pid, target))
            targets.add(target)
            check(sha(need(files, source)) == digest, "payload hash mismatch: " + source)
            if line in overlay_lines:
                check(source.startswith(root), "%s cross-profile payload %s" % (pid, source))
        for line in need(files, root + "integration/variants.list").decode().splitlines():
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            check(len(fields) >= 4, "malformed variants line: " + line)
            check(fields[3].startswith(root + "integration/"), "cross-profile OEM variant")
            check(sha(need(files, fields[3])) == fields[2], "variant hash mismatch: " + fields[3])
    source = load_json(files, "source/SOURCE_MANIFEST.json")
    try:
        check(source["coverage"] == "PARTIAL", "do not silently promote source coverage")
        check(source["files"], "empty source inventory")
        for row in source["files"]:
            check(sha(need(files, row["path"])) == row["sha256"], "source hash mismatch: " + row["path"])
    except (KeyError, TypeError) as exc:
        raise PackageError("malformed SOURCE_MANIFEST.json: %r" % (exc,)) from exc
    print("MODULAR_PACKAGE_GATE=PASS profiles=3 files=" + str(len(files)))


def fixture_files():
    """A minimal package that satisfies every rule of the gate (test only)."""
    f = {
        "common/menu/config/mibr-menu.conf": b"menu\n",
        "common/payload/helper": b"helper\n",
        "tools/menu-editor/mibr-menu-editor.html": b"<html></html>\n",
        "source/doc.txt": b"source\n",
    }
    selectors = ["profile selector"] + ["%s sel-%d" % (p, i) for i, p in enumerate(sorted(PROFILES))]
    f["installer/config/profiles.list"] = ("\n".join(selectors) + "\n").encode()
    f["installer/mibr-kit.ksh"] = ("PROFILES_SHA=%s\n" % sha(f["installer/config/profiles.list"])).encode()
    f["installer/config/payload.manifest"] = ("%s 0755 /x/helper common/payload/helper\n"
                                              % sha(f["common/payload/helper"])).encode()
    for pid in PROFILES:
        root = "profiles/" + pid + "/"
        for g in GROUPS:
            f[root + g + "/file"] = (pid + g).encode()
        f[root + "payload.manifest"] = ("%s 0644 /x/%s %sicons/file\n"
                                        % (sha(f[root + "icons/file"]), pid, root)).encode()
        f[root + "integration/variants.list"] = ("v1 a %s %sintegration/file\n"
                                                 % (sha(f[root + "integration/file"]), root)).encode()
    f["source/SOURCE_MANIFEST.json"] = json.dumps(
        {"coverage": "PARTIAL", "files": [{"path": "source/doc.txt", "sha256": sha(f["source/doc.txt"])}]}).encode()
    meta = {"profiles": sorted(PROFILES), "modules": ["carplay", "broker", "menu", "navigation"],
            "files": [{"path": k, "sha256": sha(v)} for k, v in sorted(f.items())]}
    f["package.json"] = json.dumps(meta).encode()
    f["PACKAGE.sha256"] = "".join("%s  %s\n" % (sha(v), k) for k, v in sorted(f.items())
                                  if k != "PACKAGE.sha256").encode()
    return f


def write_zip(path, files, extra=()):
    with warnings.catch_warnings(), zipfile.ZipFile(path, "w") as z:
        warnings.simplefilter("ignore")
        for name, data in list(files.items()) + list(extra):
            z.writestr(name if name.startswith(("/", "other/")) or ".." in name else PREFIX + name, data)


def self_test():
    # Each case must be rejected with PackageError (not KeyError/AssertionError),
    # so the gate is identical under ``python -O``.
    with tempfile.TemporaryDirectory(prefix="modular-gate-negative-") as td:
        path = Path(td) / "case.zip"

        def reject(label, expected, files=None, extra=(), post=None):
            write_zip(path, fixture_files() if files is None else files, extra)
            if post:
                post(path)
            try:
                validate(path)
            except PackageError as exc:
                if expected not in str(exc):
                    raise RuntimeError("%s: wrong reason %r (wanted %r)" % (label, str(exc), expected))
                return
            raise RuntimeError("accepted invalid package: " + label)

        write_zip(path, fixture_files())
        validate(path)  # the positive fixture must pass

        def without(name):
            f = fixture_files()
            del f[name]
            return f
        reject("missing package.json", "missing package file: package.json", without("package.json"))
        reject("missing PACKAGE.sha256", "missing package file: PACKAGE.sha256", without("PACKAGE.sha256"))
        reject("missing listed file", "missing package file: source/doc.txt", without("source/doc.txt"))
        f = fixture_files()
        f["PACKAGE.sha256"] = f["PACKAGE.sha256"].replace(b"0", b"1", 1) if f["PACKAGE.sha256"][:1] != b"1" \
            else f["PACKAGE.sha256"].replace(b"1", b"0", 1)
        reject("wrong hash in PACKAGE.sha256", "PACKAGE.sha256 does not match", f)
        f = fixture_files()
        f["source/doc.txt"] = b"tampered\n"
        reject("tampered byte vs inventory", "hash mismatch: source/doc.txt", f)
        f = fixture_files()
        f["unlisted"] = b"x"
        reject("unlisted file", "unlisted package bytes", f)
        info = zipfile.ZipInfo(PREFIX + "source/link")
        info.external_attr = 0o120777 << 16

        def add_symlink(p):
            with zipfile.ZipFile(p, "a") as z:
                z.writestr(info, "doc.txt")
        reject("symlink member", "symlink archive member", post=add_symlink)
        reject("absolute path member", "unsafe archive path", extra=[("/etc/passwd", b"x")])
        reject("dot-dot path member", "unsafe archive path", extra=[(PREFIX + "../escape", b"x")])
        reject("outside prefix", "unsafe archive path", extra=[("other/file", b"x")])

        def flip(p):
            raw = bytearray(p.read_bytes())
            raw[raw.index(b"<html></html>")] ^= 0xFF  # stored data: CRC32 now wrong
            p.write_bytes(bytes(raw))
        reject("corrupt CRC", "CRC failure", post=flip)
        reject("truncated ZIP", "corrupt or unreadable ZIP", post=lambda p: p.write_bytes(p.read_bytes()[:-40]))
        reject("not a ZIP", "corrupt or unreadable ZIP", post=lambda p: p.write_bytes(b"garbage"))
        # Regression: flat payload roots and archive traversal must never be accepted.
        for name in ("MIBR-CarPlay/files/profiles/old/file", "MIBR-CarPlay/../escape", "other/file"):
            reject("invalid layout " + name, "", files={}, extra=[(name, b"invalid layout")])
    print("MODULAR_PACKAGE_GATE_SELF_TEST=PASS")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("zip", nargs="?")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if not args.self_test and not args.zip:
        p.error("supply a ZIP and/or --self-test")
    try:
        if args.self_test:
            self_test()
        if args.zip:
            validate(args.zip)
    except PackageError as exc:
        print("MODULAR_PACKAGE_GATE=FAIL " + str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
