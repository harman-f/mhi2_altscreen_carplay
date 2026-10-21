# Contributing

Thanks for helping with MHI2 AltScreen CarPlay.

This is an experimental reverse-engineering and interoperability project. Contributions are most useful when they are **specific, reproducible and traceable to an exact platform/build**.

## Where to post

### Use an Issue for

- a reproducible bug;
- a concrete vehicle test result that requires action;
- a verified research finding with evidence;
- a regression;
- a clearly scoped implementation task.

### Use Discussions for

- questions;
- new ideas;
- architecture/design discussion;
- "does my platform look compatible?";
- early observations that are not yet reproducible;
- requests for support on a new Škoda/SEAT/VW MHI2 variant;
- coordination between testers.

Please do not use Issues as a general support forum or as an internal development/status tracker. Internal investigations, work assignments and experimental source are not public issue handoffs. Public source PRs should be standalone, buildable and provenance-cleared.

## Before opening a vehicle-test Issue

Include as much of the following as possible:

- vehicle brand/model/year;
- head-unit platform;
- exact firmware train/version;
- MU version if known;
- cluster type;
- how SSH access is obtained;
- whether the test was WLAN or USB-LAN;
- exact build/commit/artifact tested;
- expected result;
- observed result;
- relevant logs;
- whether the unit recovered to stock behavior.

Sanitize logs/screenshots before posting and follow the canonical redaction/privacy rules in [SECURITY.md](SECURITY.md).

## Help with physical input mapping

Our measured [MU1440 wheel and head-unit input map](docs/testing/MU1440_MFW_RAW_KEY_MAPPING.md) separates physical observation from symbolic OEM constants. Compatible-platform contributions for unassigned VIEW/Assist, fitted head-unit hardkeys and rotary inputs are welcome. Record the exact firmware/cluster, the physical control and its stock effect, and only **sanitized** observed `KBD/KEY/KST` or `updateEncoder2` tuples. No VIN, original firmware, private trace/video or unsafe remapping is needed. Missing `HK` text may simply indicate a different OEM input consumer.

## Evidence levels

Please distinguish these explicitly:

- **Observed on vehicle** — directly reproduced on hardware;
- **Binary-confirmed** — supported by disassembly/decompilation/string/xref evidence;
- **Build-confirmed** — source/toolchain compiles and the output is verified;
- **Hypothesis** — plausible but not yet proven;
- **Historical/prior art** — observed in another implementation or source.

Do not promote a hypothesis to fact merely because multiple implementations appear similar.

## Mandatory QNX target-script gate (MMX and RCC)

Before adding or handing over any on-unit `.sh`/`.ksh` (including an ad-hoc
private diagnosis ZIP), read [root AGENTS.md](AGENTS.md) and the
[exact-target QNX compatibility document](docs/testing/MU1440_QNX_SHELL_COMPATIBILITY.md).
Its vehicle-proven absence of external `printf` is an explicit prohibition; host Linux
mock/syntax tests cannot establish target command availability. Execute
`python3 tools/check_mu1440_target_shell.py --self-test --check <each-target-script>`
on **every** extracted target file before delivery; inventory all commands/options
and validate unknown RCC and MMX capabilities independently. Keep original error logs;
do not publish a target-tested claim before a real-unit run. Existing repository CI
cannot see private ZIPs; this explicit local gate closes that coverage gap.

## Pull Requests

A PR should explain:

1. what problem it solves;
2. which platform/build it targets;
3. whether it changes runtime behavior;
4. how it was built;
5. how it was tested;
6. how stock/recovery behavior was verified;
7. whether it adds any third-party material.

Prefer small, reviewable changes over large opaque drops.

### Code and build artifacts

For project-owned code, prefer:

- source code;
- reproducible build scripts;
- pinned tool versions/commits;
- SHA-256 hashes for generated artifacts;
- unstripped/debuggable output where practical;
- a short provenance note.

Generated binaries without source/build provenance may be rejected.

## Third-party and proprietary inputs

Do **not** submit full OEM firmware images, Apple system binaries, commercial proprietary packages or material you do not have the right to redistribute.

It is normally better to submit:

- exact filename/path;
- firmware/build identity;
- SHA-256;
- extraction/reproduction instructions;
- documented observations;
- small legally permissible metadata/patch information.

If a finding originated from leaked or commercially distributed software, describe it as **comparative research/prior art** and identify the source as precisely as possible without presenting that code as ours.

## Safety / recovery

Vehicle-side changes should be bounded and reversible whenever possible.

For experimental runtime controls:

- define the stock state;
- define the modified state;
- define the recovery path;
- avoid persistence unless persistence is part of the test;
- capture logs before and after;
- state whether a reboot returns to stock behavior.

Never encourage someone to run a package whose target build has not been checked.

## Style

- English is preferred for repository documentation and code comments.
- Use exact component/class/function names where known.
- Prefer ASCII diagrams for architecture/state-machine documentation when they improve clarity.
- Keep source observations separate from interpretation.
- Add dates/build identifiers to time-sensitive reverse-engineering notes.

## License

By contributing original project code or documentation, you agree that it may be distributed under **GPL-3.0-or-later**, unless a file or contribution explicitly and compatibly states otherwise.

Third-party code retains its original license and attribution requirements.
