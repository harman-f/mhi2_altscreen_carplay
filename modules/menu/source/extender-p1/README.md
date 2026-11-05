# MIBR Extender P1 boot probe (source)

Independently authored, inert startup probe for the MU1440 HMI (`MHI2_ER_SKG13_P4526_MU1440`, IBM J9 / Java 1.2,
class-file major 46). It implements the HMI's `ExtendedStartupSPI` interface and does nothing else:

- constructor: writes the volatile lifecycle record `/tmp/mibr-hmi-activation.status` (`FORMAT=1`, then the
  allow-listed stages `P1_SESSION_START`, `SPI_ENTERED`, `MODULES_DISABLED`) and prints two markers to stderr;
- `isSnapshotBoot()`: records `BEFORE_AUTOSTART` once and returns `false`;
- every other SPI method returns `false` or does nothing. No threads, sockets, configuration reads, module loading,
  persistence or property writes. Every error is swallowed; the record is capped at 2048 bytes.

The HMI loads the class through `-DextendedStartupSPI.class=de.mibr.extender.MibrStartupHook` with the JAR on the boot
class path (configured outside this directory).

## Layout

| Path | Purpose |
|---|---|
| `java/de/mibr/extender/` | `MibrStartupHook` (SPI entry) and `MibrExtenderCore` (bounded status record) |
| `tests/` | host lifecycle test (`run_host.sh`) with minimal interface stubs that only declare the six SPI method signatures |
| `toolchain/build_p1.sh` | target build: IBM J9 `javac -source 1.2 -target 1.2` against a caller-supplied `lsd.jar` |
| `toolchain/verify_p1_jar.py` | archive gate: exactly the two classes, both major 46 |

## Build and test

```sh
sh tests/run_host.sh                       # host JDK, stubs only; prints P1_HOST_TEST_PASS
J9_HOME=/path/to/ibm-j9-sdk LSD_JAR=/path/to/lsd.jar SRC=$PWD OUT=/tmp/p1-out sh toolchain/build_p1.sh
python3 -I toolchain/verify_p1_jar.py /tmp/p1-out/MIBR-Extender-P1-BootProbe.jar
```

`LSD_JAR` is the unit's own OEM `lsd.jar`, obtained locally. It is a compile-time input only; no OEM class, JAR or
decompiled code is part of this source, and the built JAR contains only `de/mibr/extender/*.class`.

## Source scope

The member and constant-pool layout of the classes in the JAR installed on the reference unit
(SHA-256 `1b47814a2e27b8566813ad6f1490882cf4f4c7be2188b38ad810146d6508c303`) matches this source. A byte-exact
rebuild needs the same J9 SDK and OEM `lsd.jar` and has not been performed here; no byte identity is claimed.
This directory is not an installer and does not change `lsd.sh`.
