# SEAT/CUPRA MU1409 — local development and analysis environment

**Contributor setup guide · 23 October 2026 · macOS host / QNX 6.5 ARMv7 target**

This is the **practical workstation setup** for the proposed [SEAT/CUPRA collaboration](SEAT_CUPRA_MU1409_COLLABORATION.md). It prepares a local environment to compare an exact `MHI2_ER_SEG11_P4708_1` firmware against the known MU1447/MU1440 references, compile project-authored native/Java modules, and later develop a SEAT-specific OEM HOME/Settings adapter.

**This is an off-car guide.** The [MU1440 source baseline](../build/MU1440_R50_SOURCE.md) supplies the actual menu adapter, controller and native modules for source development. Its OEM inputs and installed support-file gaps are documented individually. Finishing setup does not establish safe installation or MU1409 compatibility. Never replace a working omonob installation simply because a cross-build passes.

## 1. End state / first milestone

After the setup, the contributor should be able to:

- record the exact Mac architecture, build tools and selected source commits;
- run our firmware toolkit's host tests and **plan** an extraction without modifying the original archive;
- extract MMX, RCC and Java from an authorised original P4708_1 firmware using the dependencies required by its actual container types;
- validate and convert its `lsd.jxe` into a class-indexed JAR using a pinned external converter, and inspect selected classes without placing OEM code in public Git;
- inspect ARM/QNX ELF files and selected functions with a recorded Ghidra configuration;
- reproduce at least one **host-only QNX ARMv7 build and ELF inspection** using the public pinned CI toolchain path;
- create a private, redacted compatibility report for review **before** any proposed vehicle write.

Do not begin with OEM HMI patching. The first target-specific output is a small compatibility matrix for the video/control interfaces. A separate second phase studies the original SEAT menu and develops a no-write Java UI proof.

## 2. Host choice: Mac + isolated Linux build environment

A Mac (Intel or Apple Silicon) is suitable for editing, Git, Python, PowerShell 7, Java tools and Ghidra. The reference QNX cross-toolchain was built and exercised under **`linux/amd64`**. On Apple Silicon, use Docker Desktop with working amd64 emulation, or a separate x86_64 Linux VM/builder if emulation or legacy dependencies fail. Do not silently substitute the macOS Clang compiler or a modern Linux ARM toolchain: the target ABI is **QNX Neutrino 6.5 ARMv7 little-endian**, not macOS or Linux.

The extraction dependencies are also not all Python-only. A native macOS extraction is acceptable **only if** the actual qnxmount/dumpifs/LZO tools work and the resulting manifest validates. Otherwise keep the Mac as the front end and perform extraction within an explicitly provisioned Linux analysis environment. Do not call a partial export a completed firmware extraction.

### Suggested macOS prerequisites

Install [Homebrew](https://brew.sh/) if desired, then in a Mac terminal:

```sh
brew install git python@3.12 p7zip powershell
git --version
python3.12 --version
7z
pwsh -NoProfile -Command '$PSVersionTable.PSVersion.ToString()'
uname -m
```

The bare `7z` command above may print usage and exit nonzero; its purpose is to confirm the CLI exists. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) separately and **start its engine**. Then check:

```sh
docker version
docker info
docker buildx version
docker run --rm --platform linux/amd64 alpine uname -m
```

The final command should report `x86_64`. If the container fails to start, resolve the host/virtualisation issue first instead of debugging the QNX compiler.

Install a supported JDK for the chosen [Ghidra](https://github.com/NationalSecurityAgency/ghidra) release; keep **JDK 8 separately available if a legacy Java/J9 module's documented build requires it**. Install a Java decompiler such as [CFR](https://github.com/leibnitz27/cfr). Record all versions and binary hashes where available. The converted `lsd.jxe` classes are not compiled using the Mac's default modern target level: the actual on-unit IBM J9 classfile/API constraints remain authoritative.

## 3. Keep source, proprietary inputs and outputs separate

One possible layout (names can differ):

```sh
export LAB="$HOME/seat-mu1409-lab"
mkdir -p "$LAB/src" "$LAB/private/firmware" "$LAB/private/extractions"
mkdir -p "$LAB/private/java" "$LAB/private/ghidra" "$LAB/private/reports"
mkdir -p "$LAB/build" "$LAB/tools-cache"
git clone https://github.com/harman-f/mhi2_altscreen_carplay.git "$LAB/src/altscreen"
git clone https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit.git "$LAB/src/firmware-toolkit"
git -C "$LAB/src/altscreen" rev-parse HEAD
git -C "$LAB/src/firmware-toolkit" rev-parse HEAD
```

| Directory | Intended contents | Publication |
| --- | --- | --- |
| `src/altscreen` | Published project source and documentation, pinned to an agreed commit for comparisons | Normal clean Git checkout |
| `src/firmware-toolkit` | Public host extraction/conversion wrappers | Normal clean Git checkout |
| `private/firmware` | Original authorised firmware update package(s) | **Never commit or upload publicly** |
| `private/extractions` | Manifest and recovered MMX/RCC/Java filesystem trees | **Never commit or upload publicly** |
| `private/java`, `private/ghidra` | Reconstructed JAR/class content and native reverse-engineering projects | **Never commit or upload publicly** |
| `private/reports` | Complete source/component manifests and raw local evidence | Publish only separately reviewed/redacted summaries |
| `build`, `tools-cache` | Reproducible output and external pinned tooling | Keep generated binaries/tool licenses separate from source |

Use a private local feature branch for project changes and record its base SHA. Do not merge or overwrite the active public development branches. Maintain only sanitised, independently authored code/docs in the public repository.

## 4. Install and validate the host firmware toolkit

```sh
cd "$LAB/src/firmware-toolkit"
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q tools tests
python -m unittest discover -s tests -v
```

`requirements.txt` intentionally does **not** install every external extractor. For actual MMX/RCC filesystem materialisation, follow the toolkit's [dependencies](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/DEPENDENCIES.md) and [tool guide](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/docs/TOOL_GUIDE.md). In particular, qnxmount, dumpifs and LZO support may be needed depending on the selected components. Keep their source, versions and availability documented; do not bypass a missing dependency or accept silently partial files.

A successful toolkit unit-test run validates the host code against its test fixtures. It is **not** proof that a newly supplied firmware has extracted completely.

## 5. Intake and extract the exact P4708_1 firmware

Use an original update archive that the owner is entitled to analyse. Do not download an arbitrary same-MU package and relabel it P4708_1. Keep P4708, P4708_1, P4709/MU1447 and P4526/MU1440 as separate baselines unless exact component hashes establish a match.

Example once the original file has been placed in the private directory:

```sh
export FW="$LAB/private/firmware/original-P4708_1-update.7z"
shasum -a 256 "$FW"
cd "$LAB/src/firmware-toolkit"
. .venv/bin/activate
python tools/extract_firmware.py --source "$FW" --plan
```

The filename above is illustrative; replace it with the **actual** downloaded filename and record its SHA-256, bytes, source identity and exact train. Review the plan and prerequisites, then use a **new, nonexistent** output directory:

```sh
python tools/extract_firmware.py \
  --source "$FW" \
  --output "$LAB/private/extractions/P4708_1-run01" \
  --component mmx --component rcc --component java
```

If an authoritative source hash is available, also use the extractor's `--expected-sha256`. Inspect `extraction_manifest.json`, component/member hashes, skipped/opaque classifications and any freeze/partial report. **Do not delete failed partial state and then report success.** Rerun into a different fresh directory after resolving the root cause.

Locate the extracted `lsd.jxe`, `libairplay.so`, `dio_manager`, `displaymanager`, relevant startup scripts and production display/MOST configuration **from the verified manifest/tree**; do not invent a path because it exists on the Škoda reference.

## 6. Java / IBM J9 analysis

The firmware toolkit exports the source `lsd.jxe`; conversion to JAR is a separate step. The project wrapper obtains a **pinned external** `luka-dev/jxe2jar` revision:

`9eeb45bbf14bf8afe3452c7be96a4d1f0206a286`.

On macOS, its default `LOCALAPPDATA` cache location is Windows-oriented, so **pass `-ToolCacheRoot` explicitly**. Set `JXE` to the real extracted file discovered in step 5:

```sh
export JXE="/absolute/path/to/the/extracted/lsd.jxe"
pwsh -NoProfile -File "$LAB/src/firmware-toolkit/tools/jxe2jar/convert-jxe.ps1" \
  -InputJxe "$JXE" \
  -OutputDirectory "$LAB/private/java/P4708_1-run01" \
  -Python python3.12 \
  -ToolCacheRoot "$LAB/tools-cache/jxe2jar-9eeb45"
```

The output directory must not pre-exist. Check the generated `conversion-manifest.json` (source hash, exact converter commit, output JAR hash and class count), then make a class/path manifest. Decompile **selected** target classes with a recorded CFR version; compare class *bytes* and method descriptors first, and use decompiled Java to explain differences rather than claiming decompiler text equality proves binary identity.

Prioritise:

1. stock navigation/CarPlay coexistence classes and currently installed `NavActiveIgnore.jar` / other bootstrap overrides;
2. stock HOME/Settings view, ViewHandler, widget/resource and Java/DSI dependencies for the later SEAT HMI adapter;
3. selected `mostkombi` and display/rate-control boundaries needed to understand the video route.

Compare MU1409 with the project's existing MU1447 and MU1440 **recorded baselines**. The reported historical 26,202 identical common classes are a useful hypothesis; remeasure against this exact P4708_1 source. Never publish extracted OEM classes or original decompiled implementation bodies.

## 7. Native ELF inspection and Ghidra

On the private original components, collect hashes, file sizes, ELF machine/ABI information, `DT_NEEDED`, relevant imports/exports and executable-code comparisons. Use appropriate host `file`/`readelf` or the pinned cross-toolchain equivalents (a Mac host may not ship GNU `readelf` by default).

Use a separate private Ghidra project for each exact firmware baseline and record Ghidra version, loader language, image base, analysis options, sample hash and function addresses. The most valuable initial comparison is **not** an indiscriminate full decompile:

| Boundary | Question to answer |
| --- | --- |
| `libairplay.so` | Same Type-111/GEN2 hook functions, object/session offsets and calling conventions as the MU1440/MU1447 reference? |
| `dio_manager` / original session owner | Same integration and loader expectations; how does the existing omonob wrapper coexist with stock? |
| DisplayManager / MOST | What endpoint, original owner, open/write behaviour and TS framing actually apply? |
| `smartphone_integrator`, relevant config/startup | Any source/session/config or classpath change that affects our adapter? |
| SEAT Java/J9 HMI | Which stock HOME/Settings entry, widgets, DSI bindings and menu geometry differ from Škoda? |

A matching train label, file length or package architecture alone is not an ABI check. Classify every comparison as exact-byte match, same interface with differences, new target adapter required, or unresolved.

## 8. Reproduce the QNX 6.5 ARMv7 build environment

For the first native build, follow the **exact checked-in [direct-ts-remux CI workflow](../../.github/workflows/build-direct-ts-remux.yml)** as the canonical reference, including its dependency pin and current legacy-Debian APT bootstrap adjustment.

It currently identifies:

| Item | Pinned reference |
| --- | --- |
| Toolchain source | [luka-dev/qnx65-armv7-toolchain](https://github.com/luka-dev/qnx65-armv7-toolchain) |
| CI toolchain commit | `56a66557245af14077678cd28a83ce3a337d9e2d` |
| Original Dockerfile SHA-256 | `9a867a7ae70f2c0222a241b80232856526ccec0db2cfe013f8991ca31c74bcb1` |
| Build container target | `--platform=linux/amd64 --target base-env --build-arg BASE=base-4.9` |
| Compiler family | `arm-unknown-nto-qnx6.5.0eabi-gcc`, GCC 4.9.4 |
| Reference remux dependency | FFmpeg 6.1.5, verified by the checked-in build script |

To obtain and inspect the exact toolchain **without yet compiling**:

```sh
git clone https://github.com/luka-dev/qnx65-armv7-toolchain.git "$LAB/src/qnx65-toolchain"
git -C "$LAB/src/qnx65-toolchain" checkout 56a66557245af14077678cd28a83ce3a337d9e2d
shasum -a 256 "$LAB/src/qnx65-toolchain/Dockerfile"
```

Compare the original Dockerfile SHA with the table before applying the workflow's **specific** APT snapshot fix. Follow that workflow's build commands; do not guess a different base image, silently move the source pin or distribute a proprietary toolchain image. The firmware toolkit documents a **different reviewed HEAD** for research, which must not be confused with the exact remux CI build pin.

Once its image has been built with the workflow, perform a compiler/ABI smoke check in `linux/amd64` and reproduce the project build using [`tools/build_direct_ts_remux.sh`](../../tools/build_direct_ts_remux.sh). The script first performs a minimal QNX target link, obtains/hash-checks FFmpeg and emits an **unstripped** ARM executable. Inspect the ELF header, dynamic dependencies, symbols and SHA-256; compare with the CI artifact. Compilation success on the Mac/host or within Docker **never** equals a live QNX/vehicle pass.

For later Java HMI modules, record the actual target IBM J9 API stubs, build toolchain and classfile major version; keep compilation stubs out of the runtime JAR. Do not pretend that the published, independent experimental menu-model source is already a complete installable SEAT OEM view.

## 9. Keep Codex local, scoped and auditable

Codex can help organise the cloned source, analyse approved offline binaries, compare class manifests and run host tests. Start it in the **clean public source checkout**, not at a parent path that indiscriminately includes original firmware, credentials and private evidence. Offer narrow, explicitly approved file access when private samples are needed; do not paste secrets into prompts, source, issue comments or logs.

The contributor already has WLAN SSH. Reuse only their authorised local SSH/Keychain/agent setup. A cloud agent may **not** have access to the vehicle's private LAN; never interpret that as a successful remote test. **No automatic SSH writes, remounts, process kills, installer execution, reboot, stock-file replacement or firmware flashing.** Each live step requires a separate owner decision and a verified recovery path.

The reference unit's exact [QNX shell compatibility contract](../testing/MU1440_QNX_SHELL_COMPATIBILITY.md) documents missing/unreliable commands and the MMX/RCC split; these details must be rechecked on SEAT. Before proposing **any** target shell script, inventory every command, option and read path and run the repository's static gate against that script:

```sh
cd "$LAB/src/altscreen"
python3 tools/check_mu1440_target_shell.py --self-test --check /path/to/a/proposed-target-script.sh
```

The checker is necessary, not sufficient and does not certify the SEAT runtime. Keep the first device phase bounded/read-only and separate MMX from RCC. Do not use an installer to discover a filesystem layout.

## 10. Deliverables and stop/go gates

| Gate | Required local proof | Next step |
| --- | --- | --- |
| E0 — host ready | Mac, Docker/amd64, Python, Git, Java and analysis tools listed with exact versions; source commits recorded | Run firmware toolkit tests |
| E1 — firmware intact | Exact P4708_1 original identity/hash, successful extraction manifest (or explicit PARTIAL/blocker) | Construct component/class manifests |
| E2 — comparator ready | Exact binary/class hashes and focused MU1409↔MU1447↔MU1440 compatibility notes; no proprietary files in public Git | Agree on target build profile |
| E3 — build ready | Pinned QNX image, successful host link/remux and ELF/debug/symbol/dependency inspection; Java target build independently checked where relevant | Maintainer review of target-specific source |
| E4 — vehicle preflight | Owner-approved read-only inventory, stock baseline, active third-party/JAR coexistence, backups and feasible restoration independently verified | **Separate** authorisation for any bounded parked vehicle test |
| E5 — WP1 qualified | Exact target video, owner and reversible STOCK/DIRECT results | Begin SEAT UI-only proof |
| E6 — WP2 qualified | OEM menu appearance, storage, live application and actual ACTIVE/visible effect individually observed, factory interaction preserved | Consider optional extras |

The **first useful handoff** is only E0–E2: a concise redacted environment/firmware compatibility summary, reproducible tool versions and a list of exact questions we can address together. The contributor does not need to reverse-engineer every firmware subsystem or dismantle a working car installation before we can review it.

## Reference pages

- [Joint SEAT/CUPRA port plan](SEAT_CUPRA_MU1409_COLLABORATION.md)
- [Current source/release coverage](../status/PUBLISHED_SOURCE_COVERAGE.md) and [evidence status](../status/INTEGRATION_STATUS_2026-10-21.md)
- [Public QNX build workflow](../../.github/workflows/build-direct-ts-remux.yml) and [native architecture](../architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md)
- [Firmware toolkit](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit), [tool guide](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/docs/TOOL_GUIDE.md) and [dependency list](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/DEPENDENCIES.md)
- [Pinned JXE converter wrapper](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/tree/main/tools/jxe2jar)
- [Community MU1409/790 report](https://github.com/harman-f/mhi2_altscreen_carplay/issues/47)
