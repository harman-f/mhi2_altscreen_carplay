# Public repository documentation audit — 2026-10-22

## Scope and method

At audit start the public `main` was `76dc58db29072b7588066e0d5ca6a651a1ed7dba`, with 390 Git tree entries, 135 Markdown files, 106 under `docs/`. Four historically dated Final Drive Markdown reports were subsequently imported independently from the old #34 line. The repository's publication CI walks the **whole checked-out tree**, checks required files, pinned old artifact hashes, disallowed binaries, configured secret patterns and relative Markdown links. A hard current-tree check for separate non-public development identity was added. Principal status/index/architecture/release/compatibility/publication documents were also manually compared with the October evidence.

This is a *current-tree/documentation* audit, not a rewrite of existing Git history, an external GitHub attachment or issue edit audit, a legal clearance of third-party material, or a new vehicle acceptance test.

## Findings and corrections

| Area | Problem | Resolution |
| --- | --- | --- |
| README/docs index/Roadmap | October current status coexisted with an outdated newcomer link to the October 5 research preview | Put the cross-module status first and keep dated previews as historical reading |
| Old `CURRENT_DEVELOPMENT_STATUS` / `CURRENT_RESEARCH_STATUS` / October 5 preview | October 2/3/5 statements such as no tested HMI were misleading as present tense | Mark explicitly historical and link later status, HMI and vehicle evidence |
| `release/CURRENT.md` | Early list/claims excluded Most20 and described D2 as optional while the later September 29 addendum includes Most20 and persistent D2 by default; old text suggested documentation merges recreate the release tag | Consolidate effective seven-file ZIP and D2 status; keep binary and release tag unchanged |
| Final Drive PR #34 | Detailed vehicle evidence on a diverged stacked branch | Import *only* four dated Markdown records: final-drive status, switch matrix, zoom-cadence observations and exact local ZIP provenance; no installable scripts/archives copied |
| Recovery and parity | Zero writer errors did not distinguish phone/session teardown from native gate-proof loss or prove physical frame cadence | Maintain separate current timing, fault-isolation and owner qualification pages |
| HMI/control plane | Source builds, durable store/TEMP and actual visible configuration application can be confused | Keep UI, STORE, APPLY and current-session ACTIVE acceptance independent; describe MU1440-specific widgets separately from portable architecture |
| Classic vehicle-data research | Host/source candidate is not a phone-accepted feature | Preserve only the separately authored high-level optional-feature design; no original phone/OEM binaries or reconstructed implementation bodies |
| SEAT MU1409 | External adapted third-party 790 port could be misreported as our runtime | Compatibility matrix explicitly distinguishes the two |
| Publication checklist | Initial public-launch instructions were not a recurring publication audit | Cross-link current per-PR/privacy policy and this report; add non-public attribution check |

## Outstanding experimental PR disposition

| PR | Decision / rationale |
| --- | --- |
| #30 | Retire stacked clockdiag research branch; newer aggregated timing evidence exists; no runtime promotion |
| #31 | Retire unqualified opt-in POLLOUT driver experiment; no hardware replacement approval |
| #33 | Retire further pollwait fallback diagnostic; preserve dated observations, no release merge |
| #34 | Transfer four public evidence docs independently; close old stacked development review |
| #35 | Retire unqualified dual observer; host build is not target OEM-handshake PASS |
| #36 | Retire standalone right-wheel V1 draft; future current-owner/focus/visual/installer qualification remains |
| #48 | Retire old stacked experimental Luka/GEN2 recovery review; not vehicle-qualified or installable |

Closing a review is not deleting its branch, cancelling research or claiming a feature is tested. New product implementation must use a coherent current-main integration and separate physical acceptance.

## Audit boundary

The added filter prevents direct references to the non-public development account/repository **in the current checked-out source/text tree**. CI also protects the pre-existing pinned release artifact hashes and relative Markdown links. Previously published Git commits and GitHub edit history cannot be erased through a normal current-tree change. User-contributed issue attachments and original OEM/iOS binaries are outside this publication. A passing audit never constitutes legal provenance approval for externally sourced binaries or graphics, nor a live vehicle test.