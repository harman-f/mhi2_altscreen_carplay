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
    "docs/build/MU1440_R50_SOURCE.md",
    "docs/build/MU1440_R57_SOURCE.md",
    "docs/build/INSTALLED_GEN2_SOURCE.md",
    "settings/registry.json",
    "src/native/parity-session/parity_session.c",
    "src/native/direct-ts-parity/direct_ts_parity.c",
    "src/native/mibr-control/mibr_v3_service.c",
    "src/hmi/oem-menu/java/de/mibr/hmi/MibrControlClient.java",
    "runtime/parity/parity_drive_supervisor.sh",
    "tools/build_mu1440_source.sh",
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

# Reviewed first-party flat-color artwork. No general OEM skin/image exception.
OWNED_ARTWORK = {
    "src/hmi/oem-menu/assets/scroll/mibr_scroll_thumb.png": "3f883283a5af35a789ce76c3f414a3b030250bbf5a3d8b76421120d80e39cbee",
    "src/hmi/oem-menu/assets/scroll/mibr_scroll_thumb_v2.png": "6d34382b9744264121871e8b092f1ab025619ee028b1f5ca30ffc030fe62f8f4",
    "src/hmi/oem-menu/assets/scroll/mibr_scroll_track.png": "f33c96eada17e1573a81032c5301dc9e0c9e5320ad37be3bc2dd97386f6b27d4",
    "src/hmi/oem-menu/assets/scroll/mibr_scroll_track_v2.png": "8b2f0d77dd89432e3faa043d0b0e1566d939366d42a6d3b2f8964645cd13f93b",
}


# Contributor-authorized vehicle photos; exact bytes only, no general media exception.
REVIEWED_SEAT_PHOTOS = {'docs/media/seat-mu1409-2026-10-25/hardware-and-controls.jpg': 'ffd9f405d1c260212864e1ce03ffa6b0ed8826723d9c0d031023cf76e1762143', 'docs/media/seat-mu1409-2026-10-25/round-dials-cards-obscured.jpg': '4296fd7bf1cba60c521ee952fa38fcec270f23e6edbecdadd352b9d5b8d751c5', 'docs/media/seat-mu1409-2026-10-25/oem-single-dial-layout.jpg': '15e4a8b82d5b63cf5ac94554ab3bba8b7e03f79ac540dafae56bd0a96d0a3a61', 'docs/media/seat-mu1409-2026-10-25/edge-gauges-cards-clipped.jpg': '41bec956593792e41d2831687a6aa9af8c188ad9bd1227d1b4ebfcdf213653e6', 'docs/media/seat-mu1409-2026-10-25/wide-cards-visible.jpg': 'a13b5655b8e8480d9a339285e6583854d9c25acac1ca145d4d3088f3ea470d2f', 'docs/media/seat-mu1409-2026-10-25/center-map-only.jpg': 'caa872da937b545929412669aa6acbe2a30d1bb837602aaf824b390019bd913a'}

def reviewed_seat_photo(rel: Path, data: bytes) -> bool:
    expected = REVIEWED_SEAT_PHOTOS.get(rel.as_posix())
    return expected is not None and hashlib.sha256(data).hexdigest() == expected


def reviewed_artwork(rel: Path, data: bytes) -> bool:
    expected = OWNED_ARTWORK.get(rel.as_posix())
    return bool(expected and hashlib.sha256(data).hexdigest() == expected)

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
    b"(?:Cane" + b"TLOTW|M[.]I[.]B[.][_]Research)", re.IGNORECASE
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
        data = path.read_bytes()
        is_curated_public_media = (
            rel.is_relative_to(PUBLIC_MEDIA_ROOT)
            and suffix in PUBLIC_MEDIA_SUFFIXES
        )

        if any(low.endswith(blocked) for blocked in FORBIDDEN_SUFFIXES):
            if not is_curated_public_media and not reviewed_artwork(rel, data) and not reviewed_seat_photo(rel, data):
                fail(errors, f"forbidden publication artifact type: {rel}")

        if "dyld_shared_cache" in low:
            fail(errors, f"dyld cache material must not be committed: {rel}")

        size = path.stat().st_size
        if size > MAX_FILE_SIZE:
            fail(errors, f"unexpected large file ({size} bytes): {rel}")

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
    # Regression fixtures are assembled without embedding the disallowed cleartext
    # identity in this checker source, which is itself scanned as a public text file.
    assert PRIVATE_DEVELOPMENT_REFERENCES.search(b"Cane" + b"TLOTW")
    assert PRIVATE_DEVELOPMENT_REFERENCES.search(b"M.I.B." + b"_Research")
    errors: list[str] = []
    for rel in OWNED_ARTWORK:
        asset = ROOT / rel
        if not asset.is_file():
            fail(errors, f"missing reviewed owned artwork: {rel}")
            continue
        data = asset.read_bytes()
        if not reviewed_artwork(Path(rel), data):
            fail(errors, f"reviewed owned artwork changed: {rel}")
        assert not reviewed_artwork(Path(rel), data + b"tampered")
        assert not reviewed_artwork(Path("unreviewed.png"), data)
    for rel in REVIEWED_SEAT_PHOTOS:
        asset = ROOT / rel
        if not asset.is_file() or not reviewed_seat_photo(Path(rel), asset.read_bytes()):
            fail(errors, f"missing or changed reviewed SEAT vehicle photo: {rel}")
        else:
            assert not reviewed_seat_photo(Path(rel), asset.read_bytes() + b"tampered")
            assert not reviewed_seat_photo(Path("unreviewed.jpg"), asset.read_bytes())
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
