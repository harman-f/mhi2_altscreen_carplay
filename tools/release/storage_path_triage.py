#!/usr/bin/env python3
"""Conservative triage of source path references for MIBR persistent migration.

Pure host analysis. Categories are work queues, never proof of writers/readers,
actual on-unit state, migration completeness, or a safe install.
"""
import argparse
import collections
import json
import re
import tempfile
from pathlib import Path

import storage_migration_review as review_inventory

ROOT = Path(__file__).resolve().parents[2]
STORAGE = "/mnt/app/root/"
PROJECT = STORAGE + "altscreen-u2/"


def classify(fragment):
    """Classify a literal *fragment*, not a verified runtime file."""
    if not fragment.startswith((STORAGE, "/tmp/mibr")):
        return "other-source", "inspect-manually"
    # Delimiters/format tokens can make a lexical hit only a prefix.
    if (fragment.endswith(("}", ".", "/"))
            or re.search(r"%[a-zA-Z]", fragment)):
        return "noncanonical-fragment", "resolve-before-mapping"
    if fragment.startswith("/tmp/mibr"):
        return "volatile-ipc-or-test", "retain-tmp-namespace"
    if fragment in (PROJECT.rstrip("/"), PROJECT + "config"):
        return "project-directory", "verify-runtime-root"
    if fragment.startswith(PROJECT + "bin/") or fragment.startswith(PROJECT + "scripts/"):
        return "installed-runtime", "check-boot-and-installer"
    if fragment.startswith(PROJECT + "logs/"):
        return "durable-log", "check-lifetime-and-retention"
    if fragment.startswith(PROJECT + "config/"):
        if fragment.endswith(".enabled") or fragment.endswith(".disabled"):
            return "persistent-presence-marker", "migrate-format-aware"
        return "project-config", "map-reader-writer-format"
    if (re.search(r"(?:[.-](?:enabled|disabled)|-disable|[.-]force-(?:on|off))$", fragment)
            or fragment.endswith("/rgi.on")):
        return "persistent-presence-marker", "migrate-format-aware"
    if fragment.endswith("-owned"):
        return "ownership-receipt", "preserve-uninstall-evidence"
    if ("backup" in fragment or "rollback" in fragment
            or fragment.endswith(".stock")):
        return "backup-or-rollback", "retain-exact-original-evidence"
    if fragment.startswith(STORAGE + "mibr-kit/"):
        return "version-receipt", "reconcile-with-version-namespace"
    if fragment.startswith(STORAGE + "mibr-view"):
        return "persisted-view", "map-view-consumers"
    if (fragment.startswith(STORAGE + "mibr-carplay111-")
            or fragment.startswith(STORAGE + "mibr-direct-output-")):
        return "legacy-carplay-config", "map-to-carplay-registry"
    if fragment.startswith(STORAGE + "mibr-v3"):
        return "legacy-installed-runtime", "check-boot-and-installer"
    return "unclassified-persistent", "manual-review"


def dynamic_context(root, record):
    """Fetch exact source line; preserve leads if checkout is unavailable."""
    path = record["source"]
    line = record["line"]
    candidate = root / path
    if not candidate.is_file():
        return {"source": path, "line": line, "context_class": "source-unavailable",
                "review": "recheck-exact-source"}
    lines = candidate.read_text(encoding="utf-8", errors="replace").splitlines()
    if line < 1 or line > len(lines):
        return {"source": path, "line": line, "context_class": "line-drift",
                "review": "recheck-exact-source"}
    source_line = lines[line - 1].strip()
    if path.startswith("tools/release/"):
        kind, action = "host-tool-source", "exclude-from-on-unit-runtime-only-after-review"
    elif re.search(r"\bexport (?:PATH|LD_LIBRARY_PATH)=", source_line):
        kind, action = "runtime-search-path", "preserve-and-verify-target-env"
    elif source_line.startswith("#define ") and '"/mnt/app/root"' in source_line:
        kind, action = "macro-persistent-root", "enumerate-macro-consumers"
    elif re.search(r'\blstat\("/mnt/app/root"', source_line):
        kind, action = "mount-root-probe", "preserve-qnx-mount-preflight"
    elif re.search(r'^\w*TMP=/mnt/app/root/', source_line):
        kind, action = "persistent-staging-path", "review-same-fs-staging-and-rollback"
    elif source_line.startswith("Changes are persistent under "):
        kind, action = "usage-documentation", "confirm-no-runtime-effect"
    elif source_line.startswith("#define "):
        kind, action = "compiled-path-macro", "trace-every-macro-consumer"
    elif (source_line.startswith("#") or source_line.startswith("/*")
          or source_line.startswith("*")):
        kind, action = "comment-or-documentation", "confirm-no-runtime-effect"
    elif (re.search(r'["\x27]/mnt/app/root["\x27]', source_line)
          or re.search(r"\bROOT=/mnt/app/root\b", source_line)
          or re.search(r"\bBASE=/mnt/app/root\b", source_line)):
        kind, action = "composed-persistent-root", "enumerate-all-suffix-consumers"
    elif "LD_LIBRARY_PATH=" in source_line:
        kind, action = "embedded-runtime-env", "preserve-generated-runtime-env"
    else:
        kind, action = "unclassified-nonliteral", "read-source-and-evaluate"
    return {
        "source": path, "line": line, "context_class": kind,
        "review": action, "source_excerpt": source_line[:280],
        "not_verified_as_file": True,
    }


def build(review, root=ROOT):
    assert review["migration_authorized"] is False, "unreviewed migration flag"
    assert review["status"] == "REVIEW_REQUIRED_NOT_MIGRATION_READY", "unexpected status"
    grouped = collections.defaultdict(list)
    for item in review["unmatched_literal_references"]:
        path = item["literal_fragment"]
        assert isinstance(path, str) and path, "empty path fragment"
        grouped[path].append({"source": item["source"], "line": item["line"]})
    records = []
    for fragment in sorted(grouped):
        kind, action = classify(fragment)
        locations = sorted(grouped[fragment], key=lambda r: (r["source"], r["line"]))
        records.append({
            "literal_fragment": fragment,
            "category": kind,
            "review_action": action,
            "occurrences": len(locations),
            "source_locations": locations,
            "runtime_path_proven": False,
            "reader_writer_roles_proven": False,
        })
    dynamic = [
        dynamic_context(root, lead)
        for lead in review["unresolved_dynamic_or_nonliteral_source_lines"]
    ]
    assert len(dynamic) == len(review["unresolved_dynamic_or_nonliteral_source_lines"])
    totals = collections.Counter(row["category"] for row in records)
    occurrences = collections.Counter()
    for row in records:
        occurrences[row["category"]] += row["occurrences"]
    contexts = collections.Counter(x["context_class"] for x in dynamic)
    return {
        "schema_version": 1,
        "kind": "source-path-triage-not-migration-authorization",
        "evidence_grade": "lexical-syntax-and-reviewed-source-context-only",
        "source_inventory_sha256": review["source_sha256"],
        "counts": {
            "raw_lexical_occurrences": sum(row["occurrences"] for row in records),
            "distinct_lexical_fragments": len(records),
            "nonliteral_source_lines": len(dynamic),
            "fragment_categories": dict(sorted(totals.items())),
            "occurrences_by_category": dict(sorted(occurrences.items())),
            "nonliteral_contexts": dict(sorted(contexts.items())),
        },
        "fragment_groups": records,
        "nonliteral_source_contexts": dynamic,
        "remaining_manual_review": [
            "Confirm all path fragments and dynamic suffixes against exact callers",
            "Find real readers, writers, boot, restore and install/uninstall consumers",
            "Treat persistent presence markers and revision/CRC files format-aware",
            "Keep volatile QNX /tmp IPC unchanged in initial migration",
            "Verify current actual on-unit state separately before any write",
        ],
        "migration_authorized": False,
    }


def self_test():
    # Classification is conservative, not an automatic destination selection.
    samples = {
        "/tmp/mibr-parity-session.lock": "volatile-ipc-or-test",
        "/mnt/app/root/mibr-carplay-autodirect.enabled": "persistent-presence-marker",
        "/mnt/app/root/mibr-isotx2-gate-disable": "persistent-presence-marker",
        "/mnt/app/root/mibr-carplay111-bit26.force-on": "persistent-presence-marker",
        "/mnt/app/root/mibr-carplay111-bit26.force-off": "persistent-presence-marker",
        "/mnt/app/root/mibr-parity-status-enabled": "persistent-presence-marker",
        "/mnt/app/root/altscreen-u2/config/display-scaling.conf": "project-config",
        "/mnt/app/root/altscreen-u2/config/mibr-menu.conf": "project-config",
        "/mnt/app/root/mibr-kit/installed-version.properties": "version-receipt",
        "/mnt/app/root/mibr-deploy-most20-owned": "ownership-receipt",
        "/mnt/app/root/altscreen-u2/scripts/common.sh": "installed-runtime",
        "/mnt/app/root/altscreen-u2/config/%s.conf": "noncanonical-fragment",
        "/mnt/app/root/mibr-view}": "noncanonical-fragment",
        "/mnt/app/root/mibr-parity-drive.enabled": "persistent-presence-marker",
    }
    for path, expected in samples.items():
        actual = classify(path)[0]
        assert actual == expected, (path, actual, expected)
    fake = {
        "migration_authorized": False, "status": "REVIEW_REQUIRED_NOT_MIGRATION_READY",
        "source_sha256": {},
        "unmatched_literal_references": [
            {"literal_fragment": "/tmp/mibr-lock", "source": "a.sh", "line": 2},
            {"literal_fragment": "/tmp/mibr-lock", "source": "b.sh", "line": 8},
            {"literal_fragment": "/mnt/app/root/mibr-parity-drive.enabled",
             "source": "c.sh", "line": 5},
        ],
        "unresolved_dynamic_or_nonliteral_source_lines": [],
    }
    with tempfile.TemporaryDirectory(prefix="mibr-triage-") as temp:
        root = Path(temp)
        (root / "sample.c").write_text(
            '#define MIBR_CFG_PERSIST_ROOT "/mnt/app/root"\n'
            '/* example: /mnt/app/root */\n'
            'ROOT=/mnt/app/root\n'
            'TMP=/mnt/app/root/lsd.tmp.$$\n', encoding="utf-8"
        )
        expected = ("macro-persistent-root", "comment-or-documentation",
                    "composed-persistent-root", "persistent-staging-path")
        for line, category in enumerate(expected, 1):
            result = dynamic_context(root, {"source": "sample.c", "line": line})
            assert result["context_class"] == category, (line, result)
    s = build(fake)
    assert s["counts"]["raw_lexical_occurrences"] == 3
    assert s["counts"]["distinct_lexical_fragments"] == 2
    assert s["migration_authorized"] is False
    print("STORAGE_PATH_TRIAGE_SELF_TEST=PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-json", type=Path,
                        help="optional previously generated storage-migration-review JSON")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    review = (json.loads(args.review_json.read_text(encoding="utf-8"))
              if args.review_json else
              review_inventory.compile_review(review_inventory.source_inventory.build()))
    report = build(review)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print("STORAGE_PATH_TRIAGE=PARTIAL " + json.dumps(report["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
