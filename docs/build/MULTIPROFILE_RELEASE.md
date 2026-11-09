# Three-profile beta package build

The beta package workflow `.github/workflows/multiprofile-beta-release.yml`
assembles the current `main` revision on a dedicated, protected Linux runner.
It does **not** run for pull requests and does **not** publish a GitHub Release.
Only final ZIP, SHA-256 and menu artifacts are uploaded as 30-day Actions artifacts.
Its main-push trigger remains disabled until repository variable
`MIBR_RELEASE_RUNNER_ENABLED=true`.

## Two different build inputs

- **QNX cross-compiler image (GHCR):** `ghcr.io/harman-f/mhi2-qnx65-armv7`
  is a host-side Docker build environment (GCC 4.9.4 / QNX 6.5 / ARMv7),
  **not a CarPlay application release**. The immutable digest in
  `tools/qnx65-image.lock` is required by existing native CI and the package
  builder. Do not delete it while this lockfile references the image.
- **OEM/J9 menu classes:** The three owner-approved, profile-specific
  `MIBR-CarPlay.jar` files are checked into
  `modules/profiles/<id>/hmi/prebuilt/`. They are the default inputs
  (`MIBR_MENU_JAR_MODE=prebuilt`); they are **not** rebuilt for every
  ordinary package run. Each must have the pinned SHA-256 and class major 46.
  `tools/release/stage_prebuilt_menu.py` rejects reuse when any shared
  Java/menu, exact profile HMI/API or settings-registry input differs from
  the reviewed public source baseline
  `420fc46c63594a1a0274ddf6a3da7fb19c33b294`.
  It creates the `hmi/SOURCE_COMMIT.txt` receipt required by the assembler.

When those sources change, build the affected profile JARs **outside the public
CI**, against the exact IBM J9 toolchain, exact profile API `lsd.jar` and
private OEM source inputs. The old JARs are then **stale**: do not bump the
baseline alone. Independently check the new JAR contents/class versions,
update the three pinned SHA-256 values and source-baseline provenance after
review, and only then enable package assembly again. The optional
`MIBR_MENU_JAR_MODE=rebuild` can still rebuild all three profile JARs
on the secured runner if it has every input; that mode writes the exact
current source commit receipt.

**Remaining private build blockers:** The current script still builds the
`MIBR-Extender-P1-BootProbe.jar` with J9 and the matching Škoda API;
it also compiles navigation components using a private QNX target sysroot,
exact iAP2 library and pinned Clang/LLD/FFmpeg. Therefore adopting prebuilt
profile menu JARs **does not eliminate the dedicated runner** or make a full
package runnable on GitHub-hosted CI yet. The extender/navigation artifacts
need their own reviewed, source-fresh prebuilt contract before they could
be reused instead. Never substitute arbitrary or stale binaries.

The QNX host builds use the checked-in immutable image digest. All native
output, extender, prebuilt menu JARs and final ZIP must pass build provenance,
freshness and package validation. Host success is not vehicle acceptance;
Škoda's historical installed menu evidence does not qualify newly compiled
native outputs or the two SEAT targets.

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

## Reference comparison

The beta.11 r11b archive was reconstructed byte-for-byte from its documented
assembler inputs; its complete 292-file, three-profile ZIP also passed the
current package validator. The later merged installer entrypoints and runtime
scripts matched the reference package; selected configuration comments and host
test files differ. Recompiling the three menu JARs with the documented J9 and
profile API inputs produced the same file and class bytes as the reference JARs;
JAR archive hashes changed because packaging metadata differs. A subsequent
native rebuild produced both matching and differing binary hashes, so it must
be treated as a new build rather than silently called the vehicle-tested bytes.

## Runner provisioning

The private J9 inputs remain necessary **today** for the separately built
extender even when the three profile menu JARs are reused. Only the
`rebuild` mode recompiles all three menu JARs. The existing runner and
protected environment must not be opened to untrusted branches.



Provision a dedicated Linux x64 runner with label `mibr-private-release-j9-qnx`
and restrict it to this repository. Never use this runner for untrusted pull
requests. Configure the protected environment `multiprofile-private-build` with
these secrets (paths refer only to that runner):

- `MIBR_PRIVATE_J9_HOME`: IBM J9 SDK home. Set `MIBR_J9_JAVAC_SHA256` and
  `MIBR_J9_JAR_SHA256` to the SHA-256 of its `bin/javac` and `bin/jar`.
- `MIBR_PRIVATE_INPUT_ROOT`: private directory with `<profile>/lsd.jar`,
  `<profile>/Activator.java` and `<profile>/WidgetFactoryImpl.java` for each
  of the three profile IDs. Supply its `SHA256SUMS` and pin the SHA-256 of that
  file in `MIBR_PRIVATE_INPUT_MANIFEST_SHA256`. Generate the manifest with
  `sha256sum <profile>/<file> ... > SHA256SUMS` from the input root.
- `MIBR_QNX_TARGET`: the QNX 6.5 `target/qnx6` sysroot. Provision
  `MIBR_TARGET_SHA256SUMS` in that directory and pin its SHA-256 as
  `MIBR_QNX_TARGET_MANIFEST_SHA256`.
- `MIBR_IAP2_LIB`: the exact private MU1440 iAP2 library required by the
  navigation build; its expected hash is checked by that build script.
- `MIBR_CLANG`, `MIBR_LLD`, `MIBR_FFMPEG`: executable paths, with SHA-256
  pins `MIBR_CLANG_SHA256`, `MIBR_LLD_SHA256` and `MIBR_FFMPEG_SHA256`.
  FFmpeg must include libx264; Docker must be available to the runner. When the
  runner is not root, it also needs non-interactive sudo for restoring build-output
  ownership after the Docker builds.

The workflow reads the QNX compiler image from the repository lock and logs in
to GHCR with its read-only job token. Provisioning these dependencies and runner
registration is an explicit operational step; simply merging the workflow does
not make an unavailable runner start. Keep private input files, generated OEM
sources and the J9 SDK out of repository commits and uploaded artifacts.
