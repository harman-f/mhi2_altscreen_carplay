# Release readiness, module ownership and target-shell safety

The canonical source of truth for build ownership is
[`modules/module-index.json`](../../modules/module-index.json). The workflow
[`release-mu1440-aid10.yml`](../../.github/workflows/release-mu1440-aid10.yml)
uses this structure for **pre-publication readiness**, not as a vehicle-ready
multi-profile release generator.

## Mandatory three-profile beta release inputs

`python3 tools/release/plan_multi_profile_beta.py --self-test --json-out beta-profile-plan.json` emits the *same* common beta inclusion for Škoda MU1440 and both SEAT firmware families. Java adapters are per-firmware repairable; code and registry remain shared. This is a real CI input for the future R3 packager, not yet an executable installation ZIP. Final vehicle acceptance is common beta testing, not an exclusion gate. Exact missing JXE hashes and compiled ABI-specific Java must still be present in the final installer. Never manufacture substitutes.

## Independent stages

1. **Impact plan (host):** `module_plan.py` compares the exact base/head Git
   paths and resolves reverse dependencies through the canonical index.
   For example, CarPlay can affect Broker, Menu and Navigation; Broker
   can affect Menu and Navigation. Unknown new module paths fail closed.
   Central settings/module-index changes invalidate the entire owner graph.
   Output is `mu1440-release-module-plan`, a JSON CI artifact, not an executable ZIP.
2. **Build and lineage:** the existing GEN2, MU1440 QNX, support-tool and
   module-lineage workflows retain their own QNX compile/receipt gates.
   The owner impact plan does not pretend to recompile, promote or qualify
   their binaries. Module binaries are not automatically substituted for
   pinned vehicle-evidenced binaries in the old installer.
3. **QNX shell compatibility:** `qnx_scripts.py --canonical` discovers
   `*.sh`/`*.ksh` from all indexed module runtime owners and shared
   deployment/diagnostic roots. After staging, the same checker runs against
   **every script in the exact assembled SD root**. This includes the outer
   installer, Auto-Direct, isoTX2, diagnostics and navigation scripts.
   The checker applies the [MU1440 QNX command contract](../../docs/testing/MU1440_QNX_SHELL_COMPATIBILITY.md)
   and `bash -n` for eligible .sh files as an additional host-only syntax
   check; neither operation is a successful QNX/MMX/RCC execution claim.
4. **Legacy archive integrity:** `audit_legacy.py` re-opens the finished ZIP
   and rejects path traversal, symlinks, duplicate members, unlisted content,
   missing scripts, payload drift and mismatched SHA-256 receipts. It checks
   pinned vehicle-media digests and current build-confirmed helper receipts.
   The old SD-root ZIP remains **CI-internal**, not downloadable as a release.
5. **Actual R3 publication boundary:** the R3 validator's self-test is not
   enough. The final assembled archive must contain the
   `MIBR-CarPlay/common/`, `profiles/`, `installer/`, `source/` inventories
   and the unique fail-closed firmware selectors required by
   [PACKAGE_LAYOUT.md](../../docs/build/PACKAGE_LAYOUT.md), and pass
   `python3 tools/validate_modular_package.py <final.zip>`. That archive
   does not yet exist in this public tree: the profile-specific Java/HMI,
   icons and integration inputs are not fully qualified. Publishing is
   intentionally **disabled**; no legacy R3 aliases, placeholder profiles,
   tag rewriting or automatic release deletion.

## Host commands

```bash
python3 tools/release/module_plan.py --self-test
python3 tools/release/module_plan.py --all
python3 tools/release/qnx_scripts.py --self-test --canonical
python3 tools/release/audit_legacy.py --self-test
tools/prepare_mu1440_sd.sh /tmp/mu1440-legacy-audit
python3 tools/release/qnx_scripts.py --package-root /tmp/mu1440-legacy-audit
```

The final archive integrity gate is invoked from CI **after ZIP creation**.
These commands are workstation/GitHub-Runner commands and are **not installed
or executed on the QNX unit**.

## QNX caveats that cannot be waived by green host CI

- Never use external `printf`, `sed`, `tr`, unbundled `sha256sum` or
  `tee`, or GNU-`date` assumptions in on-unit scripts. The known QNX
  shell/environment is not a generic GNU/Linux environment.
- Do not assume command/option behavior validated on MMX applies to RCC.
  Use verified absolute helper paths and documented mount/remount rules.
- `awk` is not banned, but the exact scripted program must have evidence.
  `grep 'A\\|B'` alternation is not portable. Dynamic command evaluation,
  boot-time side effects and device nodes require manual/vehicle review.
- A passing shell syntax check is necessary, not sufficient. A newly
  introduced target command/option is a dependency needing a separate
  vehicle/board-specific inventory and regression fixture.
- Do not start installation or create a release merely because the
  dependency plan and legacy compatibility checks are green.

## Future R3 implementation gate

Implement the real symmetrically inventoried profile tree and complete
source/build receipts. Only then connect a **separate publish job** requiring
successful final ZIP validation, exact source commit and binary SHA-256
provenance, relevant QNX regression and vehicle/profile authorization.
Release tags must be immutable and unrelated historical release assets preserved.
