# Profile menu binary provenance

The reviewed 1.5.0-beta.16 (r15j) profile menu JARs are retained in the
private HARMAN-F build infrastructure. They are not active inputs in the
public source tree. Their exact SHA-256 identities and the matching source
lock are verified by the private package builder before reuse.

| Profile | `MIBR-CarPlay.jar` SHA-256 |
| --- | --- |
| `skoda-mu1440-p4526` | `9dc4b8347b809f5f9fccbba026426697fcf7a0f1b710da0d015a9a3022298dea` |
| `seat-mu1409-p4708` | `933fc4e7e63e678eecd76a1e2429e5f6aef0e44808147e26bd33202958c5e210` |
| `seat-mu1447-p4709` | `bd99adae52672939bc3396dcae61a4c5c41facd64b7b47066f32df74ac810cef` |

The public `MENU_SOURCE_LOCK.json` pins the independently reviewed Java,
profile and settings inputs. Any change to these inputs invalidates reuse
until the corresponding private J9 build and source lock are reviewed.
Removing the public JAR paths does not erase their historical Git objects.

The owner reports a Skoda MU1440 vehicle test of the 1.5.0-beta.16 package
(2026-11-20); SEAT MU1409 and MU1447 have not been vehicle-tested. These
statements do not qualify a newly rebuilt package.
