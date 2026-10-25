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
import shlex
import sys
import tempfile

# The scan is intentionally conservative for small, direct on-unit .ksh/.sh
# diagnostic packages. Shell scripts that construct commands dynamically MUST
# also be reviewed manually. This is not a general POSIX shell parser.
BLOCKED_COMMANDS = {"printf", "sed", "tr", "sha256sum", "tee"}
GREP_BRE_ALTERNATION = re.compile(r"\\\|")
COMMAND_SEPARATORS = {";", ";;", ";&", ";;&", "&&", "||", "|", "&", "(", ")", "\n"}
CONTROL_WORDS = {"then", "do", "else", "elif", "if", "while", "until"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _is_allowed_bundled_helper(token: str, command_name: str) -> bool:
    bundled_paths = {
        "tee": {
            "$BASE/bin/tee", "${BASE}/bin/tee", "$PAYLOAD/tee", "${PAYLOAD}/tee",
        },
        "sha256sum": {
            "$BASE/bin/sha256sum", "${BASE}/bin/sha256sum",
            "$PAYLOAD/sha256sum", "${PAYLOAD}/sha256sum",
            "/mnt/app/root/altscreen-u2/bin/sha256sum",
        },
    }
    return token in bundled_paths.get(command_name, set())


def _find_dollar_substitution_end(text: str, start: int) -> int | None:
    depth = 1
    quote: str | None = None
    double_sub_depth = 0
    i = start + 2
    while i < len(text):
        char = text[i]
        if char == "\\":
            i += 2
            continue
        if quote == "'":
            if char == "'":
                quote = None
            i += 1
            continue
        if quote == '"':
            if char == '"':
                quote = None
            elif text.startswith("$(", i):
                depth += 1
                double_sub_depth += 1
                i += 2
                continue
            elif char == ")" and double_sub_depth:
                depth -= 1
                double_sub_depth -= 1
                if depth == 0:
                    return i
            i += 1
            continue
        if char == "'":
            quote = "'"
        elif char == '"':
            quote = '"'
        elif char == "`":
            end = _find_backtick_end(text, i)
            if end is None:
                return None
            i = end + 1
            continue
        elif char == "#" and (i == 0 or text[i - 1].isspace() or text[i - 1] in ";|&"):
            newline = text.find("\n", i)
            i = len(text) if newline < 0 else newline + 1
            continue
        elif text.startswith("$(", i):
            depth += 1
            i += 2
            continue
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _find_backtick_end(text: str, start: int) -> int | None:
    i = start + 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "`":
            return i
        i += 1
    return None


def _active_substitutions(text: str) -> list[tuple[int, int, str]]:
    """Return active $(...) and backtick bodies, excluding single quotes/comments."""
    found: list[tuple[int, int, str]] = []
    quote: str | None = None
    i = 0
    while i < len(text):
        char = text[i]
        if char == "\\":
            i += 2
            continue
        if quote == "'":
            if char == "'":
                quote = None
            i += 1
            continue
        if quote == '"':
            if char == '"':
                quote = None
                i += 1
                continue
            if text.startswith("$(", i):
                end = _find_dollar_substitution_end(text, i)
                if end is None:
                    return found
                found.append((i, end, text[i + 2:end]))
                i = end + 1
                continue
            if char == "`":
                end = _find_backtick_end(text, i)
                if end is None:
                    return found
                found.append((i, end, text[i + 1:end]))
                i = end + 1
                continue
            i += 1
            continue
        if char == "#" and (i == 0 or text[i - 1].isspace() or text[i - 1] in ";|&"):
            newline = text.find("\n", i)
            i = len(text) if newline < 0 else newline + 1
            continue
        if char == "'":
            quote = "'"
            i += 1
            continue
        if char == '"':
            quote = '"'
            i += 1
            continue
        if text.startswith("$(", i):
            end = _find_dollar_substitution_end(text, i)
            if end is None:
                return found
            found.append((i, end, text[i + 2:end]))
            i = end + 1
            continue
        if char == "`":
            end = _find_backtick_end(text, i)
            if end is None:
                return found
            found.append((i, end, text[i + 1:end]))
            i = end + 1
            continue
        i += 1
    return found


def _scan_command_tokens(script_text: str) -> list[int]:
    script_text = _terminate_unquoted_newlines(script_text)
    lexer = shlex.shlex(script_text, posix=True, punctuation_chars="\n;&|()")
    lexer.whitespace_split = True
    lexer.commenters = "#"
    try:
        tokens = [(token, lexer.lineno) for token in lexer]
    except ValueError:
        # Keep malformed shell lines visible to the gate; they need a manual fix.
        return [lexer.lineno]

    command_expected = True
    wrapper: str | None = None
    wrapper_skip_argument = False
    wrapper_lookup = False
    case_states: list[str] = []
    loop_state: str | None = None
    blocked_lines: list[int] = []
    for token, line_number in tokens:
        if wrapper:
            if token in COMMAND_SEPARATORS:
                if wrapper_skip_argument:
                    blocked_lines.append(line_number)
                wrapper = None
                wrapper_skip_argument = False
                wrapper_lookup = False
                command_expected = True
                continue
            if wrapper_skip_argument:
                wrapper_skip_argument = False
                continue
            if wrapper == "command":
                if token in {"-v", "-V"}:
                    wrapper_lookup = True
                    continue
                if wrapper_lookup:
                    wrapper = None
                    wrapper_lookup = False
                    command_expected = False
                    continue
                if token in {"-p", "--"}:
                    continue
                if token.startswith("-"):
                    blocked_lines.append(line_number)
                    wrapper = None
                    command_expected = False
                    continue
                command_token = token
            elif wrapper == "env":
                if token in {"-i", "--ignore-environment", "-0"}:
                    continue
                if token in {"-u", "--unset", "-C", "--chdir"}:
                    wrapper_skip_argument = True
                    continue
                if token in {"-S", "--split-string"}:
                    # The operand is a second command line; reject unless it is parsed separately.
                    blocked_lines.append(line_number)
                    wrapper = None
                    command_expected = False
                    continue
                if token.startswith("--unset=") or token.startswith("--chdir="):
                    continue
                if token == "--":
                    continue
                if ASSIGNMENT.match(token):
                    continue
                if token.startswith("-"):
                    # Unknown env options make the wrapped executable ambiguous.
                    blocked_lines.append(line_number)
                    wrapper = None
                    command_expected = False
                    continue
                command_token = token
            else:
                if token in {"-c", "-l", "--"}:
                    continue
                if token == "-a":
                    wrapper_skip_argument = True
                    continue
                if token.startswith("-"):
                    blocked_lines.append(line_number)
                    wrapper = None
                    command_expected = False
                    continue
                command_token = token

            command_name = command_token.lstrip("(").rsplit("/", 1)[-1]
            if command_name in BLOCKED_COMMANDS and not _is_allowed_bundled_helper(command_token, command_name):
                blocked_lines.append(line_number)
            wrapper = None
            command_expected = False
            continue

        if case_states and case_states[-1] == "header":
            if token == "in":
                case_states[-1] = "pattern"
            continue
        if case_states and case_states[-1] == "pattern":
            if token == ")":
                case_states[-1] = "body"
                command_expected = True
            elif token == "esac":
                case_states.pop()
                command_expected = False
            continue
        if case_states and case_states[-1] == "body" and token in {";;", ";&", ";;&"}:
            case_states[-1] = "pattern"
            command_expected = False
            continue
        if case_states and token == "esac":
            case_states.pop()
            command_expected = False
            continue
        if loop_state:
            if token == "in":
                loop_state = "values"
            elif token == "do":
                loop_state = None
                command_expected = True
            continue
        if token in COMMAND_SEPARATORS:
            command_expected = True
            continue
        if command_expected and token in CONTROL_WORDS:
            command_expected = True
            continue
        if token in {"{", "}"}:
            command_expected = True
            continue
        if not command_expected:
            if token == "esac" and case_states:
                case_states.pop()
                command_expected = False
            continue
        if token == "case":
            case_states.append("header")
            command_expected = False
            continue
        if token in {"for", "select"}:
            loop_state = "header"
            command_expected = False
            continue
        if ASSIGNMENT.match(token):
            continue
        if token == "!":
            continue
        if token in {"command", "env", "exec", "builtin"}:
            wrapper = "command" if token == "command" else "env" if token == "env" else "exec"
            command_expected = False
            continue
        command_name = token.lstrip("(").rsplit("/", 1)[-1]
        if command_name in BLOCKED_COMMANDS:
            if not _is_allowed_bundled_helper(token, command_name):
                blocked_lines.append(line_number)
        command_expected = False

    return sorted(set(blocked_lines))


def _terminate_unquoted_newlines(script_text: str) -> str:
    """Turn shell statement newlines into separators while preserving quoted text."""
    output: list[str] = []
    quote: str | None = None
    in_comment = False
    escaped = False
    pending_operator: str | None = None
    previous_operator: str | None = None

    def terminate_line() -> None:
        if pending_operator in {"|", "||", "&&"}:
            output.append("\n")
        else:
            output.extend((";", "\n"))

    for index, char in enumerate(script_text):
        if in_comment:
            if char == "\n":
                terminate_line()
                in_comment = False
                pending_operator = None
                previous_operator = None
            else:
                output.append(" ")
            continue
        if escaped:
            output.append(char)
            escaped = False
            if char != "\n":
                pending_operator = None
                previous_operator = None
            continue
        if char == "\\" and quote != "'":
            output.append(char)
            escaped = True
            continue
        if quote == "'":
            output.append(char)
            if char == "'":
                quote = None
                pending_operator = None
                previous_operator = None
            continue
        if quote == '"':
            output.append(char)
            if char == '"':
                quote = None
                pending_operator = None
                previous_operator = None
            continue
        if char == "#" and (index == 0 or script_text[index - 1].isspace() or script_text[index - 1] in ";|&"):
            output.append(" ")
            in_comment = True
            continue
        if char in {"'", '"'}:
            quote = char
            output.append(char)
            pending_operator = None
            previous_operator = None
            continue
        if char == "\n":
            terminate_line()
            pending_operator = None
            previous_operator = None
            continue
        output.append(char)
        if char in " \t\r":
            previous_operator = None
            continue
        if char == "|":
            pending_operator = "||" if previous_operator == "|" else "|"
            previous_operator = "|"
            continue
        if char == "&":
            pending_operator = "&&" if previous_operator == "&" else None
            previous_operator = "&"
            continue
        pending_operator = None
        previous_operator = None
    return "".join(output)


def _blocked_command_lines(script_text: str) -> list[int]:
    """Check command positions, including command substitutions, not arguments/log text."""
    substitutions = _active_substitutions(script_text)
    blocked_lines: list[int] = []
    for start, end, body in substitutions:
        start_line = script_text.count("\n", 0, start) + 1
        blocked_lines.extend(start_line + line - 1 for line in _blocked_command_lines(body))

    masked_parts: list[str] = []
    cursor = 0
    for start, end, _ in substitutions:
        masked_parts.append(script_text[cursor:start])
        masked_parts.append("SUBSTITUTION")
        masked_parts.append("\n" * script_text.count("\n", start, end + 1))
        cursor = end + 1
    masked_parts.append(script_text[cursor:])
    blocked_lines.extend(_scan_command_tokens("".join(masked_parts)))
    return sorted(set(blocked_lines))


def scan(path: Path) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")
    blocked_lines = set(_blocked_command_lines(text))
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if number in blocked_lines:
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
        script.write_text('runtime_emit "ERROR bundled tee helper missing: $TEE"\n', encoding="utf-8")
        assert not scan(script), "quoted diagnostic text was mistaken for a command"
        script.write_text("command -v sha256sum >/dev/null 2>&1\n", encoding="utf-8")
        assert not scan(script), "command availability probe was mistaken for execution"
        for source, description in (
            ("echo data |\ntee log.txt\n", "multiline pipeline tee"),
            ("true &&\nprintf x\n", "multiline AND-list printf"),
            ("false ||\ntee log.txt\n", "multiline OR-list tee"),
            ("echo data | # comment\ntee log.txt\n", "commented multiline pipeline tee"),
        ):
            script.write_text(source, encoding="utf-8")
            problems = scan(script)
            assert any(":2:" in problem for problem in problems), (
                f"{description} was not rejected on the continued command line"
            )
        for source, continuation, description in (
            ("echo data |\ntee log.txt\n", "|\ntee", "pipeline"),
            ("true &&\nprintf x\n", "&&\nprintf", "AND-list"),
            ("false ||\ntee log.txt\n", "||\ntee", "OR-list"),
        ):
            normalized = _terminate_unquoted_newlines(source)
            assert continuation in normalized, f"{description} continuation was split with a semicolon"
            assert continuation.replace("\n", ";\n") not in normalized, (
                f"{description} continuation contains a statement separator"
            )
        commented = _terminate_unquoted_newlines("echo data | # comment\ntee log.txt\n")
        assert commented.splitlines()[0].rstrip().endswith("|"), (
            "commented pipeline continuation was split with a semicolon"
        )
        assert "|;\ntee" not in commented, "commented pipeline continuation contains a separator"
        script.write_text("echo first\necho second\n", encoding="utf-8")
        assert not scan(script), "ordinary statement newlines were mistaken for continuation"
        script.write_text('echo "literal | && || tee printf"\necho done\n', encoding="utf-8")
        assert not scan(script), "quoted operator/command text was mistaken for shell syntax"
        script.write_text('echo "literal | && || tee\nprintf"\necho done\n', encoding="utf-8")
        assert not scan(script), "quoted multiline operator/command text was mistaken for syntax"
        script.write_text("echo data \\\ntee log.txt\n", encoding="utf-8")
        assert not scan(script), "a continued echo argument was mistaken for a tee command"
        script.write_text("sha256sum input.bin\n", encoding="utf-8")
        assert scan(script), "unbundled sha256sum command was not rejected"
        script.write_text("case x in x) sha256sum input.bin;; esac\n", encoding="utf-8")
        assert scan(script), "blocked command in a case arm was not rejected"
        script.write_text("case x in x) echo ok\nesac\nsha256sum input.bin\n", encoding="utf-8")
        assert scan(script), "case without a final ;; hid a following command"
        script.write_text("echo do sha256sum\n", encoding="utf-8")
        assert not scan(script), "a control-word argument was mistaken for a command"
        script.write_text('digest="$(printf data)"\n', encoding="utf-8")
        assert scan(script), "blocked command substitution was not rejected"
        script.write_text("digest=`printf data`\n", encoding="utf-8")
        assert scan(script), "blocked backtick substitution was not rejected"
        script.write_text('"$BASE/bin/tee" -a log.txt\n', encoding="utf-8")
        assert not scan(script), "explicit bundled tee helper was rejected"
        script.write_text('"/usr/bin/tee" -a log.txt\n', encoding="utf-8")
        assert scan(script), "unbundled qualified tee path was not rejected"
        script.write_text("command -p sha256sum input.bin\n", encoding="utf-8")
        assert scan(script), "command -p wrapper hid a blocked command"
        script.write_text("env -i sha256sum input.bin\n", encoding="utf-8")
        assert scan(script), "env -i wrapper hid a blocked command"
        script.write_text("env -u PATH tee log.txt\n", encoding="utf-8")
        assert scan(script), "env -u wrapper hid a blocked command"
        script.write_text("env -S 'sha256sum input.bin'\n", encoding="utf-8")
        assert scan(script), "env -S split-string wrapper hid a blocked command"
        script.write_text("command; sha256sum input.bin\nenv; tee log.txt\n", encoding="utf-8")
        assert scan(script), "empty command wrappers hid a following blocked command"
        script.write_text("echo 'example $(printf x)'\n# $(printf x)\n", encoding="utf-8")
        assert not scan(script), "literal/comment substitution text was mistaken for execution"
        script.write_text('echo "$(command -p printf data)"\n', encoding="utf-8")
        assert scan(script), "blocked command in double-quoted substitution was not rejected"
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
