# GitHub Pages publication — Cluster Atlas

**Prepared:** 2026-11-16. This is an operational runbook, **not** a claim that a public site is already live.

## Architecture

The Atlas is a **single standalone HTML** file at `docs/index.html` with CSS-controlled offline-safe tabs and optional JavaScript enhancement for search/hash navigation. External links point only to public GitHub source documents and releases. No server, database, API key, analytics, webfont, CDN or proprietary firmware is needed.

Workflow: [`.github/workflows/cluster-atlas-pages.yml`](../../.github/workflows/cluster-atlas-pages.yml).
- On pull requests the `validate` job checks 58 original feature rows, 58 profiles, 22 data fields per row, seven topic tabs, internal anchors, duplicate IDs and sensitive-source markers.
- On `main` pushes (or a manual workflow run) the `deploy` job publishes **only `docs/index.html`**, not other `docs/` sources and not firmware or chat exports. This avoids exposing any extra files accidentally through the Pages artifact.
- No source branch merge or GitHub Pages settings change happens automatically from a draft PR.

## GitHub account setup (once)

1. Open **Settings → Pages** in `harman-f/mhi2_altscreen_carplay`.
2. Under **Build and deployment**, select **GitHub Actions** as the source.
3. Review and merge the Atlas PR into `main` only after source and browser acceptance. `develop` alone does not deploy the public site.
4. Check the **Cluster Atlas static-site validation and Pages deployment** workflow under Actions. Once it reports a successful Pages environment deployment, use the URL from the job/Settings. The expected project-hosting pattern is `https://harman-f.github.io/mhi2_altscreen_carplay/`, but **do not publish that as a confirmed live URL until tested**.
5. If Settings or Pages permissions prevent activation through the connected GitHub tool, the repository administrator must perform the Pages source selection in the GitHub UI.

## Publication acceptance

- [ ] Source-only 58×22 matrix and profile changes reviewed, including recent versions and negative release flags.
- [ ] Seven tabs work on desktop/mobile and with JavaScript disabled.
- [ ] Search/filter/sort and link-to-profile navigation work, even after changing tabs.
- [ ] No third-party raw chat export, VIN/FAZIT/ECU keys, passwords, private Research paths or proprietary binaries in deployed HTML.
- [ ] Original withdrawn MST2-cluster-nav 1.1.0 warning visible.
- [ ] GitHub Actions validation PASS on exact merge head and successful Pages deployment verified on an external browser.
