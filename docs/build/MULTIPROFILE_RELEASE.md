# Three-profile beta package build

The release workflow `.github/workflows/multiprofile-beta-release.yml` builds the
three-profile ZIP from the current main revision on a dedicated, protected Linux
runner. It must not run on pull requests or untrusted branches. Both the pinned
QNX 6.5 compiler image and locally provisioned private build inputs are required.
It compiles the profile-specific menu JARs with the IBM J9 SDK and builds the
native components. It then runs the modular assembler and validates the actual
ZIP. The job uploads the ZIP, its SHA-256 file and the three resulting menu JARs;
no original OEM build inputs or J9 SDK are uploaded. This is a beta build, not
proof of vehicle acceptance.

The runner needs the private profile `lsd.jar`, `Activator.java` and
`WidgetFactoryImpl.java` inputs, an IBM J9 SDK, a QNX target sysroot, the
hash-pinned iAP2 library, Clang/LLD and FFmpeg with libx264. The workflow lists
all required environment secrets and tool hashes; the build script checks them
before compiling. The three original OEM input sets and the toolchain must be
provisioned outside the public repository. Set the repository variable
`MIBR_RELEASE_RUNNER_ENABLED` to `true` only when the dedicated runner and
protected environment are configured. The workflow is triggered by a main push
or manually and does not push commits to main or publish a GitHub Release.

The owner-authorized checked-in menu JARs are reference artifacts, not hidden
build inputs: the workflow compiles the JARs again. The assembler excludes the
reference copies from the ZIP so there is one installable JAR per profile.
SHA-256 and the tested-vehicle scope of the reference files are documented in
[MENU_PREBUILT_PROVENANCE.md](../../modules/profiles/MENU_PREBUILT_PROVENANCE.md).

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
