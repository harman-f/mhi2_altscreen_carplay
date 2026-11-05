# MU1440 OEM menu adapter source

This module contains project-authored Java/J9 adapter source for the MU1440 HOME and CarPlay settings menu, updated through the R57 menu implementation. It is a source publication, not an installer or a vehicle-qualified release. `tests/PublicProtocolSmokeTest.java` is an OEM-independent host check of the protocol/model classes.

The menu uses the repository's single canonical [settings registry](../../../settings/registry.json). The adjacent `menu-definition.json` only describes menu navigation, labels and visibility. It does not define values, defaults, storage or apply behavior. Generated `MibrSettingsCatalog.java` and `MibrMenuDefinition.java` are built from the registry and menu JSON. The R57 `Ansichten` submenu contains broker-backed virtual rows for cockpit-view following; those rows do not add keys to the 48-setting registry.

## R51–R57 menu source

The adapter includes the R51 settled-icon drawing behavior and the R55–R57 view controls. In `Ansichten`, seven broker-backed rows control view-follow mode, current cockpit view, the R57 long-press resync view, three cockpit-view-to-safe-area mappings, and whether the vehicle has the Sporttacho view. The HMI sends `VIEW_GET` and `VIEW_SET` through the existing MIBR/3 session; these rows are outside the canonical registry.

The R57 source snapshot corresponds to the menu artifact whose recorded SHA-256 is `8cf3b61939a54ba2d1456479238ed2484129216525adf355778404e53cff7558`. This is a reference artifact hash, not proof that this public source rebuild reproduces those bytes. No IBM J9 toolchain or exact MU1440 `lsd.jar` is redistributed; exact Java rebuild parity remains unverified.

The Java menu depends on a matching MIBR/3 broker implementation for `VIEW_GET` and `VIEW_SET`. The R57 physical key mapping also depends on the separately versioned native key daemon and service. This module does not include or replace those non-Java components, and it does not by itself establish the complete R57 runtime behavior.

## Source scope

`java/de/mibr/hmi/` contains the Java adapter, owned page lifecycle, native Ssm row/dropdown bindings, project UI state models, MIBR/3 client, and the diagnostics/vehicle-data adapters. `java/mib/mu1440/vehiclespeed/` contains the project-owned speed decoding and DSI adapter used by that menu.

The module does not include OEM JAR/JXE files, OEM class files, decompiled OEM implementation sources, generated OEM class bodies, menu artwork, or an install package. Two local source files from the exact target are needed only as inputs to the build-time adapter patcher. The patcher checks each expected anchor exactly once, writes patched copies to the local build directory, and fails on drift or repeated patching. Keep those inputs and generated outputs outside public Git.

The four project-authored scroll-indicator PNGs are included under [assets/scroll](assets/scroll/README.md). The owned HOME tile also expects four Skin3-derived and four stock Skin1 icon PNGs supplied from local OEM resources; these images are derived from OEM skin records/assets and are not distributed here. The widget clears the cloned stock art before loading its external image, so without those files the custom HOME tile artwork is incomplete. A working visual presentation therefore requires the locally installed target firmware/resources and those external icon prerequisites; this source tree is not a self-contained visual preview.

The adapter targets the MU1440 OEM Java API and is not a portable MHI2 widget implementation. It preserves the stock widget lifecycle and restores the stock list/page state when the owned page closes. Settings remain behind the shared MIBR/3 service; this Java UI does not introduce a parallel settings store or a second media/ownership component.

## Build prerequisites

- IBM J9 SDK whose `javac` emits the target's class-file major version 46.
- The exact MU1440 `lsd.jar`, held locally and supplied as `LSD_JAR`.
- Local source views extracted or decompiled from that same target's CIO `Activator` and `WidgetFactoryImpl`, supplied as `OEM_ACTIVATOR_SOURCE` and `OEM_WIDGET_FACTORY_SOURCE`.
- Python 3 and Bash on the host.

The J9 SDK and OEM classpath/source inputs are external prerequisites and are not redistributed here. The resulting JAR contains target-derived classes and should remain in the local build area.

```sh
export J9_HOME=/path/to/ibm-j9-sdk
export LSD_JAR=/path/to/local/mu1440/lsd.jar
export OEM_ACTIVATOR_SOURCE=/path/to/local/extracted/Activator.java
export OEM_WIDGET_FACTORY_SOURCE=/path/to/local/extracted/WidgetFactoryImpl.java
export OUT=/tmp/mu1440-oem-menu-build
export REGISTRY_JSON="$PWD/settings/registry.json"
bash modules/menu/source/build.sh
```

The build regenerates UI metadata from the public canonical registry, applies the two guarded adapter edits to local target-source inputs, compiles with `-source 1.2 -target 1.2`, checks every JAR class file is major version 46, and writes the target-specific JAR under `OUT`. It does not fetch, copy or unpack OEM source material.

## Host checks

```sh
python3 -m unittest discover -s modules/menu/source/tests -v
python3 modules/menu/source/generate_catalog.py \
  --registry settings/registry.json \
  --menu modules/menu/source/menu-definition.json \
  --out-dir /tmp/mu1440-oem-menu-catalog
python3 modules/menu/source/generate_catalog.py --check \
  --registry settings/registry.json \
  --menu modules/menu/source/menu-definition.json \
  --out-dir /tmp/mu1440-oem-menu-catalog
bash modules/menu/source/tests/run_view_model_test.sh
```

Python host tests cover menu metadata generation and the guarded source transformations. The separate Java host test compiles and runs the R57 view-state/protocol model with a local JDK. These checks do not validate IBM J9 compilation, OEM widget rendering, installation, or runtime behavior. The generated catalog metadata differs from the reference R57 JAR because this source build uses the repository's canonical registry. The published build is not byte-identical proof for the reference JAR; its OEM toolchain inputs are intentionally not included here.

Project-authored source is licensed under the repository's GPL-3.0-or-later terms. OEM APIs, firmware, SDKs and other third-party material retain their owners' rights; see [third-party notices](../../../THIRD_PARTY_NOTICES.md).

## Building per firmware profile

The menu core under `java/` is shared by all profiles. Firmware differences sit behind `de.mibr.hmi.MibrOemProfile`: stock setup view id, home tile geometry, tile renderer strategy, native dropdown availability strategy, accepted home animation table, native image index offset and listener lifecycle. `MibrOemProfiles.current()` returns the profile bound at compile time. One JAR is built per profile; `build.sh` generates `MibrProfileBinding`, which names the adapter class, and adds the profile's `modules/profiles/<id>/hmi/java` directory to the source path.

```sh
PROFILE=seat-mu1409-p4708 bash modules/menu/source/build.sh   # default: skoda-mu1440-p4526
```

| `PROFILE` | Adapter class | Source |
| --- | --- | --- |
| `skoda-mu1440-p4526` (default) | `MibrSkodaMu1440Profile` | shared core, behaviour unchanged |
| `seat-mu1409-p4708` | `MibrSeatMu1409Profile` | `modules/profiles/seat-mu1409-p4708/hmi/java` |
| `seat-mu1447-p4709` | `MibrSeatMu1447Profile` (MU1409 adapter, image index offset 6) | its own and the MU1409 `hmi/java` |

Each profile carries its OEM patch anchors as data in `modules/profiles/<id>/hmi/oem-anchors.json`; `prepare_oem_sources.py --profile <id>` applies them (default Skoda output is unchanged and checked against a frozen copy of the previous patcher). The SEAT gear overlay PNG named by `MibrSeatGearOverlayImage` is a profile asset that is not part of this source tree yet.

Status: the SEAT profiles are source only. No J9 build of any SEAT JAR and no device test has been run; the exact per-firmware `lsd.jar` and OEM source inputs are local-only. Host checks: `python3 modules/menu/source/check_java12_syntax.py` (Java 1.2 syntax lint, no compiler needed) and the unit tests above.
