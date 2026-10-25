# MIBR CarPlay version, target and configuration identity (v1)

Status: **developer source implementation; NOT an installable 1.3.2 release and NOT vehicle-qualified.**

## Stable filenames and four independent identities

Never put a product version in existing MU1440 on-unit filenames: `parity-session`,
`libaltscreen111.so`, `mibr-v3-service`, the HMI JAR and existing startup paths
retain their binding names. Installed compatibility remains determined by
firmware fingerprints and exact bytes.

1. `product_version`: semantic product release, e.g. `1.3.3-rc.1`.
2. `source_commit`: immutable full Git commit.
3. `binary_set_id`: digest of the **actual** released binary manifest, not a
   version label. Remains `null` in source-only output.
4. `package_id`: digest of the **actual** assembled package. Remains `null`
   in source-only output. An installed state is a separate transaction receipt,
   plus checked on-disk/runtime evidence.

Do not republish the historical Kit 1.3.2 with different owner bytes or new
embedded sections under its old identity. Optional future
`mibr_build_identity.c` uses a GCC retained `.mibr.ident` ELF section;
the bytes change when linked, so opt-in only for new versioned candidate
binaries, with QNX readelf/strip/reproducibility tests before deployment.
The current pinned native build recipes and their hash tests are unchanged.

## Target and config scopes

Every target has `schema=1`, an immutable `id`, `brand` of exactly
`GENERIC`, `VW`, `SKODA`, or `SEAT`, and explicit qualification state.
`GENERIC` must not imply a qualified vehicle/firmware. The only brand-specific
reference target included here is the known Škoda MU1440/P4526/AID10
source-reference profile. A named VW or SEAT vehicle profile must carry its own
reviewed firmware/cluster fingerprints and cannot inherit MU1440 eligibility.

Project configuration metadata uses a **separate index**, not additional lines
in OEM or parser-sensitive configuration files. Each entry binds relative
path, schema version, brand, size and SHA-256 of the unchanged file bytes.
`GENERIC` configs may be shared with a matching brand; a VW/SEAT/SKODA config
may never be silently applied to a different brand. No OEM config bytes are
redistributed.

Run from the repository root (output directory must not already exist):

```sh
python3 tools/mibr_build_identity.py \
  --product-version 1.3.3-rc.1 \
  --source-commit "$(git rev-parse HEAD)" \
  --target target-profiles/skoda-mu1440-p4526-aid10.json \
  --config-index config-identity.json \
  --component mibr-v3-service \
  --out /tmp/mibr-identity-new
```

For a truly generic **unqualified** build, use
`target-profiles/generic.json` and `config-identity-generic.json`.
The latter excludes the Škoda-specific OEM HMI overlay.

Outputs: deterministic `build-identity.json` with config file hashes,
Java 1.2-compatible `build-version.properties` as a future installer input,
and (when `--component` is set) an opt-in ELF section source. Generated
`build-version.properties` is SOURCE_ONLY, and is **not** an installed
receipt. Future public installer integration must verify package/binary-set
digests and atomically write the separate on-unit
`/mnt/app/root/mibr-kit/installed-version.properties` only after validated
installation, with ownership-qualified restore. HMI never changes a setting,
starts a new service, or accepts unverified input.

## HMI

The new read-only **Erweitert → Version** page presents product version,
brand/target, source revision and each config's version + Generic/brand scope,
or a clear missing/invalid-metadata status. It is not one of the canonical
48 settings, does not change the native UI projection or MIBR/3 protocol, and
does not prove that a file is the one currently loaded into process memory.

## Not in this PR

Full 1.3.2 clone, embedded IDs for all production binaries, versioned
immutable ZIP release, Java/J9 OEM build, vehicle installer transaction,
effective runtime/hash verification, generic brand cross-target deployment,
and any unit access remain separate gates. Preserve the existing 1.3.2
source/binary reference and do not merge before PR #73's source-allowlist
is extended and both reviews pass.
