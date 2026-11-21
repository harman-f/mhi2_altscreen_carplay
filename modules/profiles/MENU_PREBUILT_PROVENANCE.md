# Profile menu binary provenance

The reviewed 1.5.0-beta.17 (r15k) profile menu JARs are retained in the
private HARMAN-F build infrastructure. They are not active inputs in the
public source tree. Their exact SHA-256 identities and the matching source
lock are verified by the private package builder before reuse.

**Status of 1.5.0-beta.17 (r15k): vehicle-accepted 2026-11-21 (Skoda MU1440; SEAT built, not vehicle-tested).** It
removes the Demo GPS position function and changes the physical-size hint
text; all other binaries except `mibr-v3-service` are unchanged from r15j.

| Profile | `MIBR-CarPlay.jar` SHA-256 (1.5.0-beta.17, r15k) |
| --- | --- |
| `skoda-mu1440-p4526` | `62e3fcf22ab5368266c9ea33817a787e1533932e8ae8a6a73913af8647f0b4e3` |
| `seat-mu1409-p4708` | `dbca94021693670e25aa68089ccc8144a5e50bdb2ef9dc99f75cbc751b9ce15d` |
| `seat-mu1447-p4709` | `fd2aedc13fdee025c3118295c571e31c3273ce270666a9070ec1abe07d620c73` |

The previously vehicle-accepted menu JARs are those of 1.5.0-beta.16 (r15j):

| Profile | `MIBR-CarPlay.jar` SHA-256 (1.5.0-beta.16, r15j) |
| --- | --- |
| `skoda-mu1440-p4526` | `9dc4b8347b809f5f9fccbba026426697fcf7a0f1b710da0d015a9a3022298dea` |
| `seat-mu1409-p4708` | `933fc4e7e63e678eecd76a1e2429e5f6aef0e44808147e26bd33202958c5e210` |
| `seat-mu1447-p4709` | `bd99adae52672939bc3396dcae61a4c5c41facd64b7b47066f32df74ac810cef` |

The public `MENU_SOURCE_LOCK.json` pins the independently reviewed Java,
profile and settings inputs. Any change to these inputs invalidates reuse
until the corresponding private J9 build and source lock are reviewed.
Removing the public JAR paths does not erase their historical Git objects.

The owner reports a Skoda MU1440 vehicle test of the 1.5.0-beta.16 package
(2026-11-20). The 1.5.0-beta.17 package was vehicle-tested on the Skoda MU1440
(2026-11-21). SEAT MU1409 and MU1447 have not been vehicle-tested in either version. These
statements do not qualify a newly rebuilt package.
