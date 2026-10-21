#!/usr/bin/env python3
import argparse
import hashlib
import json
import pathlib
import zipfile

PATCH_CLASS = "de/vw/mib/asl/internal/mostkombi/streamsink/usecases/ChangeDataRateSequence.class"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_jar(path, title, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = (
        "Manifest-Version: 1.0\r\n"
        f"Implementation-Title: {title}\r\n"
        "Created-By: MHI2 AltScreen deterministic split\r\n"
        "\r\n"
    ).encode("utf-8")
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as z:
        zi = zipfile.ZipInfo("META-INF/MANIFEST.MF", FIXED_TIME)
        zi.external_attr = 0o644 << 16
        z.writestr(zi, manifest)
        for name, data in sorted(entries.items()):
            zi = zipfile.ZipInfo(name, FIXED_TIME)
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--expected-sha256", required=True)
    args = ap.parse_args()

    src = pathlib.Path(args.source)
    out = pathlib.Path(args.out)
    got = sha256(src)
    if got.lower() != args.expected_sha256.lower():
        raise SystemExit(f"source SHA mismatch: {got}")

    with zipfile.ZipFile(src, "r") as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise SystemExit("duplicate ZIP entries in source JAR")
        if PATCH_CLASS not in names:
            raise SystemExit(f"required class missing: {PATCH_CLASS}")

        payload = {}
        for n in names:
            if n.endswith("/") or n.upper().startswith("META-INF/"):
                continue
            payload[n] = z.read(n)

    fps_entries = {PATCH_CLASS: payload[PATCH_CLASS]}
    nav_entries = {k: v for k, v in payload.items() if k != PATCH_CLASS}

    if not nav_entries:
        raise SystemExit("NavIgnore split unexpectedly empty")
    if PATCH_CLASS in nav_entries:
        raise SystemExit("20 FPS class leaked into NavIgnore split")

    fps_jar = out / "most20fps" / "Most20FPS.jar"
    nav_jar = out / "navignore" / "NavIgnore.jar"
    write_jar(fps_jar, "MHI2 MOST 20 FPS", fps_entries)
    write_jar(nav_jar, "MHI2 NavIgnore (without MOST 20 FPS)", nav_entries)

    (out / "source-entries.txt").write_text("\n".join(sorted(payload)) + "\n")
    (out / "most20fps" / "classes.txt").write_text(PATCH_CLASS + "\n")
    (out / "navignore" / "classes.txt").write_text("\n".join(sorted(nav_entries)) + "\n")

    manifest = {
        "schema": 1,
        "source_commit": args.source_commit,
        "source_sha256": got,
        "source_payload_entries": len(payload),
        "most20fps": {
            "jar": "most20fps/Most20FPS.jar",
            "sha256": sha256(fps_jar),
            "owned_classes": [PATCH_CLASS],
        },
        "navignore": {
            "jar": "navignore/NavIgnore.jar",
            "sha256": sha256(nav_jar),
            "excluded_classes": [PATCH_CLASS],
            "payload_entries": len(nav_entries),
        },
    }
    (out / "split-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

if __name__ == "__main__":
    main()
