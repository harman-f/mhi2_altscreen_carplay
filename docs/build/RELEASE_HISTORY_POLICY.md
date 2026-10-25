# Release history preservation

The legacy `mu1440-aid10-dev-current` workflow remains a **mutable developer
alias** at this stage, not a reproducible, immutable product version. It is
not the archived, private 1.3.2 kit and should never be called 1.3.2.

**Rules for all workflows:**

1. Never delete unrelated releases or tags as a side effect of publishing a
   different artifact. Old bytes, commit IDs and their associated evidence
   must remain accessible.
2. Immutable product releases must use unique versioned tags and artifact
   names, and refuse to replace an existing tag or release with different bytes.
3. A package's name alone does not establish its identity. The package
   manifest must bind a full source commit, target profile and its fingerprint,
   binary-set and package IDs, per-file SHA-256, config identities, build
   provenance and a clearly scoped qualification level.
4. Third-party/OEM/private firmware inputs and any private Unit exports are
   not public release artifacts, even if needed for a complete local build.
5. No vehicle installation or release publication is authorized by the
   legacy safety change.

This change removes only the historically destructive **global sweep**
from the existing `dev-current` workflow. Its own mutable alias update is
still legacy behavior and must be frozen or replaced under the separate
immutable product release architecture before production qualification.
