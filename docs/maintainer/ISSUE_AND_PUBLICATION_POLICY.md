# Public publication and issue-tracking policy (October 2026)

The public repository documents a reproducible experimental project, accepts outside compatibility/bug reports and hosts independently publishable source. It is not an automatic mirror of development branches, private handoffs, device exports or work logs.

## Publication rules

- Use neutral project authorship and publicly accessible references; no private repository/account identifiers, inaccessible source links, personal names, email addresses, local paths, location or session IDs.
- Publish project-authored code and graphics with provenance/licensing, permitted public upstream references, sanitized aggregate vehicle evidence and synthetic test fixtures. Do not include original Apple/OEM binaries, JXE/JAR/firmware dumps, original disassembly/decompilation output or raw private traces.
- Separate the evidence labels OBSERVED, STATIC/RESEARCH, HOST/QNX BUILD, VEHICLE-TESTED, and OPEN. Source or host compilation is never an implied installable release.
- Review every changed file and generated output for embedded URLs, author identity, credentials, VIN, MAC/serial, location and proprietary content. For binaries, verify origin, hash and obvious embedded identity strings.
- Existing hash-pinned releases remain unchanged by docs-only publication. Changes to builds, assets and installers have independent review and exact-target/rollback gates. An existing Git history leak needs its own security response; simply deleting its current file is insufficient.

## Public issue practice

Public Issues should primarily capture external compatibility findings, reproducible faults, questions and contributions. Internal task coordination should be kept out of the public issue tracker. Experimental source PRs may remain public as clearly labelled drafts without implying current-release status.

Do not bulk-close external reports. A successful third-party port is valuable evidence but does not prove the project's own binary works on that firmware. Acknowledge contributors, ask for sanitized component hashes and non-destructive observations, and never request proprietary firmware dumps or an unqualified installation.

Maintainer-only historical task Issues may be closed individually with a concise public rationale. Open Draft PRs must be reviewed separately; never auto-merge, close as completed or label vehicle-proven merely to tidy the issue list.

## Porting principle

The MU1440/AID10 reference is an architectural starting point for compatible Skoda, SEAT and Volkswagen systems, not a cross-brand compatibility guarantee. Check the exact fitted cluster, firmware/components, OEM HMI view/widgets, original DSI inputs, display owner, runtime dependencies and rollback before any modification.
