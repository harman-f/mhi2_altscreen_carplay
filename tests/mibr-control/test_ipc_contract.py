"""Consistency test for implementation/IPC_CONTRACT.tsv.

The contract lists every MIBR RAM file (/tmp, /dev/shmem) that components of the active product code share.
This test scans the active sources for /tmp/... and /dev/shmem/... literals that belong to MIBR (name contains
mibr, alt111, parity or carplay111) and fails when

  * a literal is not covered by the contract (exact path, or a contract prefix entry ending in '*'), or
  * a contract path no longer occurs in any scanned source.

Markers at the start of the "format" column:
  [composed]   the script builds the path from a directory variable, or it lives outside the scan: no presence check.
  [gen2-only]  the path lives in the GEN2 library / settings library (zip, not scanned): no presence check.
  [host-test]  default of a host-test environment override (MIBR_V3_HOST_*): no presence check.
  [derived]    the path is built from another literal by a suffix (C string concatenation): the check only
               requires a scanned literal that is a proper prefix of it.
PENDING_NEW lists paths that are not in the sources yet (parallel work); remove them when they landed.
C files: #ifdef ALT111_SETTINGS_TEST branches (host-test only) are skipped.
"""
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]      # repository root
IMPL = HERE
CONTRACT = HERE / "IPC_CONTRACT.tsv"
if not CONTRACT.is_file():
    raise unittest.SkipTest("Research-only IPC_CONTRACT.tsv is omitted from the public source tree")

# Paths of the contract that may be absent from the sources for now; empty this set once they landed.
PENDING_NEW = set()

# Shell globs of the supervisor's SD log mirror; they name sets of files, not one file, and are covered by the
# individual rows (*.log, *.status).
GLOB_LITERALS = {"/tmp/mibr*.log", "/tmp/mibr*.status"}

HEADER = ["path", "kind", "writer", "readers", "format", "lifetime"]
KINDS = {"state", "signal", "log", "lock", "config", "socket", "secret"}
LIFETIMES = {"boot", "connection", "session", "unknown"}
KEYWORDS = ("mibr", "alt111", "parity", "carplay111")
TEST_SYMBOL = "ALT111_SETTINGS_TEST"

LITERAL = re.compile(r"(?<![A-Za-z0-9_./])(/(?:tmp|dev/shmem)/[A-Za-z0-9_.*+-]*)")
PP = re.compile(r"^\s*#\s*(if|ifdef|ifndef|else|elif|endif)\b(.*)$")


def source_files():
    native = HERE / "control" / "native"
    files = [p for p in sorted(native.glob("*.c")) + sorted(native.glob("*.h"))
             if not p.name.endswith("_probe.c") and not p.name.endswith("_harness.c")]
    files += sorted((HERE / "control" / "scripts").glob("*.ksh"))
    files.append(HERE / "control" / "runtime" / "mibr-v3-boot_r21.ksh")
    files += sorted((HERE / "java" / "de" / "mibr" / "hmi").glob("*.java"))
    files += sorted((HERE / "java" / "mib").rglob("*.java"))
    rgi = IMPL / "carplay-rgi"
    files += sorted((rgi / "src").rglob("*.c")) + sorted((rgi / "src").rglob("*.h"))
    files.append(rgi / "kit" / "mm-ipod-rgi")
    files.append(rgi / "release" / "r2" / "parity_drive_supervisor.sh")
    return files


def active_lines(path):
    """Yield lines, dropping C lines inside ALT111_SETTINGS_TEST-only branches."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix not in (".c", ".h"):
        yield from text.splitlines()
        return
    stack = []   # one [in_test_branch, mentions_symbol] per open #if
    for line in text.splitlines():
        m = PP.match(line)
        if m:
            kind, rest = m.group(1), m.group(2)
            mentions = TEST_SYMBOL in rest
            if kind in ("if", "ifdef"):
                stack.append([mentions and "!" not in rest, mentions])
            elif kind == "ifndef":
                stack.append([False, mentions])
            elif kind in ("else", "elif") and stack and stack[-1][1]:
                stack[-1][0] = not stack[-1][0]
            elif kind == "endif" and stack:
                stack.pop()
            continue
        if any(frame[0] for frame in stack):
            continue
        yield line


def scan():
    """Return (all_literals, mibr_literals) of the active sources."""
    found = {}
    for path in source_files():
        if not path.is_file():
            continue
        for line in active_lines(path):
            for lit in LITERAL.findall(line):
                lit = lit.rstrip(".-")
                if lit in ("/tmp", "/tmp/", "/dev/shmem", "/dev/shmem/"):
                    continue
                found.setdefault(lit, set()).add(path.name)
    mibr = {l: f for l, f in found.items() if any(k in l.lower() for k in KEYWORDS)}
    return found, mibr


def load_contract():
    raw = CONTRACT.read_bytes()
    text = raw.decode("utf-8")
    lines = text.split("\n")
    assert lines and lines[-1] == "", "contract must end with a LF"
    rows = [l.split("\t") for l in lines[:-1]]
    return raw, rows


class IpcContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw, cls.rows = load_contract()
        cls.header = cls.rows[0]
        cls.entries = cls.rows[1:]
        cls.all_literals, cls.mibr_literals = scan()

    def test_file_is_lf_only_with_header(self):
        self.assertNotIn(b"\r", self.raw)
        self.assertEqual(self.header, HEADER)

    def test_rows_are_well_formed(self):
        seen = set()
        for row in self.entries:
            self.assertEqual(len(row), 6, row)
            path, kind, writer, readers, fmt, lifetime = row
            self.assertTrue(path.startswith(("/tmp/", "/dev/shmem/")), path)
            self.assertIn(kind, KINDS, path)
            self.assertIn(lifetime, LIFETIMES, path)
            for col in (writer, readers, fmt):
                self.assertTrue(col.strip(), path)
            self.assertNotIn(path, seen, "duplicate row " + path)
            seen.add(path)
            if "*" in path:
                self.assertTrue(path.endswith("*") and path.count("*") == 1, path)

    def test_scan_finds_something(self):
        # Guards against a broken scanner (wrong root, empty glob) turning both checks into no-ops.
        self.assertGreater(len(self.mibr_literals), 30)

    def test_every_source_literal_is_in_contract(self):
        exact = {r[0] for r in self.entries if not r[0].endswith("*")}
        prefixes = [r[0][:-1] for r in self.entries if r[0].endswith("*")]
        missing = {}
        for lit, files in sorted(self.mibr_literals.items()):
            if lit in GLOB_LITERALS or lit in exact or any(lit.startswith(p) for p in prefixes):
                continue
            missing[lit] = sorted(files)
        self.assertEqual(missing, {}, "RAM paths in the sources but not in IPC_CONTRACT.tsv")

    def test_every_contract_path_still_occurs(self):
        literals = set(self.all_literals)
        gone = []
        for path, _kind, _w, _r, fmt, _lt in self.entries:
            if path in PENDING_NEW and path not in literals:
                continue
            if fmt.startswith(("[gen2-only]", "[host-test]", "[composed]")):
                continue
            if fmt.startswith("[derived]"):
                if not any(path.startswith(l) and path != l for l in literals):
                    gone.append(path)
                continue
            if path.endswith("*"):
                if not any(l.startswith(path[:-1]) for l in literals):
                    gone.append(path)
            elif path not in literals:
                gone.append(path)
        self.assertEqual(gone, [], "contract paths that occur in no scanned source (mark [gen2-only] or remove)")

    def test_pending_paths_are_in_contract(self):
        paths = {r[0] for r in self.entries}
        self.assertFalse(PENDING_NEW - paths, "PENDING_NEW entry without contract row")


if __name__ == "__main__":
    unittest.main()
