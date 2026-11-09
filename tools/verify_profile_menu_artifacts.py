#!/usr/bin/env python3
"""Check the owner-approved, vehicle-profile menu JAR reference artifacts."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "modules/profiles/MENU_SOURCE_LOCK.json").read_text(encoding="utf-8"))
if LOCK.get("schema") != 1:
    raise SystemExit("MENU_REFERENCE_LOCK_SCHEMA_INVALID")
EXPECTED = LOCK["menu_jars"]


def main():
    for profile, expected in EXPECTED.items():
        path = ROOT / "modules/profiles" / profile / "hmi/prebuilt/MIBR-CarPlay.jar"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"MENU_REFERENCE_HASH_MISMATCH {profile}: {actual}")
        with zipfile.ZipFile(path) as jar:
            if jar.testzip() is not None:
                raise SystemExit(f"MENU_REFERENCE_CORRUPT {profile}")
            classes = [n for n in jar.namelist() if n.endswith(".class")]
            if not classes or any(jar.read(n)[:4] != b"\xca\xfe\xba\xbe" or
                                  int.from_bytes(jar.read(n)[6:8], "big") != 46
                                  for n in classes):
                raise SystemExit(f"MENU_REFERENCE_CLASS_VERSION_MISMATCH {profile}")
        print(f"MENU_REFERENCE=PASS profile={profile} classes={len(classes)} sha256={actual}")


if __name__ == "__main__":
    main()
