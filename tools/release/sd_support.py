#!/usr/bin/env python3
"""Host-only inventory gate for project-owned supplemental SD support assets.

Not a full SD-card snapshot, QNX execution proof, or multi-profile release gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path("sd/manifest.json")


def safe_path(value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("invalid manifest path: " + repr(value))
    posix = PurePosixPath(value)
    if posix.is_absolute() or any(part in (".", "..") for part in value.split("/")) or posix.as_posix() != value:
        raise ValueError("unsafe manifest path: " + value)
    return Path(*posix.parts)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root: Path, stage: Path | None = None) -> int:
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("kind") != "supplemental_sd_assets_not_full_card":
        raise ValueError("invalid SD supplemental manifest identity")
    if manifest.get("package_scope") != "legacy-mu1440-developer-stage":
        raise ValueError("unexpected package scope")
    records = manifest.get("entries")
    if not isinstance(records, list) or not records:
        raise ValueError("missing SD supplemental entries")
    sources: set[str] = set()
    targets: set[str] = set()
    binary_count = 0
    script_count = 0
    for entry in records:
        if not isinstance(entry, dict) or entry.get("kind") not in ("binary", "script"):
            raise ValueError("unsupported SD supplemental entry")
        source_name = entry.get("source")
        target_name = entry.get("target")
        source_path = safe_path(source_name)
        target_path = safe_path(target_name)
        if source_name in sources or target_name in targets:
            raise ValueError("duplicate SD asset source or destination")
        sources.add(source_name)
        targets.add(target_name)
        if entry["kind"] == "script":
            script_count += 1
            if source_path.suffix not in (".sh", ".ksh") or target_path.suffix not in (".sh", ".ksh"):
                raise ValueError("script entry does not refer to a shell script")
            if set(entry) != {"kind", "source", "target"}:
                raise ValueError("unexpected script entry fields")
        else:
            binary_count += 1
            expected = entry.get("sha256")
            if set(entry) != {"kind", "source", "target", "sha256"} or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise ValueError("binary missing pinned SHA-256")
        source = root / source_path
        if not source.is_file() or source.is_symlink():
            raise ValueError("missing or linked source asset: " + source_name)
        source_hash = digest(source)
        if entry["kind"] == "binary" and source_hash != entry["sha256"]:
            raise ValueError("source binary hash mismatch: " + source_name)
        if stage is not None:
            target = stage / target_path
            if not target.is_file() or target.is_symlink():
                raise ValueError("missing or linked staged SD asset: " + target_name)
            if digest(target) != source_hash:
                raise ValueError("staged SD asset differs from source: " + target_name)
            if not os.access(target, os.X_OK):
                raise ValueError("staged SD executable lacks execute permission: " + target_name)
    print(f"SD_SUPPLEMENTAL_GATE=PASS binaries={binary_count} scripts={script_count} stage_checked={int(stage is not None)} publication=NOT_AUTHORIZED")
    return len(records)


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="sd-support-gate-") as td:
        root = Path(td) / "repo"
        stage = Path(td) / "stage"
        (root / "sd").mkdir(parents=True)
        (root / "assets").mkdir(parents=True)
        (stage / "payload").mkdir(parents=True)
        source = root / "assets/helper"
        source.write_bytes(b"target-binary-fixture")
        target = stage / "payload/helper"
        target.write_bytes(source.read_bytes())
        target.chmod(0o755)
        data = {"schema_version": 1, "kind": "supplemental_sd_assets_not_full_card",
                "package_scope": "legacy-mu1440-developer-stage",
                "entries": [{"kind": "binary", "source": "assets/helper",
                             "target": "payload/helper", "sha256": digest(source)}]}
        manifest_path = root / MANIFEST
        manifest_path.write_text(json.dumps(data), encoding="utf-8")
        assert verify(root, stage) == 1
        target.write_bytes(b"tampered")
        try:
            verify(root, stage)
        except ValueError:
            pass
        else:
            raise AssertionError("tampered SD stage incorrectly accepted")
        target.write_bytes(source.read_bytes())
        data["entries"][0]["target"] = "../escape"
        manifest_path.write_text(json.dumps(data), encoding="utf-8")
        try:
            verify(root, stage)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe SD destination incorrectly accepted")
    print("SD_SUPPLEMENTAL_SELF_TEST=PASS")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--source-check", action="store_true")
    parser.add_argument("--stage-root", type=Path)
    args = parser.parse_args()
    if not (args.self_test or args.source_check or args.stage_root):
        parser.error("use --self-test, --source-check and/or --stage-root")
    try:
        if args.self_test:
            self_test()
        if args.source_check or args.stage_root:
            verify(ROOT, args.stage_root)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"SD_SUPPLEMENTAL_GATE=FAIL {exc}\n")


if __name__ == "__main__":
    main()
