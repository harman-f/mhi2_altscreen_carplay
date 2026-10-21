# Public publication checklist

Originally prepared for the initial public launch. **For current changes**, apply this checklist to every proposed PR and release; see the [October 2026 publication/issue policy](ISSUE_AND_PUBLICATION_POLICY.md) and [documentation audit](DOCUMENTATION_AUDIT_2026-10-22.md). History and previously posted issue comments require separate review; a current-tree cleanup does not scrub Git history or externally hosted attachments.

## GitHub About

Recommended description:

> Open research for CarPlay AltScreen/Auxiliary Screen navigation in MQB Virtual Cockpit on VW Group MHI2 — Škoda first, SEAT/VW planned.

Recommended topics:

`mhi2`, `mib2`, `carplay`, `altscreen`, `screenalt`, `virtual-cockpit`,
`instrument-cluster`, `mqb`, `skoda`, `seat`, `cupra`, `volkswagen`,
`qnx`, `most`, `airplay`, `reverse-engineering`, `automotive`,
`infotainment`, `rgi`, `carplay-navigation`

Website: leave empty initially unless a dedicated project page exists.

## Repository features

Recommended initial state:

- Issues: enabled
- Discussions: enabled
- Wiki: disabled initially
- Projects: optional / disabled until actually used

## Discussion categories

Recommended:

- Announcements
- General
- Ideas
- Q&A
- Vehicle testing

The repository already contains Discussion forms for General, Ideas and Q&A.

## Privacy gate

Before public visibility:

- [ ] current tree contains no personal names/addresses/e-mail/private account identifiers
- [ ] public binaries passed string-level privacy audit
- [ ] no location-bearing screenshots
- [ ] no VINs
- [ ] no private repository/registry identifiers
- [ ] no credentials
- [ ] no OEM/Apple/commercial proprietary binary dumps
- [ ] temporary transfer files removed
- [ ] public history reset to clean baseline
- [ ] old Actions runs containing pre-public build/provenance data removed
- [ ] GitHub Private vulnerability reporting enabled

## Technical gate

- [ ] `direct-ts-remux` canonical SHA documented
- [ ] experimental GEN2 snapshot SHA documented
- [ ] current development status is newer than or equal to the latest vehicle findings
- [ ] Known Issues reflects current lifecycle problems
- [ ] compatibility gate for exact MU1440 `libairplay.so` documented
- [ ] rollback language present
- [ ] experimental binaries are not described as stable releases

## After public visibility

- [ ] verify README links as logged-out visitor
- [ ] verify Discussions tab
- [ ] verify Issue forms
- [ ] verify PR template
- [ ] verify binary download works
- [ ] verify repository license is detected by GitHub
- [ ] verify Topics/Description render correctly


## Recommended branch protection after public launch

Once external PRs are expected, require:

- required check: Publication integrity audit;
- relevant component build check when the PR touches that component;
- conversation resolution before merge;
- no force pushes to `main`.

The heavy QNX builds are path-filtered, so documentation-only PRs should not need all native builds.
