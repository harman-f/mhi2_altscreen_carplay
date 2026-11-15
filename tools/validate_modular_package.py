#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Host-only structural release gate; no firmware or toolchain needed.

Accepts the package ZIP or an extracted package directory (``MIBR-CarPlay/``
or its parent). An ``incomplete`` package (declared MISSING_INPUT) passes the
structural gate and prints ``status=incomplete``; ``--require-complete`` fails it.

Every check raises PackageError (never ``assert``, which ``python -O`` strips)
and the command line exits non-zero with ``MODULAR_PACKAGE_GATE=FAIL <reason>``.
"""
import argparse
import hashlib
import json
import re
import os
from pathlib import Path
import stat
import sys
import tempfile
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_mu1440_target_shell import scan_awk_text, scan_text  # noqa: E402

PREFIX = "MIBR-CarPlay/"
PROFILES = {"skoda-mu1440-p4526", "seat-mu1409-p4708", "seat-mu1447-p4709"}
SINGLE_SCOPE = "single-profile"
TRANSFORM_SUFFIXES = (".awk", ".sed", ".block", ".patch", ".ksh", ".sh")
TARGET_SHELL_SUFFIXES = (".sh", ".ksh")
OEM_NAMES = ("smartphone_integrator.json", "startup.sh", "lsd.jxe")
HEX = "0123456789abcdef"
GROUPS = ("hmi", "icons", "display", "input", "integration")
STATUS_KEYS = ("SOURCE_BUILD_PASS", "PACKAGE_VALIDATED", "UNIT_TESTED", "VEHICLE_RELEASE_APPROVED")
STATUS_WORDS = ("NOT_RUN", "BLOCKED")
BINARY_STATUS = ("SOURCE_BUILD_PASS", "PACKAGE_VALIDATED", "UNIT_TESTED", "NOT_RUN", "BLOCKED")
PROVENANCE = ("source_commit", "compiler", "image_source")
INSTALLER_REQUIRED = ("installer/mibr-install.ksh", "installer/mibr-uninstall.ksh",
                      "installer/mibr-status.ksh", "installer/select-profile.ksh",
                      "installer/config/profiles.list")


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


def is_sha(value):
    return len(value) == 64 and all(c in HEX for c in value)


def package_profiles(meta):
    """Expected profile set: all three by default, or the declared single profile."""
    scope = meta.get("scope")
    if scope is None:
        check(set(meta["profiles"]) == PROFILES, "unexpected profile set")
        return set(PROFILES)
    check(scope == SINGLE_SCOPE, "unknown package scope: %r" % (scope,))
    declared = meta["profiles"]
    check(isinstance(declared, list) and len(declared) == 1,
          "single-profile scope requires exactly one profile")
    check(declared[0] in PROFILES, "unknown profile: %r" % (declared[0],))
    return set(declared)


def check_variant(files, root, line):
    """target stock_sha256 patched_sha256 transform_file transform_sha256 [mode]; no OEM bytes."""
    fields = line.split()
    check(len(fields) >= 5, "malformed variants line: " + line)
    _target, stock, patched, tfile, tsha = fields[:5]
    check(is_sha(stock) and is_sha(patched) and is_sha(tsha), "variants line needs 64-hex SHA-256 values: " + line)
    check(tfile.startswith(root + "integration/"), "cross-profile OEM variant")
    base = tfile.rsplit("/", 1)[-1]
    check(base not in OEM_NAMES and not base.startswith("iap2.cfg") and tfile.endswith(TRANSFORM_SUFFIXES),
          "OEM-looking payload file in variants (transform required): " + tfile)
    check(sha(need(files, tfile)) == tsha, "transform hash mismatch: " + tfile)
    check(tsha not in (stock, patched), "variant file is OEM bytes, not a transform: " + tfile)


BOOT_REF_FILES = ("installer/config/lsd-block.txt", "common/broker/scripts/boot.ksh")
_MIBR_REF = re.compile(r"(?:/mnt/app/root/mibr|\$\{?MIBR_ROOT\}?|\$\{?BASE\}?|\$A)/((?:scripts|bin)/[A-Za-z0-9._-]+)")
_JAR_REF = re.compile(r"\$BASE_DIR/lsd/jars/([A-Za-z0-9._-]+\.jar)")


def check_boot_references(files, profiles):
    """Every script/binary/JAR the lsd.sh block and boot.ksh call is installed by the package
    for every profile (2026-11-05: the beta r2 ZIP shipped neither boot.ksh nor the JARs)."""
    common = set()
    for line in need(files, "installer/config/payload.manifest").decode().splitlines():
        if line and not line.startswith("#") and len(line.split()) == 4:
            common.add(line.split()[2])
    refs = set()
    ref_files = list(BOOT_REF_FILES) + sorted(
        n for n in files if n.startswith("common/") and "/scripts/" in n and n.endswith((".sh", ".ksh")))
    for ref_file in ref_files:
        if ref_file not in files:
            continue  # lsd-block.txt itself is required by the installer's own package check
        text = files[ref_file].decode("utf-8", "replace")
        refs |= {"/mnt/app/root/mibr/" + m for m in _MIBR_REF.findall(text)}
        refs |= {"/mnt/app/eso/hmi/lsd/jars/" + m for m in _JAR_REF.findall(text)}
    for pid in sorted(profiles):
        targets = set(common)
        pm = files.get("profiles/%s/payload.manifest" % pid, b"").decode()
        targets |= {l.split()[2] for l in pm.splitlines() if l and not l.startswith("#") and len(l.split()) == 4}
        absent = sorted(refs - targets)
        check(not absent, "%s: boot path not installed by the package: %s" % (pid, ", ".join(absent)))


def check_target_scripts(files):
    """Every shell/awk file the unit runs must pass the MU1440 target-shell gate."""
    problems = []
    for rel in sorted(files):
        if not rel.startswith(("installer/", "common/", "profiles/")):
            continue  # source/ and docs are host material
        data = files[rel]
        if rel.endswith(TARGET_SHELL_SUFFIXES):
            problems += scan_text(data.decode("utf-8", "replace"), rel)
        elif rel.endswith(".awk"):
            problems += scan_awk_text(data.decode("utf-8", "replace"), rel)
    check(not problems, "target shell gate: " + "; ".join(problems[:5]))


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


def safe_rel(name):
    """True for a relative, normalized, forward-slash package path."""
    return (isinstance(name, str) and name != "" and not name.startswith("/") and "\\" not in name
            and all(p not in ("", ".", "..") for p in name.split("/")))


def read_directory(path):
    """Return {relative path: bytes} from an extracted package; symlinks are rejected."""
    base = Path(path)
    if not (base / "package.json").exists() and (base / PREFIX.rstrip("/") / "package.json").exists():
        base = base / PREFIX.rstrip("/")
    check(not base.is_symlink(), "symlink package root prohibited")
    files = {}
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        for name in sorted(dirnames) + sorted(filenames):
            full = Path(dirpath) / name
            rel = full.relative_to(base).as_posix()
            mode = os.lstat(full).st_mode
            check(not stat.S_ISLNK(mode), "symlink archive member prohibited: " + rel)
            if stat.S_ISREG(mode):
                check(safe_rel(rel), "unsafe archive path: " + rel)
                files[rel] = full.read_bytes()
            else:
                check(stat.S_ISDIR(mode), "special file prohibited: " + rel)
    return files


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


def check_meta(meta, files, profiles, selectors):
    """Status, provenance and install_enabled consistency of package.json."""
    status = meta["status"]
    check(isinstance(status, dict) and set(status) <= set(STATUS_KEYS), "unknown status field")
    for key, value in status.items():
        check(isinstance(value, bool) or value in STATUS_WORDS, "invalid status value for " + key)
    check(status.get("VEHICLE_RELEASE_APPROVED") in (False, None, "NOT_RUN", "BLOCKED"),
          "VEHICLE_RELEASE_APPROVED must never be true")
    check(not meta.get("vehicle_release_approved"), "VEHICLE_RELEASE_APPROVED must never be true")
    build = meta["native_build"]
    check(isinstance(build, dict) and all(isinstance(build.get(k), str) and build[k] for k in PROVENANCE),
          "missing native build provenance (%s)" % ", ".join(PROVENANCE))
    binaries = meta["binaries"]
    check(isinstance(binaries, list) and binaries, "missing binary provenance rows")
    seen = set()
    for row in binaries:
        p = row["path"]
        check(safe_rel(p) and p not in seen, "unsafe or duplicate binary row: %r" % (p,))
        seen.add(p)
        check(row["status"] in BINARY_STATUS, "invalid binary status: %s" % p)
        check(is_sha(row["sha256"]) and sha(need(files, p)) == row["sha256"], "binary hash mismatch: " + p)
        check(row["status"] != "SOURCE_BUILD_PASS" or isinstance(row.get("native_input"), str),
              "rebuilt binary lacks native_input: " + p)
    info = meta["profile_info"]
    check(isinstance(info, dict) and set(info) == profiles, "profile_info does not match profiles")
    rows = {r[1]: r for r in selectors}
    for pid, entry in info.items():
        row = rows[pid]
        check(isinstance(entry.get("install_enabled"), bool), "install_enabled must be boolean: " + pid)
        check(len(row) >= 4 and row[3] in ("0", "1") and entry["install_enabled"] == (row[3] == "1"),
              "install_enabled inconsistent with profiles.list: " + pid)
        check(entry.get("selector_sha256") == row[0], "selector mismatch in package.json: " + pid)
    check(meta["package_status"] in ("complete", "incomplete"), "invalid package_status")
    missing = meta["missing_inputs"]
    check(isinstance(missing, list) and (meta["package_status"] == "incomplete") == bool(missing),
          "package_status inconsistent with missing_inputs")
    check(meta["complete"] is (not missing), "complete flag inconsistent with missing_inputs")
    required = list(INSTALLER_REQUIRED) + ["profiles/%s/hmi/MIBR-CarPlay.jar" % p for p in sorted(profiles)]
    if "installer/config/payload.manifest" in files and \
            "/mnt/app/eso/hmi/lsd/jars/MIBR-Extender-P1-BootProbe.jar" in files.get("installer/config/lsd-block.txt", b"").decode().replace("$BASE_DIR", "/mnt/app/eso/hmi"):
        required.append("common/menu/bin/MIBR-Extender-P1-BootProbe.jar")
    for name in required:
        if name in files:
            check(name not in missing, "declared missing but present: " + name)
        else:
            check(name in missing, "required file absent but not declared MISSING_INPUT: " + name)
    return meta["package_status"]


def oem_hashes(files, profiles):
    out = set()
    for pid in profiles:
        for line in need(files, "profiles/%s/integration/variants.list" % pid).decode().splitlines():
            fields = line.split()
            if fields and not line.startswith("#") and len(fields) >= 3:
                out.update(fields[1:3])
    return out


def validate(path, require_complete=False):
    path = str(path)
    files = read_directory(path) if os.path.isdir(path) else read_archive(path)
    check(not any(n.startswith(("files/", "config/", "bin/")) for n in files), "legacy flat payload tree")
    meta = load_json(files, "package.json")
    try:
        profiles = package_profiles(meta)
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
        check(safe_rel(p), "unsafe path in package.json: %r" % (p,))
        need(files, p)
    check(set(listed) == set(files) - {"package.json", "PACKAGE.sha256"}, "unlisted package bytes")
    for p, digest in wanted.items():
        check(sha(files[p]) == digest, "hash mismatch: " + p)
    receipts = parse_package_sha(need(files, "PACKAGE.sha256"))
    actual = {n: sha(v) for n, v in files.items() if n != "PACKAGE.sha256"}
    check(receipts == actual, "PACKAGE.sha256 does not match package bytes")
    selectors = [line.split() for line in need(files, "installer/config/profiles.list").decode().splitlines()
                 if line and not line.startswith("#")]
    n = len(profiles)
    check(len(selectors) == n and all(len(r) == 4 and is_sha(r[0]) for r in selectors)
          and {r[1] for r in selectors} == profiles, "profile index mismatch")
    check(len({r[0] for r in selectors}) == n, "ambiguous selectors")
    try:
        state = check_meta(meta, files, profiles, selectors)
    except (KeyError, TypeError, AttributeError) as exc:
        raise PackageError("malformed package.json: %r" % (exc,)) from exc
    check(meta.get("profiles_list_sha256") == sha(files["installer/config/profiles.list"]),
          "profiles_list_sha256 mismatch")
    common = need(files, "installer/config/payload.manifest").decode()
    for pid in sorted(profiles):
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
            check(safe_rel(source), "unsafe payload source path: " + source)
            check(target not in targets, "%s duplicate target %s" % (pid, target))
            targets.add(target)
            check(sha(need(files, source)) == digest, "payload hash mismatch: " + source)
            if line in overlay_lines:
                check(source.startswith(root), "%s cross-profile payload %s" % (pid, source))
        for line in need(files, root + "integration/variants.list").decode().splitlines():
            if not line or line.startswith("#"):
                continue
            check_variant(files, root, line)
    check_target_scripts(files)
    if "installer/config/payload.manifest" in files and not meta.get("missing_inputs"):
        # an incomplete package (declared MISSING_INPUT) is never installable; check it once complete
        check_boot_references(files, profiles)
    oem = oem_hashes(files, profiles)
    for name, data in files.items():
        if name.startswith(("common/", "profiles/")):
            check(sha(data) not in oem, "OEM bytes in package (equals a stock/patched hash): " + name)
    source = load_json(files, "source/SOURCE_MANIFEST.json")
    try:
        check(source["coverage"] == "PARTIAL", "do not silently promote source coverage")
        check(source["files"], "empty source inventory")
        for row in source["files"]:
            check(sha(need(files, row["path"])) == row["sha256"], "source hash mismatch: " + row["path"])
    except (KeyError, TypeError) as exc:
        raise PackageError("malformed SOURCE_MANIFEST.json: %r" % (exc,)) from exc
    check(state == "complete" or not require_complete,
          "package is incomplete: " + ", ".join(meta["missing_inputs"]))
    print("MODULAR_PACKAGE_GATE=PASS profiles=%d files=%d status=%s" % (len(profiles), len(files), state))


def fixture_files(single=None, enabled=None):
    """A minimal package that satisfies every rule of the gate (test only)."""
    f = {
        "common/menu/config/mibr-menu.conf": b"menu\n",
        "common/payload/helper": b"helper\n",
        "common/bin/tool": b"\x7fELF tool\n",
        "tools/menu-editor/mibr-menu-editor.html": b"<html></html>\n",
        "source/doc.txt": b"source\n",
    }
    for name in INSTALLER_REQUIRED[:-1]:
        f[name] = b"#!/bin/ksh\nexit 0\n"
    profiles = {single} if single else PROFILES
    enabled = {"seat-mu1409-p4708": False} if enabled is None else enabled
    rows = ["# digest profile firmware enabled"] + [
        "%s %s FW_%d %d" % (sha(b"sel-%d" % i), p, i, 1 if enabled.get(p, True) else 0)
        for i, p in enumerate(sorted(profiles))]
    f["installer/config/profiles.list"] = ("\n".join(rows) + "\n").encode()
    f["installer/config/payload.manifest"] = ("%s 0755 /x/helper common/payload/helper\n"
                                              % sha(f["common/payload/helper"])).encode()
    for pid in profiles:
        root = "profiles/" + pid + "/"
        for g in GROUPS:
            f[root + g + "/file"] = (pid + g).encode()
        f[root + "hmi/MIBR-CarPlay.jar"] = b"PK jar " + pid.encode()
        f[root + "payload.manifest"] = ("%s 0644 /x/%s %sicons/file\n"
                                        % (sha(f[root + "icons/file"]), pid, root)).encode()
        f[root + "integration/si.awk"] = b"{ print }\n"
        f[root + "integration/variants.list"] = (
            "# target stock_sha256 patched_sha256 transform_file transform_sha256 mode\n"
            "/x/v1 %s %s %sintegration/si.awk %s 644\n"
            % (sha(b"stock"), sha(b"patched"), root, sha(f[root + "integration/si.awk"]))).encode()
    f["source/SOURCE_MANIFEST.json"] = json.dumps(
        {"coverage": "PARTIAL", "files": [{"path": "source/doc.txt", "sha256": sha(f["source/doc.txt"])}]}).encode()
    return seal(f, sorted(profiles), SINGLE_SCOPE if single else None)


def seal(f, profiles, scope=None, patch=None):
    """(Re)write package.json and PACKAGE.sha256 so they match the bytes in ``f``.
    ``patch(meta)`` may mutate the manifest before it is written (tests only)."""
    f = {k: v for k, v in f.items() if k not in ("package.json", "PACKAGE.sha256")}
    index = [l.split() for l in f["installer/config/profiles.list"].decode().splitlines()
             if l and not l.startswith("#")]
    missing = sorted(n for n in list(INSTALLER_REQUIRED) +
                     ["profiles/%s/hmi/MIBR-CarPlay.jar" % p for p in profiles] if n not in f)
    meta = {"profiles": profiles, "modules": ["carplay", "broker", "menu", "navigation"],
            "profile_info": {r[1]: {"install_enabled": r[3] == "1", "selector_sha256": r[0]}
                             for r in index if len(r) >= 4},
            "package_status": "incomplete" if missing else "complete", "complete": not missing,
            "missing_inputs": missing,
            "status": {"SOURCE_BUILD_PASS": True, "PACKAGE_VALIDATED": "NOT_RUN",
                       "UNIT_TESTED": "NOT_RUN", "VEHICLE_RELEASE_APPROVED": False},
            "native_build": {"source_commit": "0" * 40, "compiler": "gcc", "image_source": "img"},
            "binaries": [{"path": "common/bin/tool", "sha256": sha(f["common/bin/tool"]),
                          "status": "SOURCE_BUILD_PASS", "native_input": "bin/tool"}],
            "profiles_list_sha256": sha(f["installer/config/profiles.list"])}
    if scope:
        meta["scope"] = scope
    meta["files"] = [{"path": k, "sha256": sha(v)} for k, v in sorted(f.items())]
    if patch:
        patch(meta)
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
        # Single-profile scope and transform-based variants (no OEM bytes in the package).
        one = "skoda-mu1440-p4526"
        root = "profiles/" + one + "/"
        write_zip(path, fixture_files(one))
        validate(path)
        write_zip(path, fixture_files())
        validate(path)  # default three-profile contract unchanged

        def sealed(mutate, profiles=(one,), scope=SINGLE_SCOPE):
            f = fixture_files(one)
            mutate(f)
            return seal(f, list(profiles), scope)

        def variants(f, line):
            f[root + "integration/variants.list"] = line.encode()
        reject("single scope, unknown profile", "unknown profile",
               sealed(lambda f: None, profiles=("nonexistent-profile",)))
        reject("single scope, three profiles", "exactly one profile",
               sealed(lambda f: None, profiles=sorted(PROFILES)))
        reject("unknown scope", "unknown package scope", sealed(lambda f: None, scope="bogus"))
        reject("three profiles without scope, one declared", "unexpected profile set",
               sealed(lambda f: None, scope=None))
        good = "/x/v1 %s %s %sintegration/si.awk %s 644\n" % (sha(b"stock"), sha(b"patched"), root,
                                                             sha(b"{ print }\n"))
        reject("missing transform file", "missing package file",
               sealed(lambda f: (variants(f, good), f.pop(root + "integration/si.awk"))))
        reject("transform sha mismatch", "transform hash mismatch",
               sealed(lambda f: variants(f, good.replace(sha(b"{ print }\n"), sha(b"other")))))
        reject("non-hex stock sha", "64-hex", sealed(lambda f: variants(f, good.replace(sha(b"stock"), "zz"))))
        reject("variants line too short", "malformed variants line", sealed(lambda f: variants(f, "/x/v1 a b\n")))

        def printf_script(f):
            f["common/carplay/scripts/x.ksh"] = b"#!/bin/ksh\nprintf '%s\\n' x\n"
        reject("printf in a unit script", "target shell gate", sealed(printf_script))

        def new_awk(f):
            f[root + "integration/si.awk"] = b"BEGINFILE { x=1 }\n{ print }\n"
            variants(f, "/x/v1 %s %s %sintegration/si.awk %s 644\n"
                     % (sha(b"stock"), sha(b"patched"), root, sha(f[root + "integration/si.awk"])))
        reject("awk newer than GNU Awk 3.1.5", "target shell gate", sealed(new_awk))

        def boot_ref_missing(f):
            f["installer/config/lsd-block.txt"] = (
                b"[ -r /mnt/app/root/mibr/scripts/boot.ksh ] && /bin/ksh /mnt/app/root/mibr/scripts/boot.ksh\n"
                b"BOOTCLASSPATH=\"$BOOTCLASSPATH -Xbootclasspath/p:$BASE_DIR/lsd/jars/MIBR-CarPlay.jar\"\n")
        reject("lsd.sh block calls a file the package does not install", "boot path not installed",
               sealed(boot_ref_missing))

        def oem_named(f):
            f[root + "integration/smartphone_integrator.json"] = b"{}\n"
            variants(f, "/x/v1 %s %s %sintegration/smartphone_integrator.json %s 644\n"
                     % (sha(b"stock"), sha(b"patched"), root, sha(b"{}\n")))
        reject("OEM-looking payload in variants", "OEM-looking payload", sealed(oem_named))

        def oem_bytes(f):
            f[root + "integration/si.awk"] = b"stock"
            variants(f, "/x/v1 %s %s %sintegration/si.awk %s 644\n"
                     % (sha(b"stock"), sha(b"patched"), root, sha(b"stock")))
        reject("variant file equals stock bytes", "OEM bytes", sealed(oem_bytes))
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
        # Three-profile contract: consistency, provenance, status, OEM hashes, paths.
        def s3(mutate=None, patch=None, enabled=None):
            f = fixture_files(enabled=enabled)
            if mutate:
                mutate(f)
            return seal(f, sorted(PROFILES), None, patch)

        def meta_set(fn):
            return lambda m: fn(m)
        reject("install_enabled flipped vs profiles.list", "install_enabled inconsistent",
               s3(patch=lambda m: m["profile_info"]["seat-mu1409-p4708"].update(install_enabled=True)))
        reject("install_enabled not boolean", "must be boolean",
               s3(patch=lambda m: m["profile_info"]["seat-mu1409-p4708"].update(install_enabled="no")))
        reject("profiles.list wrong column count", "profile index mismatch",
               s3(lambda f: f.update({"installer/config/profiles.list": b"# h\n" + b"x y\n" * 3})))
        for key in ("source_commit", "compiler", "image_source"):
            reject("missing provenance " + key, "missing native build provenance",
                   s3(patch=lambda m, k=key: m["native_build"].pop(k)))
        reject("no binary rows", "missing binary provenance",
               s3(patch=lambda m: m.update(binaries=[])))
        reject("binary hash mismatch", "binary hash mismatch",
               s3(patch=lambda m: m["binaries"][0].update(sha256=sha(b"other"))))
        reject("binary status approved", "invalid binary status",
               s3(patch=lambda m: m["binaries"][0].update(status="VEHICLE_RELEASE_APPROVED")))
        reject("binary status unknown", "invalid binary status",
               s3(patch=lambda m: m["binaries"][0].update(status="FINE")))
        reject("VEHICLE_RELEASE_APPROVED true", "never be true",
               s3(patch=lambda m: m["status"].update(VEHICLE_RELEASE_APPROVED=True)))
        reject("vehicle_release_approved flag", "never be true",
               s3(patch=lambda m: m.update(vehicle_release_approved=True)))
        reject("unknown status field", "unknown status field",
               s3(patch=lambda m: m["status"].update(SHIPPED=True)))
        reject("invalid status value", "invalid status value",
               s3(patch=lambda m: m["status"].update(UNIT_TESTED="MAYBE")))
        reject("OEM stock hash under common/", "OEM bytes in package",
               s3(lambda f: f.update({"common/payload/oem": b"stock"})))
        reject("OEM patched hash under profiles/", "OEM bytes in package",
               s3(lambda f: f.update({root + "display/oem": b"patched"})))
        reject("absolute path in inventory", "unsafe path in package.json",
               s3(patch=lambda m: m["files"].append({"path": "/etc/passwd", "sha256": sha(b"x")})))
        reject("dot-dot path in inventory", "unsafe path in package.json",
               s3(patch=lambda m: m["files"].append({"path": "../x", "sha256": sha(b"x")})))
        reject("dot-dot payload source", "unsafe payload source path",
               s3(lambda f: f.update({"installer/config/payload.manifest":
                                      ("%s 0644 /x/y ../x\n" % sha(b"x")).encode()})))
        reject("required installer file absent, undeclared", "not declared MISSING_INPUT",
               s3(patch=lambda m: (m.update(missing_inputs=[], complete=True, package_status="complete")),
                  mutate=lambda f: f.pop("installer/mibr-status.ksh")))
        reject("declared missing but present", "declared missing but present",
               s3(patch=lambda m: m.update(missing_inputs=["installer/mibr-status.ksh"], complete=False,
                                           package_status="incomplete")))
        reject("complete flag lies", "complete flag inconsistent",
               s3(patch=lambda m: m.update(complete=False)))
        # Incomplete (declared MISSING_INPUT) passes structurally, fails --require-complete.
        inc = s3(lambda f: f.pop("profiles/seat-mu1447-p4709/hmi/MIBR-CarPlay.jar"))
        write_zip(path, inc)
        validate(path)
        try:
            validate(path, require_complete=True)
            raise RuntimeError("accepted incomplete package under --require-complete")
        except PackageError as exc:
            if "incomplete" not in str(exc):
                raise
        # Extracted directory form: accepted, and symlinks / special files rejected.
        full = s3()
        for sub in ("", PREFIX):
            d = Path(td) / ("dir" + str(len(sub)))
            for n, v in full.items():
                (d / sub / n).parent.mkdir(parents=True, exist_ok=True)
                (d / sub / n).write_bytes(v)
            validate(d)
        link = Path(td) / "dir0" / "source" / "link"
        link.symlink_to("doc.txt")
        try:
            validate(Path(td) / "dir0")
            raise RuntimeError("accepted symlink in extracted directory")
        except PackageError as exc:
            if "symlink" not in str(exc):
                raise
        link.unlink()
        # Regression: flat payload roots and archive traversal must never be accepted.
        for name in ("MIBR-CarPlay/files/profiles/old/file", "MIBR-CarPlay/../escape", "other/file"):
            reject("invalid layout " + name, "", files={}, extra=[(name, b"invalid layout")])
    print("MODULAR_PACKAGE_GATE_SELF_TEST=PASS")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("zip", nargs="?", help="package ZIP or extracted package directory")
    p.add_argument("--require-complete", action="store_true",
                   help="fail an incomplete package (declared MISSING_INPUT)")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if not args.self_test and not args.zip:
        p.error("supply a ZIP and/or --self-test")
    try:
        if args.self_test:
            self_test()
        if args.zip:
            validate(args.zip, args.require_complete)
    except PackageError as exc:
        print("MODULAR_PACKAGE_GATE=FAIL " + str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
