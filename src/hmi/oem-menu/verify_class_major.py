#!/usr/bin/env python3
"""Fail unless every class in a target JAR has the expected class-file major."""

import argparse
import struct
import sys
import zipfile


def verify(path: str, expected_major: int) -> int:
    checked = 0
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith(".class"):
                continue
            data = archive.read(name)
            if len(data) < 8 or data[:4] != b"\xca\xfe\xba\xbe":
                raise ValueError(f"invalid class file: {name}")
            major = struct.unpack_from(">H", data, 6)[0]
            if major != expected_major:
                raise ValueError(f"{name}: class major {major}, expected {expected_major}")
            checked += 1
    if checked == 0:
        raise ValueError("JAR contains no class files")
    return checked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("jar")
    parser.add_argument("--major", type=int, default=46)
    args = parser.parse_args()
    try:
        count = verify(args.jar, args.major)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"CLASS_MAJOR_CHECK_FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"CLASS_MAJOR_CHECK_PASS major={args.major} classes={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
