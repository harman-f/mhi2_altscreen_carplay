#!/usr/bin/env python3
"""Create a deterministic source-only snapshot from this repository's public Git tree.

The archive is a review/source handoff. It is not an install kit, release payload,
or vehicle-qualified artifact. Only committed text/source files named by the exact
path allowlist are considered; files are read from Git objects, never the working tree.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile
from typing import Iterable


ALLOWLIST_PATH = "tools/source-package-v1.paths"
ALLOWED_DIRECTORY_PREFIXES = (
    "deployment/mu1440/",
    "deployment/mu1440-parity-drive-v1/",
    "runtime/auto-direct/",
    "runtime/deployment/",
    "runtime/diagnostics/",
    "runtime/isotx2-gate/",
    "runtime/mibr-control/",
    "runtime/navigation/",
    "runtime/parity/",
    "settings/",
    "src/hmi/oem-menu/",
    "src/native/altscreen111-gen2/",
    "src/native/alt111-settings/",
    "src/native/direct-ts-parity/",
    "src/native/direct-ts-remux/",
    "src/native/isotx2-gate/",
    "src/native/mibr-control/",
    "src/native/most-ts-writer/",
    "src/native/parity-session/",
    "src/native/sha256sum-compat/",
    "src/native/tee-compat/",
    "src/native/vehicle-data/",
    "tests/mibr-control/",
)
ALLOWED_ROOT_FILES = {
    "README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "LICENSE",
    "THIRD_PARTY_NOTICES.md", ALLOWLIST_PATH, "tools/package_source_v1.py",
    "tests/test_package_source_v1.py",
    "tools/build_alt111_settings.sh", "tools/build_altscreen111_gen2.sh",
    "tools/build_direct_ts_parity.sh", "tools/build_direct_ts_remux.sh",
    "tools/build_mibr_control.sh", "tools/build_native_isotx2_guard.sh",
    "tools/build_parity_session.sh", "tools/build_qnx65_image.sh",
    "tools/build_support_tools.sh", "tools/build_mu1440_source.sh",
    "tools/generate_alt111_settings.py", "tools/check_mu1440_target_shell.py",
    "tools/test_gen2_components_host.sh", "tools/test_installed_gen2_host.sh",
    "tools/test_parity_host.sh", "tools/test_alt111_zoom_host.sh",
    "LICENSES/LGPL-2.1-or-later.txt",
    "THIRD_PARTY/NavIgnore/README.md", "THIRD_PARTY/NavIgnore/LICENSE-MIT.txt",
    "THIRD_PARTY/Most20FPS/README.md", "THIRD_PARTY/Most20FPS/LICENSE-MIT.txt",
    ".github/workflows/build-mu1440-source.yml",
    ".github/workflows/build-support-tools.yml",
    ".github/workflows/publication-audit.yml",
    ".github/workflows/source-package-v1.yml",
    "docs/build/SOURCE_PACKAGE_V1.md", "docs/build/MU1440_R57_SOURCE.md",
    "docs/architecture/README.md", "docs/architecture/AUTO_DIRECT_RUNTIME.md",
    "docs/architecture/DIRECT_VC_VIDEO_PATH.md",
    "docs/architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md",
    "docs/architecture/NAVIGATION_COMPOSITION_AND_SAFEAREA.md",
    "docs/architecture/RUNTIME_CONTRACT.md", "docs/architecture/SCREENALT_CONTROL_PLANE.md",
    "docs/architecture/SYSTEM_OVERVIEW.md",
    "docs/architecture/mibr-control/BUILD_AND_EVIDENCE.md",
}
ALLOWED_TOP_TEST_RE = re.compile(
    r"tests/(?:alt111_[A-Za-z0-9_.-]+|direct_ts_parity_[A-Za-z0-9_.-]+|"
    r"parity_session_(?:lifecycle|logging)\.py|test_three_views\.c|test_public_mibr3\.py|"
    r"test_vdata\.c|test_vstatus\.c)"
)
EXCLUDED_COMPONENTS = {"artifacts", "release", ".research"}
EXCLUDED_PREFIXES = ("docs/research/", "src/experimental/", "runtime/experimental/")
EXCLUDED_EXACT_PATHS = {
    "docs/build/DIRECT_TS_REMUX_BUILD.md",
    "runtime/navigation/gen2_safearea.sh",
}
SOURCE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".ipp",
    ".java", ".js", ".ts", ".py", ".sh", ".ksh", ".json", ".md", ".txt",
    ".yaml", ".yml", ".toml", ".xml", ".properties", ".cmake", ".mk", ".cfg",
    ".conf", ".ini", ".csv", ".sql", ".gradle", ".kt", ".s", ".S".lower(),
    ".diff", ".patch", ".rst", ".adoc", ".html", ".css", ".gitignore",
    ".gitattributes", ".paths",
}
SOURCE_FILENAMES = {
    "makefile", "dockerfile", "license", "license.md", "license.txt", "notice",
    "notice.md", "notice.txt", ".gitignore", ".gitattributes", ".editorconfig",
}
WORKFLOW_CONTEXT_ENV = {
    "event_name": "GITHUB_EVENT_NAME",
    "workflow": "GITHUB_WORKFLOW",
    "run_id": "GITHUB_RUN_ID",
    "run_attempt": "GITHUB_RUN_ATTEMPT",
    "pr_base_sha": "SOURCE_PACKAGE_PR_BASE_SHA",
    "pr_head_sha": "SOURCE_PACKAGE_PR_HEAD_SHA",
}
BINARY_SUFFIXES = {
    ".a", ".apk", ".avi", ".bin", ".bmp", ".class", ".dat", ".dll", ".dylib",
    ".elf", ".exe", ".gif", ".gz", ".h264", ".ico", ".jar", ".jpeg", ".jpg",
    ".jxe", ".m4a", ".mov", ".mp3", ".mp4", ".o", ".obj", ".otf", ".pdf",
    ".png", ".pyc", ".pyo", ".so", ".tar", ".tgz", ".ttf", ".wav", ".webp",
    ".woff", ".woff2", ".zip", ".7z",
}
PACKAGE_KIND = "PUBLIC_SOURCE_ONLY_NOT_AN_INSTALL_KIT_NOT_VEHICLE_QUALIFIED"
MANIFEST_NAME = "SOURCE_ONLY_MANIFEST.json"


class PackageError(RuntimeError):
    """Raised when the selected Git tree is not safe to package as source-only."""


def _git(repo: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"")
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", "replace").strip()
        raise PackageError(f"git {' '.join(args)} failed: {detail or exc}") from exc
    return result.stdout


def _is_excluded(path: str) -> bool:
    folded = path.casefold()
    parts = folded.split("/")
    if folded in {item.casefold() for item in EXCLUDED_EXACT_PATHS}:
        return True
    if any(part in EXCLUDED_COMPONENTS for part in parts):
        return True
    return any(folded.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def _is_source_path(path: str) -> bool:
    name = PurePosixPath(path).name.casefold()
    suffix = PurePosixPath(path).suffix.casefold()
    return name in SOURCE_FILENAMES or suffix in SOURCE_SUFFIXES


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_identity(repo: Path, ref: str) -> tuple[str, str]:
    commit = _git(repo, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").decode("ascii").strip()
    tree_sha = _git(repo, "rev-parse", "--verify", f"{commit}^{{tree}}").decode("ascii").strip()
    return commit, tree_sha


def _allowed_path(path: str) -> bool:
    if path in ALLOWED_ROOT_FILES:
        return True
    if any(path.startswith(prefix) for prefix in ALLOWED_DIRECTORY_PREFIXES):
        return True
    return bool(ALLOWED_TOP_TEST_RE.fullmatch(path))


def parse_allowlist(data: bytes) -> list[str]:
    """Validate the committed path list and return its exact, ordered entries."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PackageError("source path allowlist is not UTF-8") from exc
    paths: list[str] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(text.splitlines(), 1):
        if not raw:
            continue
        if raw != raw.strip() or raw.startswith("#"):
            raise PackageError(f"allowlist line {line_number} must be a plain path without comments/whitespace")
        path = raw
        pure = PurePosixPath(path)
        if (pure.is_absolute() or "\\" in path or re.match(r"^[A-Za-z]:", path)
                or any(part in ("", ".", "..") for part in path.split("/"))):
            raise PackageError(f"allowlist path must be relative and normalized: {path!r}")
        if any(c in path for c in "*?[]"):
            raise PackageError(f"glob syntax is not allowed in path allowlist: {path!r}")
        if _is_excluded(path):
            raise PackageError(f"excluded path in allowlist: {path}")
        if not _allowed_path(path):
            raise PackageError(f"path is outside the curated product closure: {path}")
        if PurePosixPath(path).suffix.casefold() in BINARY_SUFFIXES:
            raise PackageError(f"binary extension is not allowed in source package: {path}")
        key = path.casefold()
        if key in seen:
            raise PackageError(f"duplicate path in allowlist: {path}")
        seen.add(key)
        paths.append(path)
    if ALLOWLIST_PATH not in paths:
        raise PackageError(f"allowlist must include itself: {ALLOWLIST_PATH}")
    if not paths:
        raise PackageError("source path allowlist is empty")
    return paths


def _tree_blob(repo: Path, commit: str, path: str) -> tuple[str, str, str]:
    raw = _git(repo, "ls-tree", "-r", "-z", "--full-tree", commit, "--", f":(literal){path}")
    records = [record for record in raw.split(b"\0") if record]
    if len(records) != 1:
        raise PackageError(f"allowlisted path is missing or not a single file in {commit}: {path}")
    try:
        metadata, raw_path = records[0].split(b"\t", 1)
        mode, kind, object_sha = metadata.decode("ascii").split(" ")
        actual_path = raw_path.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise PackageError(f"unsupported Git tree entry for {path}") from exc
    if actual_path != path:
        raise PackageError(f"allowlisted path did not resolve exactly: {path}")
    return mode, kind, object_sha


def collect_source(repo: Path, ref: str = "HEAD") -> tuple[dict, dict[str, bytes]]:
    """Read only exact, committed paths named by the selected commit's allowlist."""
    repo = repo.resolve(strict=True)
    commit, tree_sha = _git_identity(repo, ref)
    allowlist_mode, allowlist_kind, allowlist_sha = _tree_blob(repo, commit, ALLOWLIST_PATH)
    if allowlist_mode not in ("100644", "100755") or allowlist_kind != "blob":
        raise PackageError("source path allowlist must be a regular Git text blob")
    paths = parse_allowlist(_git(repo, "cat-file", "blob", allowlist_sha))
    selected: dict[str, bytes] = {}
    git_modes: dict[str, str] = {}
    for path in paths:
        mode, kind, object_sha = _tree_blob(repo, commit, path)
        if mode == "120000":
            raise PackageError(f"symlink is not allowed in a product root: {path}")
        if mode == "160000" or kind == "commit":
            raise PackageError(f"submodule is not allowed in a product root: {path}")
        if kind != "blob":
            raise PackageError(f"unsupported Git object in product root: {path}")
        if mode not in ("100644", "100755"):
            raise PackageError(f"unsupported regular-file mode for {path}: {mode}")
        if not _is_source_path(path) and path != ALLOWLIST_PATH:
            raise PackageError(f"allowlisted path is not an approved source/text file: {path}")
        data = _git(repo, "cat-file", "blob", object_sha)
        if b"\0" in data:
            raise PackageError(f"NUL byte in text/source file: {path}")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PackageError(f"non-UTF-8 bytes in text/source file: {path}") from exc
        selected[path] = data
        git_modes[path] = mode

    if not selected:
        raise PackageError("the selected commit contains no eligible public source files")
    file_rows = [
        {"path": path, "git_mode": git_modes[path], "size_bytes": len(data), "sha256": _sha256(data)}
        for path, data in sorted(selected.items())
    ]
    manifest = {
        "schema_version": 1,
        "package_kind": PACKAGE_KIND,
        "source_repository": "harman-f/mhi2_altscreen_carplay",
        "source_commit": commit,
        "source_tree": tree_sha,
        "allowlist_path": ALLOWLIST_PATH,
        "allowlist_sha256": _sha256(_git(repo, "cat-file", "blob", allowlist_sha)),
        "allowlist_entries": len(paths),
        "excluded_path_rules": {
            "components_case_insensitive": sorted(EXCLUDED_COMPONENTS),
            "prefixes_case_insensitive": list(EXCLUDED_PREFIXES),
            "exact_paths_case_insensitive": sorted(EXCLUDED_EXACT_PATHS),
            "binary_extensions": sorted(BINARY_SUFFIXES),
        },
        "files": file_rows,
    }
    return manifest, selected


def _tar_bytes(manifest: dict, files: dict[str, bytes]) -> bytes:
    manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    import io

    with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=9) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                members = [(MANIFEST_NAME, manifest_bytes, 0o644)]
                source_modes = {entry["path"]: entry["git_mode"] for entry in manifest["files"]}
                members.extend((f"source/{path}", data, 0o755 if source_modes[path] == "100755" else 0o644)
                               for path, data in sorted(files.items()))
                for name, data, mode in sorted(members, key=lambda item: item[0]):
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mode = mode
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    info.type = tarfile.REGTYPE
                    info.pax_headers = {}
                    archive.addfile(info, io.BytesIO(data))
        raw.seek(0)
        return raw.read()


def _write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise PackageError(f"refusing to overwrite existing output: {path}")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, path)
        except FileExistsError as exc:
            raise PackageError(f"refusing to overwrite existing output: {path}") from exc
    finally:
        temp.unlink(missing_ok=True)


def build_package(repo: Path, output: Path, ref: str = "HEAD") -> tuple[Path, Path, Path, dict]:
    repo = repo.resolve(strict=True)
    output = output.expanduser().resolve(strict=False)
    try:
        output.relative_to(repo)
    except ValueError:
        pass
    else:
        raise PackageError("output must be outside the repository checkout")
    provenance_path = output.with_name(output.name + ".provenance.json")
    checksum_path = output.with_name(output.name + ".sha256")
    if any(path.exists() for path in (output, provenance_path, checksum_path)):
        raise PackageError("refusing to overwrite an existing package, provenance, or checksum file")

    manifest, files = collect_source(repo, ref)
    archive_bytes = _tar_bytes(manifest, files)
    provenance = {
        **manifest,
        "workflow_context": {
            field: os.environ.get(variable) or None
            for field, variable in WORKFLOW_CONTEXT_ENV.items()
        },
        "archive": {
            "filename": output.name,
            "size_bytes": len(archive_bytes),
            "sha256": _sha256(archive_bytes),
            "manifest_member": MANIFEST_NAME,
        },
    }
    provenance_bytes = (json.dumps(provenance, sort_keys=True, indent=2) + "\n").encode("utf-8")
    checksum_bytes = (
        f"{_sha256(archive_bytes)}  {output.name}\n"
        f"{_sha256(provenance_bytes)}  {provenance_path.name}\n"
    ).encode("ascii")

    # Each output is created with no-overwrite semantics. If a later write fails,
    # preserve already-created evidence rather than silently replacing it.
    _write_new(output, archive_bytes)
    _write_new(provenance_path, provenance_bytes)
    _write_new(checksum_path, checksum_bytes)
    return output, provenance_path, checksum_path, provenance


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ref", default="HEAD", help="Git commit, tag, or ref; resolved to an immutable commit")
    parser.add_argument("--output", type=Path, required=True, help="new .tar.gz path outside the repository")
    args = parser.parse_args(argv)
    try:
        archive, provenance, checksums, record = build_package(args.repo, args.output, args.ref)
    except PackageError as exc:
        parser.error(str(exc))
    print(f"SOURCE_ONLY_ARCHIVE={archive}")
    print(f"DETACHED_PROVENANCE={provenance}")
    print(f"CHECKSUMS={checksums}")
    print(f"SOURCE_COMMIT={record['source_commit']}")
    print(f"SOURCE_TREE={record['source_tree']}")
    print(f"PACKAGE_KIND={PACKAGE_KIND}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
