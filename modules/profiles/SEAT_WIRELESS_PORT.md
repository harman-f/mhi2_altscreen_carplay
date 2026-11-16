# Porting wireless CarPlay and its menu to SEAT profiles

This is a source-level handoff for the existing SEAT MU1409 P4708 and MU1447
P4709 profiles. It explains how to carry the shared menu work into a
firmware-specific build. **It is not a working wireless CarPlay implementation
or installation guide.** The native wireless receiver, production adapter,
pairing and authenticated control are still missing. Neither SEAT profile has
vehicle acceptance for this work. Copying a profile or displaying the menu does
not create a wireless connection.

The current Škoda source adds the page to the existing MIBR CarPlay settings
menu, at the root by default. It does not reproduce or install the reference
package's separate App-Connect page. The editor may reposition the shared page;
no changed menu from this branch has been installed on a unit.

## What is shared

- `modules/menu/source/java/de/mibr/hmi/MibrCarPlayMenuModel.java` renders the
  menu tree. `MibrMenuLayout.java` parses the checksummed layout and identifies
  the `wireless.control` fixed page. Its rows are owned UI, not settings keys.
- `MibrWirelessSession.java` manages page lifecycle, request IDs, timeouts and
  confirmed state. `MibrWirelessBackend.java` defines the Java boundary;
  `MibrOwnedSsmRows.java` attaches it to the native menu. The normal constructor
  supplies no backend, so the page reports unavailable and actions stay disabled.
- `tools/menu-editor/function-catalog.json` is the catalog source;
  `generate_menu_catalog.py` generates `MibrMenuCatalog.java` and
  `tools/menu-editor/standard-menu.txt`. Both editor variants embed the catalog.
  Catalog 3 makes `wireless.control` movable, renameable, expert-only or
  removable. Older catalog-1/2 layouts receive it on the root; catalog-3 layouts
  may omit it. See [the layout contract](../../tools/menu-editor/MENU_FILE_FORMAT.md).
- `modules/wireless/source/` is a separate, optional C control library. It is
  disabled by default and has no production receiver or adapter. Its C API and
  the Java backend are different interfaces; no bridge between them is supplied.
  Read its [integration contract](../wireless/README.md) before proposing one.
- The common broker and `modules/broker/runtime/mibr-control/mibr-menu.ksh`
  transport the menu layout; they do not implement wireless operations or select
  menu functions by catalog number. Shared menu, broker, CarPlay and navigation
  code should remain common instead of being copied into a SEAT profile.

## What differs by profile

| Area | Škoda MU1440 P4526 | SEAT MU1409 P4708 / MU1447 P4709 |
| --- | --- | --- |
| Selection and build inputs | `skoda-mu1440-p4526/profile.json` | The respective `seat-mu1409-p4708/profile.json` or `seat-mu1447-p4709/profile.json` |
| Java profile | Shared-source `modules/menu/source/java/de/mibr/hmi/MibrSkodaMu1440Profile.java` | `seat-mu1409-p4708/hmi/java/de/mibr/hmi/MibrSeatMu1409Profile.java`; MU1447 extends it with `MibrSeatMu1447Profile.java` |
| HMI integration | Profile `hmi/oem-anchors.json` and reference profile implementation | Each profile has its own `hmi/oem-anchors.json`; MU1447 declares MU1409 adapter lineage and an image-index offset of 6 |
| Platform integration | Profile `integration/variants.list` and its transforms | Corresponding profile-specific variants and transforms; the SEAT smartphone integration transform also enables the SEAT wheel-zoom bridge |
| Other profile groups | `display/`, `icons/`, `input/` | Same groups exist, but a directory or README alone is not a built or verified adapter |

All profile paths in the table are under `modules/profiles/` unless written in
full. The Škoda profile supplies the reference geometry, four-state owned tile,
dropdown strategy and lifecycle choices through `MibrOemProfile`. The SEAT
MU1409 source instead declares its own geometry, live native image array and
gear overlay, dropdown strategy and listener handling; MU1447 inherits that
source with its declared index offset. These differences concern HMI presentation
and binding, not wireless capability. `MibrOemProfiles` selects the generated
`MibrProfileBinding` in each profile-specific JAR; it is not a runtime brand
switch. The SEAT `java.adapter_status` metadata still says `none` despite checked-in
adapter source, so reconcile metadata with actual build evidence rather than
inferring a completed build.

## Work a SEAT contributor can reproduce

1. **Identify the exact target.** Follow the [profile selector rules](README.md#selector-rules-owner-decision-e3): the booted JXE fingerprint selects one profile and the firmware string is a separate plausibility check. The API JAR fingerprint is a separate build-input check. Treat an unknown or contradictory fingerprint as unsupported; MU1409, MU1447 and P4708_1 are not interchangeable. Do not add firmware or proprietary assets to this repository.
2. **Review the binding before changing it.** Compare the selected profile's `profile.json`, `hmi/oem-anchors.json` and adapter source with the shared `MibrOemProfile` interface and Škoda reference. For MU1447 include the MU1409 source lineage. Check the target's menu templates, geometry, icon resources, dropdown behavior, callbacks and attach/detach lifecycle against independently obtained, appropriately licensed target evidence. Do not assume Škoda IDs, resources or interaction behavior are valid on SEAT.
3. **Keep the menu portable.** Retain `wireless.control` in the shared catalog rather than creating a SEAT-only synthetic row. Use the editor to position or hide it and verify the saved layout, including older layouts and custom pages. A missing backend must continue to report unavailable; no local toggle or mock confirmation may claim a native success.
4. **Run host checks from the repository root.** With a host JDK run `bash modules/menu/source/tests/run_view_model_test.sh`; run `python3 -B -m unittest discover -s modules/menu/source/tests -p 'test_profiles.py'`. With `jsdom` and `jszip` available outside the checkout (for example via `NODE_PATH` pointing to their external `node_modules`), run `node tools/menu-editor/test-p04.cjs` and `node tools/menu-editor/test-p05.cjs`. Run the wireless host fixtures as described in the wireless README. Record failures, exact inputs and results as host-only evidence.
5. **Build each target separately.** Use `modules/menu/source/build.sh` and the [menu build guide](../../docs/build/MU1440_MENU_RGI_SOURCE.md), with `PROFILE` set to the selected profile, the locally supplied hash-verified firmware API input, the two target-specific source inputs required by the script, and the required J9 toolchain. Set `OUT` to a directory outside the public checkout. The build generates the profile binding and includes declared adapter source directories. Keep supplied firmware material and build outputs out of public source. A host test or a generated binding is not a successful target J9 build. Follow the [package contract](../../docs/build/PACKAGE_LAYOUT.md) and profile source-lock checks before any release candidate; do not reuse a prebuilt JAR after changing its inputs.
6. **Implement the missing integration as separate work.** A real native backend must implement the capabilities and confirmed asynchronous replies in `MibrWirelessBackend`, and a suitable adapter must satisfy the C library's ownership, pairing, authentication, transport, radio snapshot and lifecycle contracts. Establish how the two interfaces connect without introducing another media/session owner. Exercise missing capabilities, failed or delayed replies, stale generations, teardown, wired coexistence and recovery before any vehicle claim. The current source supplies neither that bridge nor the required receiver.
7. **Classify evidence separately.** Record exact profile and artifacts, then distinguish host/mock results, target compilation, integration tests and actual unit/vehicle results. Seat HMI appearance, controls, pairing, wireless media, reconnect and wired coexistence remain unverified until independently tested on the matching unit. Any future target commands or deployment must first follow the repository's [QNX compatibility contract](../../docs/testing/MU1440_QNX_SHELL_COMPATIBILITY.md) and release/install procedures.

For example, after setting the named variables to the verified local inputs and
an external work directory, the MU1409 build invocation is:

```sh
PROFILE=seat-mu1409-p4708 OUT="$WORK_DIR/menu-seat-mu1409" \
  J9_HOME="$J9_SDK" LSD_JAR="$SEAT_API_JAR" \
  OEM_ACTIVATOR_SOURCE="$SEAT_ACTIVATOR_JAVA" \
  OEM_WIDGET_FACTORY_SOURCE="$SEAT_WIDGET_FACTORY_JAVA" \
  bash modules/menu/source/build.sh
```

Use the matching MU1447 profile and its own API/source inputs for that target.
This command builds a local JAR; it does not install or qualify it.

For the Škoda offline build, five `@Override` annotations in locally extracted
OEM source copies were incompatible with the J9 compiler's Java 1.2 source
level. Removing only those annotations in private copies allowed compilation;
the original inputs and profile hash checks remained unchanged. A different
target's inputs must be checked separately. A comparison against one existing
Škoda installation also found three `MibrViewProfile` class files absent from
the new JAR. Reconcile installed functionality and class inventory before
replacing any JAR; the inventory difference alone does not prove a failure.

The historical Škoda package has separate vehicle evidence; it does not prove
this new Wireless page, a receiver, or either SEAT profile. See [multi-profile
status](../../docs/testing/MULTI_PROFILE_TESTING.md) and [menu binary provenance](MENU_PREBUILT_PROVENANCE.md).
