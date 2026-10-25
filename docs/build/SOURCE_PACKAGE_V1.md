# Public source package v1

`tools/package_source_v1.py` creates a deterministic, source-only snapshot of the public repository at a selected Git commit. The exact per-file scope is committed in `tools/source-package-v1.paths`; the tool validates each entry against a narrower set of permitted public product paths and text/source types. It includes the selected public source, build/test scripts and technical documentation; it excludes generated binaries, release artifacts, firmware/OEM files, private material and research handoffs. The allowlist is read from the selected commit alongside every packaged file, so working-tree changes cannot silently alter the package.

## Output and provenance

The output path is outside the checkout, and the tool writes three sibling files:

- `source.tar.gz`: deterministic archive of the allowlisted public source files;
- `source.tar.gz.provenance.json`: repository, evaluated commit/tree, workflow context and per-file size/SHA-256, plus the archive SHA-256;
- `source.tar.gz.sha256`: checksums for the archive and provenance document.

The PR workflow runs the focused package tests and target-shell compatibility gate before creating the archive. Relevant application-source changes also retain the existing host, QNX and publication-integrity workflows. The `PR source gate` check is intended to be stable for every pull request to `develop`; a skipped component build is not represented as a passing build.

GitHub Actions stores this output only as a three-day workflow artifact. The workflow does not create a GitHub Release, tag, installable kit, or commit generated files to the repository. The source archive is not a deployment package and does not establish QNX build, Unit or vehicle qualification.

## Reproduce locally

From a clean checkout, run:

```sh
python3 -B -m unittest discover -s tests -p 'test_package_source_v1.py' -v
python3 -B tools/package_source_v1.py \
  --repo . \
  --ref HEAD \
  --output "${TMPDIR:-/tmp}/mhi2-source-package.tar.gz"
```

The source package records the exact public Git tree and allowlist hash used. Do not add generated binaries or private/OEM inputs; expand the file list only through a reviewed, path-specific source change and corresponding tests.
