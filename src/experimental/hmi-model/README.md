# Public Java HMI protocol and menu metadata (source only)

Project-authored source for the **bounded Java 1.2-style MIBR/3 protocol and UI metadata**. This directory does not redistribute OEM JAR/JXE, decompiled framework classes, original skins or raster icons. The language adapter refers to a platform-provided configuration service by name, using reflection; no original platform implementation is included.

- `MibrV3Protocol.java` parses/constructs bounded UI protocol frames and validates typed result claims. STORED is not ACTIVE.
- `MibrSettingsCatalog.java` and `MibrMenuDefinition.java` supply project-owned display metadata; `menu-definition.json` is the human-readable menu layout/config.
- `MibrI18n.java` provides German/English UI labels with fallback.
- `PublicProtocolSmokeTest.java` checks the current source projection and wire encoding on a host JDK.

```sh
tmp="$(mktemp -d)"
javac -d "$tmp" src/experimental/hmi-model/java/de/mibr/hmi/*.java
java -cp "$tmp" de.mibr.hmi.PublicProtocolSmokeTest
rm -rf "$tmp"
```

This is **not** the project-owned full OEM HOME/Settings widget integration, compiled exact-target IBM J9 image, native controller, a live vehicle apply/ACK, or an installer. The complete UI needs a separately qualified exact-firmware interface and provenance-cleared generated/asset code. See [public source coverage](../../../docs/status/PUBLISHED_SOURCE_COVERAGE.md).
