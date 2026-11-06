#!/usr/bin/env python3
"""Verify only two independently authored Java 1.2 classes are present."""
import hashlib
import struct
import sys
import zipfile
from pathlib import Path

EXPECTED = {
    "de/mibr/extender/MibrStartupHook.class",
    "de/mibr/extender/MibrExtenderCore.class",
}
def verify(path):
    p = Path(path)
    with zipfile.ZipFile(p) as z:
        entries = {n for n in z.namelist() if n.endswith(".class")}
        if entries != EXPECTED or z.testzip() is not None:
            raise SystemExit("P1_ARCHIVE_REJECT unexpected class or CRC")
        for name in sorted(entries):
            b = z.read(name)
            if len(b) < 8 or b[:4] != b"\xca\xfe\xba\xbe" or struct.unpack(">H", b[6:8])[0] != 46:
                raise SystemExit("P1_MAJOR46_REJECT " + name)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    print("P1_J9_ARCHIVE_PASS classes=2 major=46 sha256=" + sha)
    return sha

if __name__ == "__main__":
    verify(sys.argv[1])
