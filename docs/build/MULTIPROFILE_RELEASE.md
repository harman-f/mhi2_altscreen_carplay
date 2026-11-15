# Three-profile beta release ownership

The private HARMAN-F build repository is the sole active producer of
three-profile release packages. It obtains the approved Java menu inputs from
its private release storage, verifies their SHA-256 fingerprints, and assembles
the package. The public product repository does not download private Research
archives, stage checked-in menu binaries, assemble beta release packages, or
publish release artifacts.

The public `publication-audit` workflow remains a source and publication gate.
It runs without private credentials and checks the public repository's
publication rules, profile definitions, and source freshness locks. The menu
source lock covers the menu Java tree, settings registry, profile metadata,
and every tracked profile HMI source/configuration file except exactly
`modules/profiles/<profile>/hmi/prebuilt/MIBR-CarPlay.jar`. The verifier
requires the three canonical profile roots and the complete tracked file set;
added, removed, changed, or uncommitted source files fail closed. The excluded
JAR path is not a source input and is not present in the public tree.

Public source changes that alter Java menu behavior, profile HMI integration,
settings, or the registry require the private build owner to rebuild and
review the corresponding private menu inputs and update the independently
maintained private content lock. Public lock changes alone do not authorize a
new binary or release.

The private package is not a vehicle approval. Existing vehicle test evidence
and compatibility limits are recorded in [current release status](../../release/CURRENT.md).
The QNX compiler image is a toolchain dependency used by source-build workflows;
it is not a CarPlay release artifact.

## Package contents and source boundaries

The modular package format remains defined by [PACKAGE_LAYOUT.md](PACKAGE_LAYOUT.md).
It includes the four current editor files from `tools/menu-editor/`, the
standard menu configuration, exact firmware-profile selectors, and a generated
configuration matrix from `settings/registry.json`.

Profile HMI source and OEM anchor metadata remain public source inputs. The
firmware-derived profile menu JARs, Extender binary, native outputs, licensed
firmware, and private toolchain inputs are supplied and verified by the private
release pipeline. They are not stored as active binary inputs in this public
repository.

## Privately staged legacy support JARs

The compiled `MIBR-NavIgnore.jar` and `MIBR-Most20FPS.jar` are staged by the private HARMAN-F builder from the verified `mibr-inputs-r11b` release package as `hmi/common/*.jar`. The modular assembler requires those staged files; it does not read the historical `artifacts/mu1440/*` copies as active release inputs. That historical tree is retained for earlier vehicle-test provenance and legacy tooling until separately reviewed. The full-source rebuild requires those same exact JARs as hash-pinned private support inputs, not silent reuse of public binary copies.
