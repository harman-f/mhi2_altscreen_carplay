#!/usr/bin/env python3
"""Host-side QNX shell gate for canonical runtime and exact staged payload.

Uses the vehicle-evidenced MU1440 command contract. This is a necessary static
check, not an assertion of hardware execution or every dynamically built command.
No code in this tool is installed on the unit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from check_mu1440_target_shell import scan, self_test as shell_self_test  # noqa: E402

SCRIPT_SUFFIX = {".sh", ".ksh"}
SHARED_TARGET_DIRS = ("deployment/mu1440", "runtime/diagnostics", "runtime/deployment")

# Audited exceptions for two non-executing strings only. No new commands are
# permitted: changes to these exact lines or paths lose the exception.
NON_EXECUTING_LINES = {
    "auto-direct/common.sh": '    runtime_emit "ERROR bundled tee helper missing/not executable: $TEE"',
    "diagnostics/gen2_prereq.sh": "  command -v sha256sum 2>/dev/null && return 0",
}


def non_executing_exception(path: Path, source_line: str) -> bool:
    return any(path.as_posix().endswith("/" + suffix) and source_line == exact
               for suffix, exact in NON_EXECUTING_LINES.items())


def scripts_below(root: Path, directories: list[Path]) -> list[Path]:
    found: set[Path] = set()
    for directory in directories:
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("missing or symlinked target script directory: " + str(directory))
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise ValueError("symlinked target script path: " + str(path))
            if path.is_file() and path.suffix in SCRIPT_SUFFIX:
                found.add(path)
    if not found:
        raise ValueError("no target scripts found")
    return sorted(found)


def canonical_scripts() -> list[Path]:
    index = json.loads((ROOT / "modules/module-index.json").read_text(encoding="utf-8"))
    owned = [ROOT / p for block in index["modules"].values() for p in block.get("runtime", [])]
    shared = [ROOT / p for p in SHARED_TARGET_DIRS]
    return scripts_below(ROOT, owned + shared)


def package_scripts(path: Path) -> list[Path]:
    if not path.is_dir() or path.is_symlink():
        raise ValueError("missing or symlinked assembled package root: " + str(path))
    if not (path / "PAYLOAD.sha256").is_file():
        raise ValueError("assembled package lacks payload manifest: " + str(path))
    return scripts_below(path, [path])


def audit(paths: list[Path]) -> None:
    problems: list[str] = []
    for script in paths:
        if script.is_symlink() or not script.is_file():
            problems.append("missing/symlinked QNX script: " + str(script))
            continue
        lines = script.read_text(encoding="utf-8").splitlines()
        for finding in scan(script):
            # The base scanner also catches command-looking words in quoted
            # diagnostic text and an optional command -v capability probe.
            number = int(finding.rsplit(":", 2)[1])
            if not non_executing_exception(script, lines[number - 1]):
                problems.append(finding)
        # Bash syntax is only a HOST smoke check; on-unit shell command inventory
        # and MMX/RCC distinction still require exact hardware evidence.
        if script.suffix == ".sh":
            result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
            if result.returncode:
                problems.append(f"{script}: host syntax check failed: {result.stderr.strip()}")
    if problems:
        for finding in problems:
            print("QNX_SCRIPT_ERROR:", finding, file=sys.stderr)
        raise ValueError(f"{len(problems)} QNX target-shell problems")
    print(f"QNX_TARGET_SCRIPTS=PASS count={len(paths)} host_static_only=1")


def self_test() -> None:
    shell_self_test()
    with tempfile.TemporaryDirectory(prefix="qnx-release-scan-") as temp:
        root = Path(temp)
        stage = root / "stage"
        stage.mkdir()
        (stage / "PAYLOAD.sha256").write_text("placeholder\n")
        (stage / "install.sh").write_text("#!/bin/ksh\necho good\n")
        audit(package_scripts(stage))
        (stage / "install.sh").write_text("#!/bin/ksh\nprintf bad\n")
        try:
            audit(package_scripts(stage))
        except ValueError:
            pass
        else:
            raise AssertionError("forbidden command incorrectly passed")
        (stage / "install.sh").unlink()
        (stage / "runtime/auto-direct").mkdir(parents=True)
        (stage / "runtime/auto-direct/common.sh").write_text(
            '#!/bin/ksh\n' + NON_EXECUTING_LINES["auto-direct/common.sh"] + "\n"
        )
        (stage / "runtime/diagnostics").mkdir(parents=True)
        (stage / "runtime/diagnostics/gen2_prereq.sh").write_text(
            '#!/bin/ksh\n' + NON_EXECUTING_LINES["diagnostics/gen2_prereq.sh"] + "\n"
        )
        audit(package_scripts(stage))
        (stage / "runtime/auto-direct/common.sh").write_text('#!/bin/ksh\ntee output.log\n')
        try:
            audit(package_scripts(stage))
        except ValueError:
            pass
        else:
            raise AssertionError("real unbundled tee unexpectedly passed")
        for path in (stage / "runtime/auto-direct/common.sh",
                     stage / "runtime/diagnostics/gen2_prereq.sh"):
            path.unlink()
        try:
            package_scripts(stage)
        except ValueError:
            pass
        else:
            raise AssertionError("empty package script inventory passed")
    print("QNX_RELEASE_SCRIPT_SELF_TEST=PASS")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--canonical", action="store_true")
    ap.add_argument("--package-root", type=Path)
    args = ap.parse_args()
    if not (args.self_test or args.canonical or args.package_root):
        ap.error("use --self-test, --canonical and/or --package-root")
    try:
        if args.self_test:
            self_test()
        if args.canonical:
            audit(canonical_scripts())
        if args.package_root:
            audit(package_scripts(args.package_root))
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
