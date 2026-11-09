# Three-profile beta package build

The canonical pipeline is `.github/workflows/multiprofile-beta-release.yml`.
It reassembles the **current public `main`** with exactly pinned, reviewed
build outputs from private Research on **GitHub-hosted `ubuntu-24.04`**.
No dedicated self-hosted QNX/J9 runner is needed for this **prebuilt** mode.
It is a **build-and-validation pipeline**, not a new native compilation and
not an automatic GitHub Release. An archived Research binary is not thereby
vehicle-tested or legally approved for public redistribution.

## Two independent release gates

1. The no-secret `source-locks` job checks
   `modules/profiles/MENU_SOURCE_LOCK.json` for the three previously approved
   firmware-specific `MIBR-CarPlay.jar` files (J9 class major 46). A new Java,
   profile-HMI or settings-registry input rejects those JARs. Only a separately
   reviewed Research/J9 build may renew the lock.
2. Native CarPlay, Broker, QNX support and Navigation outputs plus the
   `MIBR-Extender-P1-BootProbe.jar` come from the **exact r11b Research ZIP**,
   identified by `tools/release/RESEARCH_PREBUILT_LOCK.json`. That lock pins
   the Research commit and whole ZIP SHA-256, and **19 public Git object
   fingerprints** for QNX/native sources, build scripts, compiler image lock,
   module index and settings registry. The staging script checks the original
   complete ZIP, SHA-256 inventory, native binary manifest, original compiler
   provenance and staged file hashes before the assembler runs. Source drift
   requires rebuilding the changed components privately, reviewing their
   complete provenance and updating the archive + locks together. It never
   uses `--allow-stale`.

Research builds have their own commit history. The assembler's new
`--use-research-prebuilts` mode verifies a dedicated Research receipt instead
of mislabelling the binary's source commit as the current public commit.
`package.json.native_build.source_commit` retains the actual Research
build provenance, `input_freshness.native` reports the validated public
source lock, while `package.json.source_commit` records the exact newly
assembled public checkout. The historic compiled bytes remain historic.

The three approved profile menu JARs are staged from
`modules/profiles/<profile>/hmi/prebuilt/MIBR-CarPlay.jar`. The separately
built Extender is extracted from the exact locked private reference package
and checked by `verify_p1_jar.py` (two Java class files, class major 46).

## Release operation and protected access

- The source lock job runs on public `main` without private credentials.
- The packaging job runs only on public `main`, when repository variable
  `MIBR_RESEARCH_PREBUILT_RELEASE_ENABLED=true`. The
  `multiprofile-private-build` environment supplies
  `MIBR_RESEARCH_READ_TOKEN`, a narrow, read-only GitHub token with **only**
  the protected source repository contents access. Configure its exact
  `owner/repo` identifier as protected secret `MIBR_RESEARCH_REPO`. The job reads the exact
  archived `MIBR-CarPlay-beta-3profile-r11b.zip` from commit
  `f733de43f58c71e4c7743dbda438b906959bce66`.
- The ZIP is reconstructed and both validators run; SHA-256 of the new ZIP
  is recorded. Java, QNX cross-compiler, licensed firmware and native
  navigation are **not** recompiled on that runner.
- **Publication is a separate decision.** The Research reference explicitly
  says PRIVATE-RESEARCH. The resulting combined ZIP must **not** be uploaded
  to public GitHub Actions unless its OEM/native/Extender distribution
  rights and contents have been independently approved. Accordingly the
  public Actions artifact upload requires a second protected repository
  variable: `MIBR_PUBLIC_BETA_ARTIFACT_APPROVED=true`. Until then, only the
  passing/failing validation logs are visible and the checked ZIP remains
  ephemeral inside the job.
- Even after upload approval, the workflow creates a 30-day Actions artifact
  only. It does **not** create a release, tag, or GitHub Package.

The original `tools/release/build_hmi_and_package.sh` is kept as an explicit
**private full-rebuild** path, not invoked by this workflow. Its J9,
QNX-target, Clang/LLD, iAP2 and FFmpeg requirements remain applicable when
source changes demand fresh binaries. The QNX cross-compiler image stored
in GHCR is a toolchain dependency, **not** a CarPlay application release,
and must not be deleted while other build workflows require its digest.

A successful host/package test is not on-unit validation. Škoda runtime
history and the SEAT untested status remain unchanged.

## HTML editor and packaged configuration

The deterministic ZIP includes all four current editor files from
`tools/menu-editor/`: `mibr-menu-editor.html`,
`function-catalog.json`, `standard-menu.txt` and
`MENU_FILE_FORMAT.md`. The standard menu is also packaged as
`common/menu/config/mibr-menu.conf` and installed at
`/mnt/app/root/mibr/config/menu/layout.conf`.

Each firmware profile supplies its own `profile.json`,
`hmi/oem-anchors.json`, integration transforms/`variants.list` and
`display/mibr-platform-defaults.conf` (from the platform-specific
`modules/navigation/source/platform-defaults/*.conf`).
`installer/config/profiles.list` is generated from the three exact
`profile.json` selector hashes. The package also includes a generated
`docs/configuration/DEFAULT_CONFIGURATION_MATRIX.md` based on
`settings/registry.json`; the registry is a *source* definition rather
than a separate user-editable on-unit configuration file.

The checked-in standard menu currently has `brand=skoda` even for a
multi-profile package. It is **not yet a separately generated SEAT
menu layout**; do not claim that all brand presentation details are
automatically adapted. The installer selects by the exact
`/ifs/lsd.jxe` SHA-256 and firmware-train cross-check, **not** VIN,
vehicle serial number or a guess from the brand. See
`config/README.md` and `modules/profiles/README.md`.

## Research-native provenance and migration notes

- Research r11b reference: private branch
  `the protected private source repository:build-output/165-beta-pkg`, immutable
  ZIP SHA-256 `f238143916a977ec24f1d6d9361194924b19852846c147d3f31c28c537f60248`.
  The original 292-file, three-profile package passed the package validator.
- Source snapshot for the reviewed public locks:
  `420fc46c63594a1a0274ddf6a3da7fb19c33b294`. This is a content reference,
  **not** a statement that Research J9/native binaries were built on that commit.
- The existing `MIBR_RELEASE_RUNNER_ENABLED` flag, self-hosted label
  `mibr-private-release-j9-qnx` and private filesystem path secrets no longer
  control the hosted prebuilt workflow; they belong exclusively to the
  preserved full-rebuild procedure.
- For Java modifications: rebuild the affected menu JAR in Research using
  the exact private J9/firmware classpath; review the new archive and update
  `MENU_SOURCE_LOCK.json` with matching source objects and hashes.
  For C/QNX/Navigation/Extender changes: rebuild in the private environment,
  produce new input and per-binary SHA-256 provenance, approve an immutable
  reference archive and regenerate `RESEARCH_PREBUILT_LOCK.json`. Never
  only adjust the lock fingerprints to silence a stale-source failure.
