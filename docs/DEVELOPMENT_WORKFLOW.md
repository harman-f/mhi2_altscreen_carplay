# Development workflow

This page says where work happens and what has to be true before a change moves on. It does not replace the [documentation policy](DOCUMENTATION_POLICY.md) or the [package contract](build/PACKAGE_LAYOUT.md).

## Three stages

| Stage | Where | What belongs there | Promise |
| --- | --- | --- | --- |
| Lab | private lab repository, branches `lab/<topic>` | protocol probes, wild tests, unit logs, photos, anything containing OEM material or vehicle data, build orders | none; every state is still committed and pushed |
| Development | this repository, `develop` | the reliable public intermediate state: cleared product code, tools and docs | always buildable, CI green |
| Release | this repository, `main` + tag `v<version>` | packages accepted in a vehicle | built from exactly the tagged commit |

## Working on develop

1. Branch `work/develop-<topic>` from `develop`. One topic per branch and per pull request; no stacked draft chains.
2. Open the pull request against `develop` early. It is squash-merged when:
   - host tests, QNX builds and the publication audit are green;
   - new behaviour is off by default or behind a marker until it is confirmed in a vehicle;
   - documentation is updated as the [documentation policy](DOCUMENTATION_POLICY.md) requires.
3. A change that alters menu or native sources keeps `MENU_SOURCE_LOCK` / `RESEARCH_PREBUILT_LOCK` stale until binaries built from it are recorded. Such a pull request merges after the package built from it has been accepted in the vehicle, with the lock updated to those binaries.
4. Delete the work branch after the merge.

## From lab to develop

Private test deployments may be built from the lab; a unit test does not need a public commit. A change moves to `develop` only as a publication candidate as defined in [AGENTS.md](../AGENTS.md): an exact change set with origin/license and disclosure review, build evidence with the right evidence class, then CI. Encapsulation, a default-off guard and tests are necessary but not sufficient, and vehicle acceptance does not replace the publication review. Probes, captures, OEM-derived material, handoffs and experiment diaries never move. Once a candidate is cleared and accepted in the vehicle, it is merged into `develop` promptly so the public state does not fall behind.

## Packages and releases

- A package is built from one named commit by one script (`tools/release/build_hmi_and_package.sh`), on one builder in the private build infrastructure, which owns menu JARs and release packaging (see [AGENTS.md](../AGENTS.md)). The build order names branch and commit.
- Native code is built in the pinned QNX image, menu JARs with J9 from privately stored, checksummed OEM inputs. The build records its own binary hashes in the profile known-states.
- `develop` → `main` only with vehicle acceptance; the tag `v<version>` (for example `v1.5.0-beta.13`) points at the commit the package was built from.

## Code is written in one place

A feature is implemented on one branch. Parallel implementations of the same feature on different machines or repositories are not merged side by side; one is chosen and the other is dropped.
