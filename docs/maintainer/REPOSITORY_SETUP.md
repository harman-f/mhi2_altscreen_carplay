# Repository setup / public metadata

This file records the intended GitHub repository settings for maintainers.

## Repository description

Recommended description:

> Open research for CarPlay AltScreen/Auxiliary Screen navigation in MQB Virtual Cockpit on VW Group MHI2 — Škoda first, SEAT/VW planned.

## Topics

Recommended GitHub topics:

- `mhi2`
- `mib2`
- `carplay`
- `altscreen`
- `screenalt`
- `virtual-cockpit`
- `instrument-cluster`
- `mqb`
- `skoda`
- `seat`
- `cupra`
- `volkswagen`
- `qnx`
- `most`
- `airplay`
- `reverse-engineering`
- `automotive`
- `infotainment`
- `rgi`
- `carplay-navigation`

## Features

Recommended initial repository features:

- Issues: **enabled**
- Discussions: **enabled**
- Wiki: **disabled initially**; enable once curated Wiki content is ready
- Projects: optional; leave disabled until there is a concrete roadmap board
- Sponsorships: not required
- Private vulnerability reporting: **enable before/when public**

Keep the repository private during initial curation. Change to public only after checking:

- README;
- license;
- proprietary binary content;
- commit history;
- screenshots/logs for personal information;
- references/attribution.

## Discussions

Recommended categories:

### 📣 Announcements

Format: Announcement

Purpose: maintainer updates, releases and major research milestones.

### 💬 General

Format: Open-ended discussion

Purpose: architecture, coordination and topics that are not actionable issues.

Template: `.github/DISCUSSION_TEMPLATE/general.yml`

### 💡 Ideas

Format: Open-ended discussion

Purpose: feature ideas, design proposals and future platform directions.

Template: `.github/DISCUSSION_TEMPLATE/ideas.yml`

### 🙋 Q&A

Format: Question and answer

Purpose: focused questions about architecture, compatibility and project use.

Template: `.github/DISCUSSION_TEMPLATE/q-a.yml`

### 🚗 Vehicle testing

Format: Open-ended discussion

Purpose: early tester coordination, new MHI2 variants and results that are not yet sufficiently reproducible for an Issue.

Template: `.github/DISCUSSION_TEMPLATE/vehicle-testing.yml`

## Issue policy

Blank Issues are disabled.

Issue forms:

- `Vehicle test report`
- `Research finding`
- `Project bug`

Questions, ideas and exploratory compatibility discussion should be redirected to Discussions.

## Suggested labels

Create a deliberately small label taxonomy.

### Type

- `type: bug`
- `type: research`
- `type: vehicle-test`
- `type: documentation`
- `type: build`
- `type: feature`

### Area

- `area: carplay-ios`
- `area: mhi2-native`
- `area: java`
- `area: virtual-cockpit`
- `area: most`
- `area: viewarea`
- `area: rgi`
- `area: tooling`

### Platform

- `platform: skoda`
- `platform: seat-cupra`
- `platform: volkswagen`
- `platform: cross-platform`

### Evidence / status

- `evidence: vehicle`
- `evidence: binary`
- `evidence: build`
- `evidence: prior-art`
- `status: needs-repro`
- `status: confirmed`
- `status: blocked`
- `status: help-wanted`

Avoid creating dozens of near-duplicate labels. The exact firmware/build belongs in the Issue body, not in a label.

## Merge policy

Recommended:

- Squash merge: **enabled / preferred**
- Rebase merge: optional
- Merge commits: optional, preferably disabled once public workflow settles
- Require PRs for external contributions
- Maintainers may commit documentation/research checkpoints directly while the project is in early bootstrap

Before the project becomes larger, consider branch protection for `main` with:

- required check: `Publication integrity audit`;
- relevant path-scoped native build checks when applicable;

- PR required for non-maintainers;
- required successful CI when CI exists;
- conversation resolution required;
- no force pushes.

## Releases

Do not call early experimental artifacts stable releases.

Suggested progression:

- research snapshots;
- PoC / vehicle-test artifacts;
- alpha;
- beta;
- stable only after platform/firmware gates and recovery behavior are well established.

Every binary release should carry:

- source commit;
- supported target(s);
- build provenance;
- SHA-256;
- explicit experimental/stability status;
- recovery instructions.

## Public-readiness checklist

Before switching the repository to public:

- [ ] Repository description set
- [ ] Topics set
- [ ] Discussions enabled
- [ ] Discussion categories created
- [ ] Issue forms render correctly
- [ ] PR template renders correctly
- [ ] GPL-3.0-or-later stated clearly
- [ ] Third-party notices reviewed
- [ ] No OEM firmware dump accidentally committed
- [ ] No Apple system binary accidentally committed
- [ ] No proprietary commercial package accidentally committed
- [ ] No VIN/address/credential/personal data in screenshots, logs or history
- [ ] Prior-art links/attribution checked
- [ ] README current-state section matches the actual implementation


## Public naming and attribution boundary

Public implementation identifiers must be project-neutral.

Use descriptive project names for:

- branch names;
- pull-request development lines;
- runtime and deployment script names;
- profile IDs;
- log directories;
- build artifacts;
- status prefixes;
- architecture/runtime identifiers.

Do not name project-owned implementation surfaces after a comparator, commercial package, upstream
author or third-party build simply because that source informed the research.

This does **not** reduce attribution. External projects and comparator identities belong in:

- `docs/research/PUBLIC_REFERENCES.md`;
- provenance notes;
- evidence/finding documents where the identity is materially relevant;
- commit/issue discussion when tracing the origin of a specific observation.

The intended boundary is:

```text
research/provenance: specific and attributable
project runtime/API/UI: semantic and project-neutral
```

Historical public names already present in immutable Git history do not need destructive rewriting.
New branches and new project-owned identifiers must follow this rule.
