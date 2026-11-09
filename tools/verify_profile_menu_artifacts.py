#!/usr/bin/env python3
"""Check the owner-approved, vehicle-profile menu JAR reference artifacts."""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "seat-mu1409-p4708": "4877e37eabea093f765cd81775728fcad088c981ce541ec61350f5d9cdcdeb6a",
    "seat-mu1447-p4709": "4f7786d3aa3f6c70f3b2b93858569081634ed7aeb3e3e9c0c50ab60ed8a8e177",
    "skoda-mu1440-p4526": "5f63fcddfa267bc7dd134b3c548a9a0e300d57a625aac3fbf472164706884a39",
}


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
