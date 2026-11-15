# Profile menu binary provenance

The reviewed 1.5.0-beta.11 profile menu JARs are retained in the private
HARMAN-F build infrastructure. They are not active inputs in the public
source tree. Their exact SHA-256 identities and the matching source lock are
verified by the private package builder before reuse.

The public `MENU_SOURCE_LOCK.json` pins the independently reviewed Java,
profile and settings inputs. Any change to these inputs invalidates reuse
until the corresponding private J9 build and source lock are reviewed.
Removing the public JAR paths does not erase their historical Git objects.

The owner reports a Skoda MU1440 vehicle test for the historical package;
SEAT MU1409 and MU1447 have not been vehicle-tested. These statements do not
qualify a newly rebuilt package.
