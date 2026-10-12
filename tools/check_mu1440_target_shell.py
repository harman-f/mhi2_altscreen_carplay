#!/usr/bin/env python3
"""HOST-ONLY preflight for separately delivered MU1440/QNX shell scripts.

Checks established absent or forbidden UNBUNDLED utilities. This is a necessary
static gate, never a substitute for exact-board command/option inventory and
actual hardware validation. See docs/testing/MU1440_QNX_SHELL_COMPATIBILITY.md.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
import tempfile

# The scan is intentionally conservative for small, direct on-unit .ksh/.sh
# diagnostic packages. Shell scripts that construct commands dynamically MUST
# also be reviewed manually. This is not a general POSIX shell parser.
BLOCKED = re.compile(
    r"(?<![A-Za-z0-9_./-])(?:printf|sed|tr|sha256sum|tee)(?=\s|$|[;&|])"
)
GREP_BRE_ALTERNATION = re.compile(r"\\\|")


def scan(path: Path) -> list[str]:
    problems: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if BLOCKED.search(line):
            problems.append(f"{path}:{number}: forbidden/unbundled target command")
        if GREP_BRE_ALTERNATION.search(line):
            problems.append(f"{path}:{number}: non-portable grep BRE alternation")
    return problems


def self_test() -> None:
    with tempfile.TemporaryDirectory() as temp:
        script = Path(temp) / "regression.ksh"
        script.write_text("#!/bin/ksh\nprintf '# BEGIN %s\\n' foo\n", encoding="utf-8")
        assert scan(script), "R17.1 regression: external printf was not rejected"
        script.write_text("#!/bin/ksh\necho '# BEGIN foo'\n", encoding="utf-8")
        assert not scan(script), "simple echo was unexpectedly rejected"
        script.write_text("#!/bin/ksh\necho yes | tee log.txt\n", encoding="utf-8")
        assert scan(script), "unbundled tee was not rejected"
    print("QNX_SHELL_GATE_SELF_TEST=PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check", action="store_true", help="check every listed target script")
    parser.add_argument("scripts", nargs="*", type=Path)
    args = parser.parse_args()
    if not (args.self_test or args.check):
        parser.error("use --self-test and/or --check")
    if args.self_test:
        self_test()
    if args.check:
        if not args.scripts:
            parser.error("--check requires explicit paths to all delivered on-unit scripts")
        problems: list[str] = []
        for script in args.scripts:
            if not script.is_file() or script.suffix not in (".sh", ".ksh"):
                problems.append(f"invalid/missing target shell script: {script}")
                continue
            problems.extend(scan(script))
        for problem in problems:
            print("ERROR:", problem, file=sys.stderr)
        if problems:
            return 2
        print(f"QNX_SHELL_GATE=PASS files={len(args.scripts)} host_only=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
