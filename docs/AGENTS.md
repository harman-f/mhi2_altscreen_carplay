# Agent instructions for public documentation

These rules apply to everything under `docs/` and supplement the [repository-wide agent and QNX rules](../AGENTS.md) and [documentation policy](DOCUMENTATION_POLICY.md).

## Find the authoritative information first

1. Start at [docs home](README.md). Product and vehicle claims belong to [feature evidence](status/FEATURE_STATUS.md), exact release availability to [packages](packages/README.md), exact firmware identity to [profiles](../modules/profiles/), current runtime design to [architecture](architecture/README.md), and research to [research library](research/README.md).
2. Distinguish **SOURCE**, **HOST/BUILD**, **COMPLETE PACKAGE**, **UNIT OBSERVED**, **VEHICLE OBSERVED**, and **RELEASE** in every technical claim. Do not infer a higher level from a lower level.
3. Follow canonical source owners and the actual current `main`/`develop` tree before quoting old release notes, R-number build snapshots or research findings.
4. Never publish private handoffs, developer chats, credentials, raw vehicle identifiers, reverse-engineered proprietary payloads, unlicensed OEM code/assets or personally identifying captures to this public repository.

## Authoring and navigation conventions

- Every new human-facing area gets a `README.md` index; every index must offer a route **up**, **across** and **down** to canonical documents.
- Prefer meaningful topic folder names to build generations such as `R57`, `GEN2` or `U2`. Preserve exact historical filenames, SHA-256 values, interface symbols and named artifacts when renaming would falsify provenance.
- One canonical definition per subsystem. Link to that owner instead of duplicating changing defaults, test classifications, install procedures or manifest tables.
- On a move, update **all incoming and outgoing relative paths, Markdown anchors, embedded HTML links, test fixtures and build references in the same PR**. Do not leave blind duplicate Markdown files.
- Add a short status/scope header to new or reorganized research pages. Explicitly state what was measured vs inferred; name the target, date and new canonical implementation when established.
- Keep a dated original report's technical content and measured values intact. Correction/closure is an attributed annotation with evidence, **not a silent rewrite**.

## Research lifecycle and archival discipline

Read [research-specific rules](research/AGENTS.md). A dated experiment is valuable even if another approach won. Use **REFERENCE**, **OPEN RESEARCH**, **HISTORICAL**, **SUPERSEDED SUMMARY** or **INTEGRATED IN SOURCE** only with precise meaning. A supersession marker must link the actual newer canonical material and specify what it replaces.

## Required checks before PR / merge

- `python3 tools/docs/check_docs.py --self-test`
- `python3 tools/docs/check_docs.py --scope active`
- `python3 tools/docs/check_docs.py --scope all`
- Existing [publication CI](../.github/workflows/publication-audit.yml), source/release checks and target-shell gate where appropriate.
- Verify user-facing README and topic indexes describe the **same exact target and acceptance level** as the underlying evidence.
- Do not change implementation, boot paths, installer, firmware binary or published release merely to make a documentation refactor compile.
