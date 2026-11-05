#!/usr/bin/env python3
"""Lint Java sources for constructs the J9 / Java 1.2 source level cannot compile.

Comments, string literals and char literals are blanked first, then regexes flag
generics, enums, annotations, varargs, for-each, assert, static imports,
String.format, StringBuilder, java.util.concurrent and boxed literal assignment.
This is a heuristic gate for hosts without the J9 compiler, not a compiler.
Usage: check_java12_syntax.py [path ...]   (default: shared core + profile adapters)
"""
import re
import sys
from pathlib import Path

RULES = [
    ("generics", re.compile(r"\b[A-Z]\w*\s*<\s*[A-Z?][\w.]*(?:\s*,\s*[A-Z?][\w.]*)*\s*>|\bnew\s+\w+\s*<>")),
    ("enum", re.compile(r"\benum\s+\w+|\benum\s*\{")),
    ("annotation", re.compile(r"(?<![\w$])@\s*[A-Za-z_]")),
    ("varargs", re.compile(r"\.\.\.")),
    ("for-each", re.compile(r"\bfor\s*\(\s*(?:final\s+)?[\w.]+(?:\s*\[\s*\])*\s+\w+\s*:")),
    ("assert", re.compile(r"(?:^|[;{}])\s*assert\b")),
    ("static-import", re.compile(r"^\s*import\s+static\b", re.M)),
    ("String.format", re.compile(r"\bString\s*\.\s*format\s*\(")),
    ("StringBuilder", re.compile(r"\bStringBuilder\b")),
    ("java.util.concurrent", re.compile(r"\bjava\s*\.\s*util\s*\.\s*concurrent\b")),
    ("autoboxing", re.compile(r"\b(?:Integer|Long|Short|Byte|Boolean|Character|Float|Double)\s+\w+\s*=\s*(?:[-+]?\d|true\b|false\b|'|\w+\.length\b)")),
]


def blank_comments_and_literals(text):
    """Replace comment and literal contents by spaces, keeping line structure."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        two = text[i:i + 2]
        if two == "//":
            while i < n and text[i] != "\n":
                out.append(" "); i += 1
        elif two == "/*":
            while i < n and text[i:i + 2] != "*/":
                out.append("\n" if text[i] == "\n" else " "); i += 1
            out.append("  "); i += 2
        elif c in "\"'":
            quote = c
            out.append(quote); i += 1
            while i < n and text[i] != quote and text[i] != "\n":
                if text[i] == "\\":
                    out.append(" "); i += 1
                out.append(" "); i += 1
            out.append(quote); i += 1
        else:
            out.append(c); i += 1
    return "".join(out)


def check_text(text):
    """Return a list of (line, rule) findings."""
    clean = blank_comments_and_literals(text)
    findings = []
    for name, pattern in RULES:
        for match in pattern.finditer(clean):
            start = match.start()
            if name == "assert":
                start = match.end() - len("assert")
            findings.append((clean.count("\n", 0, start) + 1, name))
    return sorted(findings)


def default_roots():
    module = Path(__file__).resolve().parent
    roots = [module / "java"]
    roots += sorted((module.parents[1] / "profiles").glob("*/hmi/java"))
    return roots


def main(argv):
    targets = [Path(a) for a in argv] or default_roots()
    files = []
    for target in targets:
        files += sorted(target.rglob("*.java")) if target.is_dir() else [target]
    failed = 0
    for path in files:
        for line, rule in check_text(path.read_text(encoding="utf-8")):
            print("%s:%d: JAVA12_FORBIDDEN=%s" % (path, line, rule))
            failed += 1
    if failed:
        print("JAVA12_SYNTAX_CHECK=FAIL findings=%d" % failed)
        return 1
    print("JAVA12_SYNTAX_CHECK=PASS files=%d" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
