#!/usr/bin/env python3
"""Stage immutable Research r11b binary inputs without rebuilding on public CI.

The exact private reference ZIP and current public source-object identities are
both pinned. The original Research compiler/source provenance is preserved.
No external archive member is extracted by its untrusted filename.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK_FILE = ROOT / "tools/release/RESEARCH_PREBUILT_LOCK.json"
RECEIPT = "RESEARCH_PREBUILT_RECEIPT.json"
PREFIX = "MIBR-CarPlay/"
EXTENDER = "MIBR-Extender-P1-BootProbe.jar"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class PrebuiltError(ValueError):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True,
        text=True, capture_output=True,
    ).stdout.strip()


def load_lock(path=LOCK_FILE):
    lock = json.loads(Path(path).read_text(encoding="utf-8"))
    if lock.get("schema") != 1 or not HEX64.fullmatch(lock.get("archive_sha256", "")):
        raise PrebuiltError("RESEARCH_LOCK_INVALID")
    if not HEX40.fullmatch(lock.get("research_commit", "")):
        raise PrebuiltError("RESEARCH_COMMIT_INVALID")
    objects = lock.get("git_objects")
    if not isinstance(objects, dict) or not objects:
        raise PrebuiltError("RESEARCH_SOURCE_LOCK_EMPTY")
    for path, oid in objects.items():
        if not path or path.startswith("/") or ".." in Path(path).parts or not HEX40.fullmatch(oid):
            raise PrebuiltError("RESEARCH_SOURCE_LOCK_BAD_OBJECT")
    return lock


def verify_sources(repo=ROOT, lock=None):
    lock = lock if lock is not None else load_lock()
    changed = []
    for path, expected in sorted(lock["git_objects"].items()):
        try:
            found = git(repo, "rev-parse", "--verify", "HEAD:" + path)
        except subprocess.CalledProcessError:
            found = "<missing>"
        if found != expected:
            changed.append(path)
    dirty = git(repo, "status", "--porcelain", "--untracked-files=all",
                "--", *sorted(lock["git_objects"]))
    if dirty:
        changed.append("uncommitted native source")
    if changed:
        raise PrebuiltError("RESEARCH_NATIVE_PREBUILT_STALE: " + ", ".join(changed[:12])
                            + "; rebuild and independently approve the native inputs")
    return {"method": "reviewed_git_objects",
            "reviewed_public_source_commit": lock["reviewed_public_source_commit"],
            "checked_objects": len(lock["git_objects"]), "stale_inputs": []}


def native_map():
    # Import only after module loading: assembler imports our verify_staged().
    import build_modular
    return {row[1][0]: PREFIX + row[0] for row in build_modular.NATIVE}


def package_checksums(data):
    result = {}
    for line in data.decode("ascii").splitlines():
        digest, sep, path = line.partition("  ")
        if sep != "  " or not HEX64.fullmatch(digest) or not path or path in result:
            raise PrebuiltError("REFERENCE_PACKAGE_SHA256_INVALID")
        result[path] = digest
    return result


def staging_path(root, relative):
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise PrebuiltError("UNSAFE_NATIVE_STAGE_PATH")
    path = Path(root) / rel
    if path.exists() or path.is_symlink():
        raise PrebuiltError("STAGE_REFUSES_EXISTING_FILE: " + relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def stage(repo, archive, native, hmi, lock=None):
    lock = lock if lock is not None else load_lock()
    verify_sources(repo, lock)
    if sha256_file(archive) != lock["archive_sha256"]:
        raise PrebuiltError("RESEARCH_ARCHIVE_SHA256_MISMATCH")
    outputs = native_map()
    checksum = {}
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise PrebuiltError("RESEARCH_ARCHIVE_CRC_INVALID")
        archive_files = set(z.namelist())
        meta = json.loads(z.read(PREFIX + "package.json"))
        if (meta.get("version") != lock["reference_version"]
                or not meta.get("complete")
                or set(meta.get("profiles", ())) != set(lock["profiles"])):
            raise PrebuiltError("RESEARCH_REFERENCE_PROFILE_OR_VERSION_MISMATCH")
        sums = package_checksums(z.read(PREFIX + "PACKAGE.sha256"))
        binary_rows = {row["path"]: row["sha256"] for row in meta["binaries"]}
        for rel, member in sorted(outputs.items()):
            inside = member.removeprefix(PREFIX)
            if member not in archive_files or inside not in sums:
                raise PrebuiltError("RESEARCH_BINARY_MISSING: " + inside)
            data = z.read(member)
            digest = hashlib.sha256(data).hexdigest()
            if sums[inside] != digest or binary_rows.get(inside) != digest:
                raise PrebuiltError("RESEARCH_BINARY_HASH_MISMATCH: " + inside)
            staging_path(native, rel).write_bytes(data)
            checksum[rel] = digest
        ext_member = PREFIX + "common/menu/bin/" + EXTENDER
        ext_name = ext_member.removeprefix(PREFIX)
        if ext_member not in archive_files or ext_name not in sums:
            raise PrebuiltError("RESEARCH_EXTENDER_MISSING")
        extender = z.read(ext_member)
        ext_sha = hashlib.sha256(extender).hexdigest()
        if ext_sha != sums[ext_name]:
            raise PrebuiltError("RESEARCH_EXTENDER_SHA256_MISMATCH")
        staging_path(hmi, "common/" + EXTENDER).write_bytes(extender)
        provenance = {}
        for key in ("source_commit", "compiler", "image_source"):
            value = meta.get("native_build", {}).get(key)
            if not isinstance(value, str) or not value.strip():
                raise PrebuiltError("RESEARCH_NATIVE_PROVENANCE_MISSING: " + key)
            provenance[key] = value.strip()
        if not HEX40.fullmatch(provenance["source_commit"]):
            raise PrebuiltError("RESEARCH_NATIVE_SOURCE_COMMIT_INVALID")
    for key, filename in (("source_commit", "SOURCE_COMMIT.txt"),
                          ("compiler", "COMPILER.txt"), ("image_source", "IMAGE_SOURCE.txt")):
        staging_path(native, filename).write_text(provenance[key] + "\n", encoding="utf-8")
    # Existing assembler verifies this native sub-tree when a manifest is present.
    mu = Path(native) / "bin/mu1440-source"
    lines = []
    for rel, digest in sorted(checksum.items()):
        if rel.startswith("bin/mu1440-source/"):
            lines.append(digest + "  " + rel.removeprefix("bin/mu1440-source/"))
    staging_path(native, "bin/mu1440-source/SHA256SUMS").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    receipt = {"schema": 1, "archive_sha256": lock["archive_sha256"],
               "research_commit": lock["research_commit"],
               "native_files": checksum, "extender_sha256": ext_sha,
               "native_provenance": provenance}
    staging_path(native, RECEIPT).write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    verify_staged(repo, native, hmi, lock)
    print("RESEARCH_PREBUILTS_STAGED=PASS native_files=%d archive_sha256=%s"
          % (len(checksum), lock["archive_sha256"]))


def verify_staged(repo=ROOT, native=None, hmi=None, lock=None):
    lock = lock if lock is not None else load_lock()
    freshness = verify_sources(repo, lock)
    if native is None or hmi is None:
        raise PrebuiltError("RESEARCH_STAGE_DIRS_REQUIRED")
    path = Path(native) / RECEIPT
    if not path.is_file() or path.is_symlink():
        raise PrebuiltError("RESEARCH_RECEIPT_MISSING")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if (receipt.get("schema") != 1
            or receipt.get("archive_sha256") != lock["archive_sha256"]
            or receipt.get("research_commit") != lock["research_commit"]):
        raise PrebuiltError("RESEARCH_RECEIPT_ORIGIN_MISMATCH")
    expected = native_map()
    hashes = receipt.get("native_files")
    if not isinstance(hashes, dict) or set(hashes) != set(expected):
        raise PrebuiltError("RESEARCH_NATIVE_FILE_SET_MISMATCH")
    for rel, digest in sorted(hashes.items()):
        f = Path(native) / rel
        if not HEX64.fullmatch(digest) or not f.is_file() or f.is_symlink():
            raise PrebuiltError("RESEARCH_NATIVE_FILE_INVALID: " + rel)
        if sha256_file(f) != digest:
            raise PrebuiltError("RESEARCH_NATIVE_FILE_CHANGED: " + rel)
    ext = Path(hmi) / "common" / EXTENDER
    if (not ext.is_file() or ext.is_symlink()
            or sha256_file(ext) != receipt.get("extender_sha256")):
        raise PrebuiltError("RESEARCH_EXTENDER_CHANGED")
    prov = receipt.get("native_provenance", {})
    for key, filename in (("source_commit", "SOURCE_COMMIT.txt"),
                          ("compiler", "COMPILER.txt"), ("image_source", "IMAGE_SOURCE.txt")):
        f = Path(native) / filename
        if not isinstance(prov.get(key), str) or not f.is_file() or f.is_symlink():
            raise PrebuiltError("RESEARCH_PROVENANCE_INVALID: " + key)
        if f.read_text(encoding="utf-8").strip() != prov[key]:
            raise PrebuiltError("RESEARCH_PROVENANCE_CHANGED: " + key)
    freshness["built_from"] = prov["source_commit"]  # Research, not public main.
    freshness["reference_archive_sha256"] = lock["archive_sha256"]
    return freshness


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", type=Path)
    ap.add_argument("--out-native", type=Path)
    ap.add_argument("--out-hmi", type=Path)
    ap.add_argument("--check-sources", action="store_true")
    args = ap.parse_args()
    try:
        if args.check_sources:
            gate = verify_sources()
            print("RESEARCH_NATIVE_SOURCE=PASS objects=" + str(gate["checked_objects"]))
        else:
            if not all((args.archive, args.out_native, args.out_hmi)):
                ap.error("--archive, --out-native and --out-hmi are required")
            stage(ROOT, args.archive, args.out_native, args.out_hmi)
    except (PrebuiltError, KeyError, OSError, ValueError, zipfile.BadZipFile,
            subprocess.CalledProcessError) as exc:
        raise SystemExit("RESEARCH_PREBUILT=BLOCKED " + str(exc)) from exc


if __name__ == "__main__":
    main()
