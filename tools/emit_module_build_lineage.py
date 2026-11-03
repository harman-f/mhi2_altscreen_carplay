#!/usr/bin/env python3
"""Emit and verify host-side source-to-binary lineage for a pinned QNX build.

This records build provenance. It does NOT claim bit-for-bit reproducibility,
phone compatibility, Unit installation readiness or vehicle qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "modules/module-index.json"
FIELDS = ("source", "runtime", "build_scripts", "support_tools")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def safe_rel(name):
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("invalid relative path: " + repr(name))
    p = PurePosixPath(name)
    if p.is_absolute() or any(c in (".", "..") for c in name.split("/")):
        raise ValueError("unsafe path: " + repr(name))
    return p.as_posix()


def regular_file(root, relative):
    path = root / safe_rel(relative)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("reference escapes source root: " + relative)
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing/non-regular file: " + relative)
    return path


def sha_file(path):
    dig = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            dig.update(chunk)
    return dig.hexdigest()


def collect_inputs(root, index, modules):
    paths = set()
    for name in modules:
        block = index["modules"][name]
        for field in FIELDS:
            for source in block.get(field, []):
                relative = safe_rel(source)
                folder = root / relative
                if folder.is_symlink() or not folder.exists():
                    raise ValueError("unavailable source input: " + relative)
                entries = sorted(folder.rglob("*")) if folder.is_dir() else [folder]
                for file in entries:
                    if file.is_symlink():
                        raise ValueError("symlink input not allowed: " + str(file))
                    if file.is_file():
                        paths.add(file.relative_to(root).as_posix())
    for filename in index.get("shared_orchestration", []):
        paths.add(safe_rel(filename))
    return [{"path": rel, "sha256": sha_file(regular_file(root, rel)),
             "size": regular_file(root, rel).stat().st_size} for rel in sorted(paths)]


def parse_artifacts(root, index, specs):
    found, seen, seen_paths = [], set(), set()
    for spec in specs:
        pair, sep, filename = spec.partition("=")
        module, colon, logical = pair.partition(":")
        if not sep or not colon or module not in index["modules"]:
            raise ValueError("artifact must be MODULE:LOGICAL=build/relative/path")
        if logical not in index["modules"][module].get("outputs", []):
            raise ValueError("undeclared output owner/name: " + pair)
        if (module, logical) in seen:
            raise ValueError("duplicate logical output: " + pair)
        seen.add((module, logical))
        rel = safe_rel(filename)
        if not rel.startswith("build/"):
            raise ValueError("build output must be under build/: " + rel)
        if rel in seen_paths:
            raise ValueError("one binary cannot have multiple declared output names: " + rel)
        seen_paths.add(rel)
        source = regular_file(root, rel)
        found.append({"module": module, "logical_name": logical, "path": rel,
                      "sha256": sha_file(source), "size": source.stat().st_size})
    if not found:
        raise ValueError("at least one compiled binary is required")
    return sorted(found, key=lambda row: (row["module"], row["logical_name"]))


def transitive_modules(index, selected):
    """Include all declared build dependencies, with cycle protection."""
    modules = index["modules"]
    names = set()
    pending = list(selected)
    while pending:
        name = pending.pop()
        if name in names:
            continue
        if name not in modules:
            raise ValueError("undeclared module dependency: " + name)
        names.add(name)
        pending.extend(modules[name]["depends_on"])
    return sorted(names)


def produce(root, index, commit, profile, toolchain, dockerfile_sha, specs):
    if not HEX40.fullmatch(commit) or not HEX40.fullmatch(toolchain):
        raise ValueError("exact 40-digit source/toolchain commits are required")
    if not HEX64.fullmatch(dockerfile_sha):
        raise ValueError("exact toolchain Dockerfile SHA-256 is required")
    if profile not in index["profiles"]:
        raise ValueError("unknown target profile: " + profile)
    artifacts = parse_artifacts(root, index, specs)
    names = transitive_modules(index, {row["module"] for row in artifacts})
    inputs = collect_inputs(root, index, names)
    checksum = hashlib.sha256()
    for row in inputs:
        checksum.update((row["path"] + "\0" + row["sha256"] + "\n").encode())
    index_canonical = json.dumps(index, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema_version": 1,
        "module_index_sha256": hashlib.sha256(index_canonical).hexdigest(),
        "build_scope": "QNX_6.5_ARMv7_cross_build_only",
        "vehicle_qualified": False,
        "bit_reproducible_verified": False,
        "source_commit": commit,
        "toolchain_commit": toolchain,
        "toolchain_dockerfile_sha256": dockerfile_sha,
        "requested_profile_not_qualification": profile,
        "module_dependencies": {name: index["modules"][name]["depends_on"] for name in names},
        "source_coverage": {name: index["modules"][name]["build_coverage"] for name in names},
        "source_tree_sha256": checksum.hexdigest(),
        "inputs": inputs,
        "artifacts": artifacts,
    }


def verify(root, doc):
    if doc.get("schema_version") != 1 or doc.get("vehicle_qualified") is not False:
        raise ValueError("invalid lineage or unsupported vehicle claim")
    for name in ("inputs", "artifacts"):
        if not isinstance(doc.get(name), list) or not doc[name]:
            raise ValueError("missing manifest entries: " + name)
        for row in doc[name]:
            path = regular_file(root, row["path"])
            if path.stat().st_size != row["size"] or sha_file(path) != row["sha256"]:
                raise ValueError("lineage hash mismatch: " + row["path"])
    if not HEX40.fullmatch(doc.get("source_commit", "")):
        raise ValueError("invalid recorded source revision")
    if not HEX40.fullmatch(doc.get("toolchain_commit", "")):
        raise ValueError("invalid recorded toolchain revision")
    if not HEX64.fullmatch(doc.get("module_index_sha256", "")):
        raise ValueError("invalid module index receipt")
    if not HEX64.fullmatch(doc.get("toolchain_dockerfile_sha256", "")):
        raise ValueError("invalid recorded Dockerfile digest")
    if root == ROOT and INDEX.is_file():
        actual_index = json.loads(INDEX.read_text(encoding="utf-8"))
        canonical = json.dumps(actual_index, sort_keys=True, separators=(",", ":")).encode()
        if hashlib.sha256(canonical).hexdigest() != doc["module_index_sha256"]:
            raise ValueError("module owner/dependency index changed since build")
    checksum = hashlib.sha256()
    for row in sorted(doc["inputs"], key=lambda z: z["path"]):
        checksum.update((row["path"] + "\0" + row["sha256"] + "\n").encode())
    if checksum.hexdigest() != doc["source_tree_sha256"]:
        raise ValueError("source tree hash mismatch")
    return True


def self_test():
    with tempfile.TemporaryDirectory(prefix="lineage-negative-") as directory:
        root = Path(directory)
        (root / "src").mkdir()
        (root / "build").mkdir()
        (root / "src/example.c").write_text("int main(void){return 0;}\n")
        (root / "build/example.bin").write_bytes(b"synthetic output, not a release")
        (root / "tool.sh").write_text("#!/bin/sh\nexit 0\n")
        index = {"profiles": ["synthetic"], "shared_orchestration": ["tool.sh"],
                 "modules": {"example": {"depends_on": [], "source": ["src"],
                             "build_scripts": [], "outputs": ["example.bin"],
                             "build_coverage": "partial"}}}
        args = ["example:example.bin=build/example.bin"]
        a = produce(root, index, "a" * 40, "synthetic", "b" * 40, "c" * 64, args)
        b = produce(root, index, "a" * 40, "synthetic", "b" * 40, "c" * 64, args)
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
        assert verify(root, a)
        index["modules"]["example"]["depends_on"] = ["helper"]
        index["modules"]["helper"] = {"depends_on": [], "source": ["tool.sh"],
                                      "build_scripts": [], "outputs": [],
                                      "build_coverage": "partial"}
        graph = produce(root, index, "a" * 40, "synthetic", "b" * 40, "c" * 64, args)
        assert "helper" in graph["module_dependencies"]
        index["modules"]["example"]["depends_on"] = []
        del index["modules"]["helper"]
        for invalid in (["example:bogus=build/example.bin"], args * 2,
                        ["example:example.bin=../outside.bin"]):
            try:
                produce(root, index, "a" * 40, "synthetic", "b" * 40, "c" * 64, invalid)
            except ValueError:
                pass
            else:
                raise AssertionError("accepted invalid lineage output " + repr(invalid))
        (root / "build/example.bin").write_bytes(b"modified")
        try:
            verify(root, a)
        except ValueError:
            pass
        else:
            raise AssertionError("accepted tampered build output")
    print("MODULE_BUILD_LINEAGE_SELF_TEST=PASS")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--verify", metavar="MANIFEST")
    p.add_argument("--commit")
    p.add_argument("--target-profile")
    p.add_argument("--toolchain-commit")
    p.add_argument("--toolchain-dockerfile-sha256")
    p.add_argument("--artifact", action="append", default=[])
    p.add_argument("--out")
    args = p.parse_args()
    if args.self_test:
        self_test()
    if args.verify:
        doc = json.loads(regular_file(ROOT, args.verify).read_text())
        verify(ROOT, doc)
        print("MODULE_BUILD_LINEAGE_VERIFY=PASS")
    if args.out:
        if not all((args.commit, args.target_profile, args.toolchain_commit,
                    args.toolchain_dockerfile_sha256)):
            p.error("all exact source/profile/toolchain arguments are required to emit")
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                         cwd=ROOT, text=True).strip()
        if actual != args.commit:
            raise SystemExit("source HEAD differs from requested build commit")
        index = json.loads(INDEX.read_text())
        doc = produce(ROOT, index, args.commit, args.target_profile,
                      args.toolchain_commit, args.toolchain_dockerfile_sha256,
                      args.artifact)
        target = ROOT / safe_rel(args.out)
        if not args.out.startswith("build/"):
            p.error("manifest output must be under build/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
        verify(ROOT, doc)
        print("MODULE_BUILD_LINEAGE_EMIT=PASS " + args.out)
    if not (args.self_test or args.verify or args.out):
        p.error("use --self-test, --verify, and/or --out")


if __name__ == "__main__":
    main()
