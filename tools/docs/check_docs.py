#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check internal Markdown links, anchors, and live documentation/source contracts.

The mandatory CI gate covers reader-facing current documentation. --scope all
also inventories dated historical/technical Markdown without silently changing
original evidence. --report-only provides a non-blocking backlog for archival links.
No network requests or third-party Python dependencies are used.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
ACTIVE = (
    "README.md", "ROADMAP.md", "docs/README.md", "docs/INSTALLATION.md",
    "docs/packages/README.md", "docs/status/FEATURE_STATUS.md",
    "docs/status/PUBLISHED_SOURCE_COVERAGE.md",
    "docs/testing/MULTI_PROFILE_TESTING.md",
    "docs/testing/COMPATIBILITY_MATRIX.md",
    "docs/configuration/DEFAULT_CONFIGURATION_MATRIX.md",
    "docs/architecture/README.md",
    "docs/architecture/FIRMWARE_PROFILES_AND_CONFIGURATION.md",
    "docs/architecture/UNIT_STORAGE_AND_NAMING_CONTRACT.md",
    "docs/build/PACKAGE_LAYOUT.md", "modules/profiles/README.md",
    "release/CURRENT.md",
)
LINKS = (
    re.compile(r'!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+["' + "'" + r'][^"' + "'" + r']*["' + "'" + r'])?\s*\)'),
    re.compile(r'(?m)^\s{0,3}\[[^\]\n]+\]:\s*<?([^\s>]+)>?'),
    re.compile(r'(?i)\b(?:href|src)\s*=\s*["' + "'" + r']([^"' + "'" + r']+)["' + "'" + r']'),
)
HEAD = re.compile(r'^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$')
INLINE_CODE = re.compile(r'(?<!\x60)\x60[^\x60\n]*\x60(?!\x60)')

def visible_lines(text: str) -> str:
    """Mask code fences to avoid mistaking shell examples for Markdown links."""
    out = []
    fence = None
    for line in text.splitlines(keepends=True):
        m = re.match(r'^\s{0,3}(\x60{3,}|~{3,})', line)
        if m:
            chars = m.group(1)
            if fence is None:
                fence = (chars[0], len(chars))
            elif chars[0] == fence[0] and len(chars) >= fence[1]:
                fence = None
            out.append("\n")
            continue
        out.append("\n" if fence else INLINE_CODE.sub("", line))
    return "".join(out)

def slug(text: str) -> str:
    """Conservative GitHub Markdown heading slug for current docs."""
    text = re.sub(r'!?\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'<[^>]*>', '', text)
    text = text.replace("\x60", "").replace("*", "").replace("_", "")
    text = unicodedata.normalize("NFC", text.strip().lower())
    text = "".join(c for c in text if c.isalnum() or c in " -_")
    return text.replace(" ", "-")

def anchors(path: Path, cache: dict) -> set:
    if path in cache:
        return cache[path]
    result = set()
    used = {}
    for line in visible_lines(path.read_text(encoding="utf-8")).splitlines():
        m = HEAD.match(line)
        if not m:
            continue
        base = slug(m.group(1))
        count = used.get(base, 0)
        result.add(base if count == 0 else "{}-{}".format(base, count))
        used[base] = count + 1
    cache[path] = result
    return result

def should_skip(raw: str) -> bool:
    return bool(re.match(r'^(?:[a-z][a-z0-9+.-]*:|//)', raw, re.I))

def check_file(path: Path, root: Path, cache: dict) -> tuple:
    errors = []
    checked = 0
    source = visible_lines(path.read_text(encoding="utf-8"))
    for pattern in LINKS:
        for match in pattern.finditer(source):
            url = match.group(1).strip("<>")
            if should_skip(url) or not url:
                continue
            checked += 1
            line = source.count("\n", 0, match.start()) + 1
            url = unquote(url).split("?", 1)[0]
            pathname, _, fragment = url.partition("#")
            target = path if not pathname else (path.parent / pathname).resolve()
            try:
                target.relative_to(root)
            except ValueError:
                errors.append("{}:{} outside repository: {}".format(path.relative_to(root), line, url))
                continue
            if not target.exists():
                errors.append("{}:{} missing target: {}".format(path.relative_to(root), line, url))
                continue
            if fragment and target.suffix.lower() in (".md", ".markdown"):
                if slug(fragment) not in anchors(target, cache):
                    errors.append("{}:{} missing anchor in {}: #{}".format(
                        path.relative_to(root), line, target.relative_to(root), fragment))
    return checked, errors

def tracked_markdown(root: Path) -> list:
    result = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                            capture_output=True, check=True)
    names = result.stdout.decode("utf-8").split("\0")
    return [root / name for name in names if name.endswith((".md", ".markdown"))]

def check_contracts(root: Path) -> list:
    errs = []
    overview = (root / "README.md").read_text(encoding="utf-8")
    profiles_doc = (root / "modules/profiles/README.md").read_text(encoding="utf-8")
    features = (root / "docs/status/FEATURE_STATUS.md").read_text(encoding="utf-8")
    packages = (root / "docs/packages/README.md").read_text(encoding="utf-8")
    matrix = (root / "docs/configuration/DEFAULT_CONFIGURATION_MATRIX.md").read_text(encoding="utf-8")
    for path in sorted((root / "modules/profiles").glob("*/profile.json")):
        prof = json.loads(path.read_text(encoding="utf-8"))
        pid = prof["profile_id"]
        digest = prof["selector"]["digest"]
        if pid not in profiles_doc or digest not in profiles_doc:
            errs.append("profile table missing identity/hash: " + pid)
        if pid not in features:
            errs.append("feature-status profile missing: " + pid)
        if prof["selector"]["install_enabled"] and "| yes |" not in profiles_doc:
            errs.append("profile table missing install-enabled column values")
    if "docs/status/FEATURE_STATUS.md" not in overview or "docs/packages/README.md" not in overview:
        errs.append("root README must link feature and package status")
    if "three-profile" not in packages or "MU1409" not in packages or "MU1447" not in packages:
        errs.append("package overview must describe multi-profile scope")
    if "altscreen-u2/config/mibr-platform-defaults.conf" in matrix:
        errs.append("configuration matrix still prescribes old platform default root")
    if "so it is not install-enabled" in profiles_doc:
        errs.append("profile README contains obsolete MU1409 install-disabled claim")
    return errs

def run_selftest() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp).resolve()
        a, b = root / "a.md", root / "b.md"
        b.write_text("# Example Heading\n## Example Heading\n", encoding="utf-8")
        a.write_text("[ok](b.md#example-heading) and [second](b.md#example-heading-1)\n",
                     encoding="utf-8")
        links, failures = check_file(a, root, {})
        assert links == 2 and not failures, failures
        a.write_text("[bad](missing.md)\n[bad](b.md#not-here)\n", encoding="utf-8")
        links, failures = check_file(a, root, {})
        assert links == 2 and len(failures) == 2, failures
        a.write_text("&#x60;inline&#x60;\n" + "&#x60;" * 0, encoding="utf-8")
        assert slug("MiB Runtime / Menü") == "mib-runtime--menü"
    print("DOCUMENTATION_SELF_TEST=PASS")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("active", "all"), default="active")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        run_selftest()
        return 0
    root = ROOT.resolve()
    files = ([root / path for path in ACTIVE] if args.scope == "active"
             else tracked_markdown(root))
    errors = []
    links = 0
    cache = {}
    for path in files:
        if not path.is_file():
            errors.append("active doc missing: " + str(path.relative_to(root)))
            continue
        count, broken = check_file(path, root, cache)
        links += count
        errors.extend(broken)
    if args.scope == "active":
        errors.extend(check_contracts(root))
    for error in errors:
        print("DOC_AUDIT_ERROR: " + error)
    print("DOC_AUDIT files={} links={} issues={} scope={}".format(
        len(files), links, len(errors), args.scope))
    return 0 if args.report_only or not errors else 1

if __name__ == "__main__":
    sys.exit(main())
