"""Synthetic host-only tests for the detached source-only package builder."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tools.package_source_v1 import (
    ALLOWLIST_PATH,
    MANIFEST_NAME,
    PACKAGE_KIND,
    PackageError,
    _is_excluded,
    build_package,
    collect_source,
    parse_allowlist,
)
from tools.check_mu1440_target_shell import _blocked_command_lines, _terminate_unquoted_newlines


class SourcePackageV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="source-package-v1-")
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "Source Package Test"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "source-package-test@example.invalid"], check=True)
        for directory in ("src/native/altscreen111-gen2", "runtime/auto-direct", "runtime/experimental",
                          "runtime/release", "runtime/.research", "settings", "deployment", "tools",
                          "docs/architecture", "docs/build", "docs/research", "LICENSES"):
            (self.repo / directory).mkdir(parents=True, exist_ok=True)
        (self.repo / "src/native/altscreen111-gen2/example.c").write_text("int example(void) { return 1; }\n", encoding="utf-8")
        (self.repo / "runtime/auto-direct/worker.ksh").write_text("#!/bin/ksh\necho source-only\n", encoding="utf-8")
        (self.repo / "runtime/experimental/viewarea_mode.sh").write_text("experimental\n", encoding="utf-8")
        (self.repo / "src/experimental/prototype.c").parent.mkdir(parents=True, exist_ok=True)
        (self.repo / "src/experimental/prototype.c").write_text("experimental\n", encoding="utf-8")
        (self.repo / "docs/build/SOURCE_PACKAGE_V1.md").write_text("Public source package notes.\n", encoding="utf-8")
        (self.repo / "docs/build/DIRECT_TS_REMUX_BUILD.md").write_text(
            "private Research ref 1234567890123456789012345678901234567890\n", encoding="utf-8")
        (self.repo / "LICENSE").write_text("Synthetic license notice.\n", encoding="utf-8")
        (self.repo / "docs/research/private.md").write_text("must not be packaged\n", encoding="utf-8")
        (self.repo / "runtime/release/old.py").write_text("must not be packaged\n", encoding="utf-8")
        (self.repo / "tools/.research/notes.py").parent.mkdir(parents=True, exist_ok=True)
        (self.repo / "tools/.research/notes.py").write_text("must not be packaged\n", encoding="utf-8")
        (self.repo / "src/artifacts/image.png").parent.mkdir(parents=True, exist_ok=True)
        (self.repo / "src/artifacts/image.png").write_bytes(b"\x89PNG\r\n")
        (self.repo / "src/native/altscreen111-gen2/logo.png").write_bytes(b"synthetic binary asset")
        (self.repo / "tools/package_source_v1.py").write_text("synthetic package tool\n", encoding="utf-8")
        (self.repo / "tests/test_package_source_v1.py").parent.mkdir(parents=True, exist_ok=True)
        (self.repo / "tests/test_package_source_v1.py").write_text("synthetic package test\n", encoding="utf-8")
        (self.repo / ".github/workflows").mkdir(parents=True, exist_ok=True)
        (self.repo / ".github/workflows/source-package-v1.yml").write_text("name: fixture\n", encoding="utf-8")
        (self.repo / "docs/architecture/README.md").write_text("Public architecture.\n", encoding="utf-8")
        self._write_allowlist([
            "src/native/altscreen111-gen2/example.c",
            "runtime/auto-direct/worker.ksh",
            "docs/build/SOURCE_PACKAGE_V1.md",
            "docs/architecture/README.md",
            "LICENSE",
            ".github/workflows/source-package-v1.yml",
            "tools/package_source_v1.py",
            "tests/test_package_source_v1.py",
            "tools/source-package-v1.paths",
        ])
        self._commit()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _commit(self) -> None:
        subprocess.run(["git", "-C", str(self.repo), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "-m", "fixture"], check=True)

    def _write_allowlist(self, entries: list[str]) -> None:
        (self.repo / "tools/source-package-v1.paths").write_text("\n".join(entries) + "\n", encoding="utf-8")

    def _archive_members(self, path: Path) -> dict[str, bytes]:
        with tarfile.open(path, "r:gz") as archive:
            return {member.name: archive.extractfile(member).read()
                    for member in archive.getmembers() if member.isfile()}

    def test_deterministic_archive_and_detached_provenance(self) -> None:
        first = build_package(self.repo, self.base / "first.tar.gz")
        second = build_package(self.repo, self.base / "second.tar.gz")
        first_bytes = first[0].read_bytes()
        second_bytes = second[0].read_bytes()
        # The outer filename is not stored in the gzip stream.
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(first[3]["package_kind"], PACKAGE_KIND)
        self.assertIn("NOT_AN_INSTALL_KIT", first[3]["package_kind"])
        self.assertIn("NOT_VEHICLE_QUALIFIED", first[3]["package_kind"])
        self.assertEqual(hashlib.sha256(first_bytes).hexdigest(), first[3]["archive"]["sha256"])
        detached = json.loads(first[1].read_text(encoding="utf-8"))
        self.assertEqual(detached["source_commit"], first[3]["source_commit"])
        self.assertEqual(detached["source_tree"], first[3]["source_tree"])
        members = self._archive_members(first[0])
        archived_manifest = json.loads(members[MANIFEST_NAME].decode("utf-8"))
        self.assertEqual(archived_manifest["files"], detached["files"])
        self.assertEqual(hashlib.sha256(first[0].read_bytes()).hexdigest(), detached["archive"]["sha256"])
        checks = first[2].read_text(encoding="ascii").splitlines()
        self.assertIn(detached["archive"]["sha256"], checks[0])

    def test_curated_test_scope_excludes_unshipped_experimental_dependencies(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        packaged_paths = set(parse_allowlist((repo_root / ALLOWLIST_PATH).read_bytes()))

        self.assertIn("tests/test_package_source_v1.py", packaged_paths)
        self.assertNotIn("tests/test_public_mibr3.py", packaged_paths)
        self.assertNotIn("src/experimental/mibr3/api_v3_contract.py", packaged_paths)
        self.assertNotIn("src/experimental/mibr3/mibr_v3_parity_mailbox.c", packaged_paths)
        self.assertNotIn("src/experimental/mibr3/mibr_v3_parity_mailbox_probe.c", packaged_paths)
        self.assertNotIn("src/experimental/mibr3/mibr_v3_owner_lifecycle.c", packaged_paths)
        self.assertNotIn("src/experimental/mibr3/mibr_v3_owner_lifecycle_probe.c", packaged_paths)

    def test_experimental_test_cannot_be_reintroduced_through_the_allowlist(self) -> None:
        with self.assertRaisesRegex(PackageError, "outside the curated product closure"):
            parse_allowlist(
                ("tools/source-package-v1.paths\ntests/test_public_mibr3.py\n").encode("utf-8")
            )

    def test_target_shell_gate_detects_forbidden_commands_after_multiline_operators(self) -> None:
        cases = (
            ("echo data |\ntee log\n", "echo data |\ntee log;\n", "tee"),
            ("true &&\nprintf x\n", "true &&\nprintf x;\n", "printf"),
            ("false ||\ntee log\n", "false ||\ntee log;\n", "tee"),
        )
        for script, expected_normalized, command in cases:
            with self.subTest(script=script):
                self.assertEqual(_terminate_unquoted_newlines(script), expected_normalized)
                self.assertIn(2, _blocked_command_lines(script), command)

        commented = _terminate_unquoted_newlines("echo data | # pipeline continues\ntee log\n")
        self.assertTrue(commented.splitlines()[0].rstrip().endswith("|"))
        self.assertNotIn("|;\ntee", commented)
        self.assertIn(2, _blocked_command_lines("echo data | # pipeline continues\ntee log\n"))
        escaped_cases = (
            "echo data | \\\ntee log\n",
            "true && \\\nprintf x\n",
            "false || \\\ntee log\n",
            "true && pri\\\nntf x\n",
        )
        for script in escaped_cases:
            with self.subTest(script=script):
                self.assertIn(2, _blocked_command_lines(script))

        self.assertEqual(_blocked_command_lines("echo first\necho second\n"), [])
        self.assertEqual(
            _blocked_command_lines('echo "literal | && || tee printf"\necho done\n'), []
        )
        self.assertEqual(
            _blocked_command_lines('echo "literal | && || tee\nprintf"\necho done\n'), []
        )
        self.assertEqual(_blocked_command_lines("echo data \\\ntee log\n"), [])

    def test_path_type_and_private_path_exclusions(self) -> None:
        manifest, files = collect_source(self.repo)
        self.assertIn("src/native/altscreen111-gen2/example.c", files)
        self.assertIn("runtime/auto-direct/worker.ksh", files)
        self.assertIn("docs/build/SOURCE_PACKAGE_V1.md", files)
        self.assertIn("LICENSE", files)
        for excluded in (
            "docs/research/private.md", "runtime/release/old.py", "runtime/.research/nope.sh",
            "tools/.research/notes.py", "src/artifacts/image.png", "src/native/altscreen111-gen2/logo.png",
            "runtime/experimental/viewarea_mode.sh", "src/experimental/prototype.c",
            "docs/build/DIRECT_TS_REMUX_BUILD.md",
        ):
            self.assertNotIn(excluded, files)
        self.assertTrue(_is_excluded("docs/research/private.md"))
        self.assertTrue(_is_excluded("docs/build/DIRECT_TS_REMUX_BUILD.md"))
        self.assertNotIn("runtime/experimental/viewarea_mode.sh", files)
        self.assertEqual(manifest["source_tree"], subprocess.check_output(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD^{tree}"], text=True).strip())
        self.assertTrue(all(not entry["path"].casefold().startswith("docs/research/") for entry in manifest["files"]))

    def test_symlinks_are_rejected(self) -> None:
        target = self.repo / "src/native/altscreen111-gen2/example-link.c"
        try:
            target.symlink_to("example.c")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        entries = (self.repo / "tools/source-package-v1.paths").read_text(encoding="utf-8").splitlines()
        self._write_allowlist(entries[:-1] + ["src/native/altscreen111-gen2/example-link.c", entries[-1]])
        self._commit()
        with self.assertRaisesRegex(PackageError, "symlink is not allowed"):
            collect_source(self.repo)

    def test_detached_manifest_file_hashes_match_archive_bytes(self) -> None:
        archive, provenance_path, _, provenance = build_package(self.repo, self.base / "hashes.tar.gz")
        members = self._archive_members(archive)
        for item in provenance["files"]:
            data = members["source/" + item["path"]]
            self.assertEqual(len(data), item["size_bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
        detached = json.loads(provenance_path.read_text(encoding="utf-8"))
        self.assertEqual(detached["files"], provenance["files"])

    def test_existing_outputs_are_never_overwritten(self) -> None:
        archive = self.base / "fixed.tar.gz"
        archive.write_bytes(b"keep")
        with self.assertRaisesRegex(PackageError, "refusing to overwrite"):
            build_package(self.repo, archive)
        self.assertEqual(archive.read_bytes(), b"keep")

    def test_allowlist_rejects_duplicate_glob_absolute_parent_binary_and_excluded_paths(self) -> None:
        def rejected(path: str, message: str) -> None:
            with self.subTest(path=path):
                with self.assertRaisesRegex(PackageError, message):
                    parse_allowlist(("tools/source-package-v1.paths\n" + path + "\n").encode("utf-8"))

        with self.assertRaisesRegex(PackageError, "duplicate path"):
            parse_allowlist(b"tools/source-package-v1.paths\ntools/source-package-v1.paths\n")
        rejected("src/native/altscreen111-gen2/*.c", "glob syntax")
        rejected("/src/native/altscreen111-gen2/a.c", "relative and normalized")
        rejected("src/native/altscreen111-gen2/../a.c", "relative and normalized")
        rejected("src/native/altscreen111-gen2/a.so", "binary extension")
        rejected("docs/build/DIRECT_TS_REMUX_BUILD.md", "excluded path")
        rejected("src/experimental/prototype.c", "excluded path in allowlist")
        self.assertEqual(parse_allowlist(b"tools/source-package-v1.paths\nsrc/native/altscreen111-gen2/a.c\n")[-1],
                         "src/native/altscreen111-gen2/a.c")

    def test_allowlist_and_source_bytes_come_from_selected_commit(self) -> None:
        (self.repo / "src/native/altscreen111-gen2/example.c").write_text("uncommitted change\n", encoding="utf-8")
        (self.repo / "runtime/experimental/viewarea_mode.sh").write_text("uncommitted new file\n", encoding="utf-8")
        entries = (self.repo / "tools/source-package-v1.paths").read_text(encoding="utf-8").splitlines()
        self._write_allowlist(entries + ["runtime/experimental/viewarea_mode.sh"])
        _, files = collect_source(self.repo)
        self.assertEqual(files["src/native/altscreen111-gen2/example.c"], b"int example(void) { return 1; }\n")
        self.assertNotIn("runtime/experimental/viewarea_mode.sh", files)

    def test_optional_workflow_context_is_detached_and_local_safe(self) -> None:
        names = (
            "GITHUB_EVENT_NAME", "GITHUB_WORKFLOW", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
            "SOURCE_PACKAGE_PR_BASE_SHA", "SOURCE_PACKAGE_PR_HEAD_SHA",
        )
        with patch.dict(os.environ, {name: "" for name in names}):
            for name in names:
                os.environ.pop(name, None)
            _, local_provenance, _, local_record = build_package(self.repo, self.base / "local.tar.gz")
        self.assertTrue(all(value is None for value in local_record["workflow_context"].values()))
        self.assertTrue(all(value is None for value in json.loads(
            local_provenance.read_text(encoding="utf-8"))["workflow_context"].values()))

        context = {
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_WORKFLOW": "Source package",
            "GITHUB_RUN_ID": "12345",
            "GITHUB_RUN_ATTEMPT": "2",
            "SOURCE_PACKAGE_PR_BASE_SHA": "a" * 40,
            "SOURCE_PACKAGE_PR_HEAD_SHA": "b" * 40,
        }
        with patch.dict(os.environ, context):
            _, workflow_provenance, _, workflow_record = build_package(self.repo, self.base / "workflow.tar.gz")
        self.assertEqual(workflow_record["workflow_context"]["event_name"], "pull_request")
        self.assertEqual(workflow_record["workflow_context"]["pr_base_sha"], "a" * 40)
        self.assertEqual(json.loads(workflow_provenance.read_text(encoding="utf-8"))["workflow_context"],
                         workflow_record["workflow_context"])


if __name__ == "__main__":
    unittest.main()
