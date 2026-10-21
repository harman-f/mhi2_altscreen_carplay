#!/usr/bin/env python3
"""Dependency-free publication integrity audit."""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
    "ROADMAP.md",
    "ACKNOWLEDGEMENTS.md",
    "docs/status/CURRENT_DEVELOPMENT_STATUS.md",
    "docs/findings/KNOWN_ISSUES.md",
    "docs/testing/COMPATIBILITY_MATRIX.md",
    "docs/research/MU1440_STOCK_REFERENCE.md",
    "docs/research/IOS27_SENDER_LIFECYCLE.md",
    "docs/research/PUBLIC_REFERENCES.md",
    "docs/PUBLICATION_PRIVACY.md",
    "docs/README.md",
    "docs/testing/VEHICLE_TEST_PROTOCOL.md",
    "docs/architecture/AUTO_DIRECT_RUNTIME.md",
    "docs/architecture/RUNTIME_CONTRACT.md",
    "docs/research/MU1440_GEN2_HOOK_MAP.md",
    "docs/research/JAVA_J9_BUILD_NOTES.md",
    "runtime/README.md",
    "src/native/altscreen111-gen2/DEVELOPMENT.md",
]

HASHED_ARTIFACTS = [
    (
        "artifacts/mu1440/direct-ts-remux/vehicle-proven-run143/direct-ts-remux",
        "artifacts/mu1440/direct-ts-remux/vehicle-proven-run143/direct-ts-remux.sha256",
    ),
    (
        "artifacts/mu1440/altscreen111/experimental-gen2-2026-09-25/libaltscreen111.so",
        "artifacts/mu1440/altscreen111/experimental-gen2-2026-09-25/libaltscreen111.so.sha256",
    ),
]

FORBIDDEN_SUFFIXES = {
    ".ipsw",
    ".jxe",
    ".img",
    ".ifs",
    ".rom",
    ".dump",
    ".heic",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".mov",
    ".mp4",
    ".7z",
    ".rar",
    ".zip",
}

FORBIDDEN_PATH_PARTS = {
    ".transfer",
    "__pycache__",
}

# Curated public vehicle-evidence media. Keep this allowlist deliberately narrow:
# binary image/video files remain forbidden everywhere else in the repository.
PUBLIC_MEDIA_ROOT = Path("docs/media/mu1440-stream111-poc-2026-09-29")
PUBLIC_MEDIA_SUFFIXES = {".jpg", ".jpeg", ".mp4"}

MAX_FILE_SIZE = 5 * 1024 * 1024

SECRET_PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(rb"https?://[^\s/:]+:[^\s/@]+@"),
]

# Public docs and source must not leak a distinct, non-public development identity.
# Audit the full checked-out current tree; this does NOT sanitize Git history,
# pull request discussions or hosted external attachments.
PRIVATE_DEVELOPMENT_REFERENCES = re.compile(
    rb"(?:CaneTLOTW|M[.]I[.]B[._]Research)", re.IGNORECASE
)
TEXT_PUBLICATION_SUFFIXES = {
    ".md", ".txt", ".csv", ".tsv", ".json", ".yml", ".yaml",
    ".py", ".sh", ".ksh", ".h", ".c", ".cc", ".cpp", ".java", ".toml",
}

MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def tracked_files() -> list[Path]:
    out: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        out.append(path)
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_required(errors: list[str]) -> None:
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            fail(errors, f"missing required publication file: {rel}")


def audit_artifact_hashes(errors: list[str]) -> None:
    for artifact_rel, sidecar_rel in HASHED_ARTIFACTS:
        artifact = ROOT / artifact_rel
        sidecar = ROOT / sidecar_rel
        if not artifact.is_file() or not sidecar.is_file():
            fail(errors, f"missing canonical artifact/hash pair: {artifact_rel}")
            continue
        expected = sidecar.read_text(encoding="utf-8").strip().split()[0].lower()
        actual = sha256(artifact)
        if actual != expected:
            fail(
                errors,
                f"artifact hash mismatch: {artifact_rel}: expected {expected}, got {actual}",
            )


def audit_tree(errors: list[str], files: list[Path]) -> None:
    for path in files:
        rel = path.relative_to(ROOT)
        low = path.name.lower()

        if any(part in FORBIDDEN_PATH_PARTS for part in rel.parts):
            fail(errors, f"temporary/private staging path committed: {rel}")

        suffix = path.suffix.lower()
        is_curated_public_media = (
            rel.is_relative_to(PUBLIC_MEDIA_ROOT)
            and suffix in PUBLIC_MEDIA_SUFFIXES
        )

        if any(low.endswith(blocked) for blocked in FORBIDDEN_SUFFIXES):
            if not is_curated_public_media:
                fail(errors, f"forbidden publication artifact type: {rel}")

        if "dyld_shared_cache" in low:
            fail(errors, f"dyld cache material must not be committed: {rel}")

        size = path.stat().st_size
        if size > MAX_FILE_SIZE:
            fail(errors, f"unexpected large file ({size} bytes): {rel}")

        data = path.read_bytes()
        if suffix in TEXT_PUBLICATION_SUFFIXES and PRIVATE_DEVELOPMENT_REFERENCES.search(data):
            fail(errors, f"non-public development account/repository reference: {rel}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(data):
                fail(errors, f"possible secret/private key pattern in: {rel}")
                break


def normalize_rel(base: Path, href: str) -> Path:
    href = unquote(href.split("#", 1)[0].split("?", 1)[0])
    return (base / href).resolve()


def audit_markdown_links(errors: list[str], files: list[Path]) -> None:
    root_resolved = ROOT.resolve()
    for path in files:
        if path.suffix.lower() != ".md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            fail(errors, f"markdown is not UTF-8: {path.relative_to(ROOT)}")
            continue

        for match in MARKDOWN_LINK.finditer(text):
            href = match.group(1).strip().strip("<>")
            if not href or href.startswith("#"):
                continue
            if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", href):
                continue

            target = normalize_rel(path.parent, href)
            try:
                target.relative_to(root_resolved)
            except ValueError:
                fail(
                    errors,
                    f"relative link escapes repository: {path.relative_to(ROOT)} -> {href}",
                )
                continue

            if not target.exists():
                fail(
                    errors,
                    f"broken relative link: {path.relative_to(ROOT)} -> {href}",
                )


def main() -> int:
    errors: list[str] = []
    files = tracked_files()

    audit_required(errors)
    audit_artifact_hashes(errors)
    audit_tree(errors, files)
    audit_markdown_links(errors, files)

    if errors:
        print("PUBLICATION_AUDIT=FAIL")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"PUBLICATION_AUDIT=PASS files={len(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
