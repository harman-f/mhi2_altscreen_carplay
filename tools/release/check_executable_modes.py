#!/usr/bin/env python3
"""Fail when a file pinned in executable_modes.lock loses git mode 100755.

The lock lists every tracked file that must stay executable. Adding a new
executable file means adding it to the lock (run with --write-lock).
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOCK = os.path.join(HERE, "executable_modes.lock")


def tracked_modes(root):
    out = subprocess.run(["git", "-C", root, "ls-files", "-s", "-z"],
                         check=True, capture_output=True).stdout.decode()
    modes = {}
    for entry in out.split("\0"):
        if not entry:
            continue
        meta, path = entry.split("\t", 1)
        modes[path] = meta.split()[0]
    return modes


def read_lock(path):
    with open(path, encoding="utf-8") as fh:
        return [l.strip() for l in fh if l.strip() and not l.startswith("#")]


def check(modes, pinned):
    errors = []
    for path in pinned:
        mode = modes.get(path)
        if mode is None:
            errors.append("pinned executable missing from index: " + path)
        elif mode != "100755":
            errors.append("lost executable bit (%s): %s" % (mode, path))
    unpinned = sorted(p for p, m in modes.items() if m == "100755" and p not in set(pinned))
    for path in unpinned:
        errors.append("executable not in lock (add it): " + path)
    return errors


def self_test():
    pinned = ["a.sh", "b.sh"]
    assert check({"a.sh": "100755", "b.sh": "100755", "c.sh": "100644"}, pinned) == []
    assert any("lost executable bit" in e for e in check({"a.sh": "100644", "b.sh": "100755"}, pinned))
    assert any("missing" in e for e in check({"a.sh": "100755"}, pinned))
    assert any("not in lock" in e for e in check({"a.sh": "100755", "b.sh": "100755", "d.sh": "100755"}, pinned))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--write-lock", action="store_true")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(HERE)))
    args = ap.parse_args()
    if args.self_test:
        self_test()
    modes = tracked_modes(args.root)
    if args.write_lock:
        with open(LOCK, "w", encoding="utf-8") as fh:
            fh.write("".join(p + "\n" for p in sorted(p for p, m in modes.items() if m == "100755")))
    errors = check(modes, read_lock(LOCK))
    for e in errors:
        print("ERROR " + e)
    print("EXECUTABLE_MODES=%s pinned=%d" % ("FAIL" if errors else "PASS", len(read_lock(LOCK))))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
