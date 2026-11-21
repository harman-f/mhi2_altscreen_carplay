# Fork diff, contributor provenance and expanded lineage — 16 November 2026

**Review:** public GitHub REST parent metadata, compare API ahead/behind at 2026-11-16, enumerated all fork branches for candidate exclusions, checked releases and upstream PR merge state; source/capability relationships from current public READMEs and the existing Atlas technical cards. No firmware installation, vehicle run, binary decompilation or third-party copying was performed. Historical 58 × 22 baseline dated **4 Nov 2026** was not re-scored.

## Curation outcome

- Original scored source roster **58**, visible curated comparison **56** after excluding only **two** verified default-branch-only behind-upstream copies. Original capability scores on other profiles are preserved. The removed identities are retained in `tools/docs/fork_watchlist.json` (outside the deployed single HTML) and Git history for later rescan.
- **Not deleted:** the two HARMAN-F forks that have meaningful feature or upstream contribution branches, `evanj495` with its distinct release branch, and similarly distinct author ports.
- **Source availability:** 55 of the 56 curated historical sources reachable at the earlier API check; ALeXXBody remains unavailable; do not call that repo a duplicate without evidence.
- Public diagram and filterable evidence table are now generated from the same 38 classified relationships: **10 GitHub ancestry, 2 GitHub-marked / rewritten-history ports, 13 documented code adaptations, 9 design/architectural credits, 4 pinned source dependencies**. Cross-family edges can appear in the target's platform cluster.

## Exact fork checks

| Fork | Upstream per GitHub metadata | Default branch comparison (fork relative to parent) | Branches / merged contributions | Curated site |
| --- | --- | --- | --- | --- |
| zakklmv/MHI2-Carplay-Maps | omonob/VW-MHI2-Wireless-Carplay-Maps | 1 ahead / 12 behind | Independent MU1440 cockpit layout, wired only | Keep |
| wasimlhr/mib2q-android-auto-cluster | luka-dev/mib2q-carplay-rgi | 22 ahead / 45 behind | [PR #33](https://github.com/luka-dev/mib2q-carplay-rgi/pull/33) **open**, not merged; AA MU0918 | Keep |
| waterfalldev/mib2q-carplay-enhanced-nonfpk | luka-dev/mib2q-carplay-rgi | 10 ahead / 18 behind | [PR #31](https://github.com/luka-dev/mib2q-carplay-rgi/pull/31) closed **without merge** (build portability); Non-FPK adaptation | Keep |
| Matze89x/mst2d-carplay-aid | tehfalcon-vw/mst2-nar-carplay-maps | Compare reports **no common ancestor** | Public source claims EU P0879D source adaptation and hardware reboot failures, not independently accepted | Keep (rewritten-history fork) |
| evanj495/mib2-carplay-rgi-altscreen | Allemon/mib2-carplay-rgi-altscreen | 1 ahead (README-only) / 161 behind on main | **MU1320/P4246-NAR release branch has 4 ahead**, 12 changed files, public SD release/author car report | Keep |
| yety-ua/mhi2-k3346-carplay-audio-upmix | ProManiFest2122/mhi2-k3346-carplay-vc | 6 ahead / 24 behind | Original audio-upmix code/host tests | Keep |
| maxim-smirnov/mhi2-carplay-cluster | luka-dev/mib2q-carplay-rgi | **0 ahead / 73 behind** | Only main; no release or PR found | **Hide; watch** |
| harman-f/harman-ax1800m-adapter-checker | RandomGenerated543/harman-ax1800m-adapter-checker | 9 ahead / 0 behind | Hardware-specific code additions | Keep |
| harman-f/qemu-mhi2 | iscle/qemu-mhi2 | **0 ahead / 0 behind on main** | **4 ahead** on `codex/windows-skoda-experimental`. [Upstream draft PR #2](https://github.com/iscle/qemu-mhi2/pull/2) **OPEN, not merged** | **Keep / experimental** |
| mathsls/MHI2-Carplay-Maps | ZzYunOvO/MHI2-Carplay-Maps | 8 ahead / 0 behind | Distinct source/packaging history; firmware proof per version | Keep |
| maxafanasiev/mib2q-carplay-wireless-cockpit | lindayi/mib2-carplay-rgi-altscreen | 7 ahead / 80 behind | Separate adapter / cockpit changes; **not native HU wireless** | Keep |
| KleinDevEur/mst2-eu-carplay-maps | tehfalcon-vw/mst2-nar-carplay-maps | Compare reports **no common ancestor** | Source-documented EU P0891D port with own build/tests, no physical car validation | Keep (rewritten-history fork) |
| Mr-MIBonk/mhi2-android-auto-cluster-map | MacsInSpace/mib-cluster-map | **0 ahead / 133 behind** | Only main; no releases or PR found | **Hide; watch** |
| harman-f/mib2-toolbox | jilleb/mib2-toolbox | **0 ahead / 34 behind on master** | Original `jilleb` repo created 2019-09-18; HARMAN-F fork 2022-08-30; two HARMAN-F upstream contributions [#219](https://github.com/jilleb/mib2-toolbox/pull/219) and [#220](https://github.com/jilleb/mib2-toolbox/pull/220) **MERGED** in 2022; separate `experimental` branch has **4 ahead** | **Keep / explain provenance** |

**Interpretation:** `fork=true` and its `parent` describe GitHub's structural ancestry. They do not grant authorship of parent code. Conversely, a stale default branch does not negate code on a release branch, or upstream contributions that have already merged. Rewritten histories defeat commit-parent ancestry detection even when their README traces a real port.

## Binary and code comparison policy

1. Confirm exact canonical fork parent, branch, pull request and tag before comparing bytes.
2. Compare Git merge-base, ahead/behind, top-level source files, and diff file scope. Document independent code vs README-only changes.
3. Optionally compare **public** original source and redistributable binaries: identical Git blob SHA or SHA-256 establishes byte identity only; dissimilar binaries can still derive from similar code. Reproducible builds and function-level Ghidra signatures may support lineage hypotheses, not conclusive author attribution.
4. Exclude common OEM/QNX/Apple/MFi runtime components, licensed firmware dumps, cloned SDK binaries, boilerplate and identical compilation units from assertions that two maintainers shared proprietary source.
5. When upstream PR is merged, record the original contributor and target merge rather than crediting the fork as an indefinitely separate release. Keep pending PRs explicitly pending.
6. Only a new, independently verified public code/firmware feature should restore a suppressed fork to the scored catalog. These archived entries can be manually scanned from the JSON watchlist; **no recurring monitor has been scheduled in this pass**.

## Important caveat

The lineage table uses primary public repo links and documented source-credit statements. Not every claimed code port has been independently verified at function-signature or object-binary level; hence explicit distinct relationship labels. The new family diagrams are fully self-contained inline SVG and retain a searchable source table as the authoritative evidence ledger. This is a source/provenance audit, **not** a 22-feature re-score or vehicle certification.
