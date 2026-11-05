# Research archive and navigation rules for contributors and agents

This file supplements [docs/AGENTS.md](../AGENTS.md) and the repository [AGENTS.md](../../AGENTS.md). For technical work, always read the repo-wide QNX/safety and publication rules first.

## Source of truth

The [research library index](README.md) is a **navigation layer**, not an alternative to [current architecture](../architecture/README.md), [current feature/vehicle evidence](../status/FEATURE_STATUS.md), [firmware profiles](../../modules/profiles/) or [package status](../packages/README.md).

Use exact, dated observations from the original report. Never infer a supported platform, successful Java build, installed patch or visible navigation-arrow result from a hypothesis, source code or third-party comparator.

## Every new research record should say

- **Status:** REFERENCE / OPEN RESEARCH / PROPOSAL / HISTORICAL SNAPSHOT / SUPERSEDED OVERVIEW.
- **Target and scope:** firmware, board (MMX or RCC), phone/app, cluster and version when known; identify unknowns.
- **Evidence:** measured log / firmware static / source compile / mock / inference, not a vague `tested`.
- **Date and source pointers:** exact commit, report, reproducible fixture or redacted capture where publishable.
- **Outcome:** what was established, what was disproved, what remains open and why it matters.
- **Current owner or successor:** link to the active module or later study when one exists.

Where a document was written before this convention, add a short **review annotation**, not a rewrite of its historical narrative.

## Supersession and archiving

A **SUPERSEDED OVERVIEW** flag is appropriate if a more recent canonical summary replaces that page's role; preserve original observations and update the index to point to the successor. If just one assumption is overturned (e.g. an earlier unknown hardware key is later measured), annotate **that conclusion** with later evidence. Do not label the entire experiment invalid.

Move finished experiments into the relevant topic folder and optionally tag as historical; reserve `archive/` for truly superseded umbrella summaries, not all old documents. Abandoned experiments stay available with a clear rationale and their negative outcomes.

## Navigation and publication gates

The topic index must link every active file it claims to catalog and link back to `../README.md`. Add the record to exactly one primary topic; cross-link other topics where it has relevance. Avoid dated `CURRENT_*` as the canonical entrypoint.

Maintain relative links and anchors when moving files; include data fixtures or test-plan references. Run `tools/docs/check_docs.py --scope all`. The separate QNX/boot/source rules still apply to any script or test linked here. Never copy private forensic bundles, unpublished vendor materials, credentials or private handoffs into public research.
