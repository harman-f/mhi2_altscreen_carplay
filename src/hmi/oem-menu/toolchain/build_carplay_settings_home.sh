#!/bin/sh
set -eu
: "${J9_HOME:=/jdk}"
: "${LSD_JAR:=/stock/lsd.jar}"
: "${OUT:=/out}"
: "${SRC:=/src}"
test -x "$J9_HOME/bin/javac" && test -x "$J9_HOME/bin/jar" || { echo J9_SDK_MISSING >&2; exit 21; }
test -s "$LSD_JAR" || { echo EXACT_MU1440_LSD_MISSING >&2; exit 22; }
test -f "$SRC/generated-src/de/vw/mib/cio/internal/Activator.java" || { echo CIO_SOURCE_NOT_PREPARED >&2; exit 23; }
mkdir -p "$OUT/classes"
"$J9_HOME/bin/javac" -encoding UTF-8 -source 1.2 -target 1.2 -cp "$LSD_JAR" -d "$OUT/classes" \
 "$SRC/java/de/mibr/hmi/MibrSettingsCatalog.java" \
 "$SRC/java/de/mibr/hmi/MibrMenuDefinition.java" \
 "$SRC/java/de/mibr/hmi/MibrI18n.java" \
 "$SRC/java/de/mibr/hmi/MibrCarPlayMenuModel.java" \
 "$SRC/java/de/mibr/hmi/MibrMenuCatalog.java" \
 "$SRC/java/de/mibr/hmi/MibrMenuLayout.java" \
 "$SRC/java/de/mibr/hmi/MibrMenuFunctions.java" \
 "$SRC/java/de/mibr/hmi/MibrExpert.java" \
 "$SRC/java/de/mibr/hmi/MibrCalibration.java" \
 "$SRC/java/de/mibr/hmi/MibrElementSpec.java" \
 "$SRC/java/de/mibr/hmi/MibrElementEngine.java" \
 "$SRC/java/de/mibr/hmi/MibrElementTree.java" \
 "$SRC/java/de/mibr/hmi/MibrCanonicalElementMenu.java" \
 "$SRC/java/de/mibr/hmi/MibrElementDetailRows.java" \
 "$SRC/java/de/mibr/hmi/MibrControlProtocol.java" \
 "$SRC/java/de/mibr/hmi/MibrControlSession.java" \
 "$SRC/java/de/mibr/hmi/MibrControlBootstrap.java" \
 "$SRC/java/de/mibr/hmi/MibrControlClient.java" \
 "$SRC/java/de/mibr/hmi/MibrV3Protocol.java" \
 "$SRC/java/de/mibr/hmi/MibrV3Client.java" \
 "$SRC/java/de/mibr/hmi/MibrV3Bootstrap.java" \
 "$SRC/java/de/mibr/hmi/MibrV3Session.java" \
 "$SRC/java/de/mibr/hmi/MibrV3Route.java" \
 "$SRC/java/de/mibr/hmi/MibrDraftChoiceModel.java" \
 "$SRC/java/de/mibr/hmi/MibrPopupEditorModel.java" \
 "$SRC/java/de/mibr/hmi/MibrScalingState.java" \
 "$SRC/java/de/mibr/hmi/MibrGpsDemoState.java" \
 "$SRC/java/de/mibr/hmi/MibrVersionInfo.java" \
 "$SRC/java/de/mibr/hmi/MibrOemDropdownStyle.java" \
 "$SRC/java/de/mibr/hmi/MibrNativeDropdownEditor.java" \
 "$SRC/java/de/mibr/hmi/MibrIconState.java" \
 "$SRC/java/de/mibr/hmi/MibrIconLoadState.java" \
 "$SRC/java/de/mibr/hmi/MibrNativeSkinMode.java" \
 "$SRC/java/de/mibr/hmi/MibrOwnedIconImage.java" \
 "$SRC/java/de/mibr/hmi/MibrFourStateIconUI.java" \
 "$SRC/java/de/mibr/hmi/MibrOwnedStaticImage.java" \
 "$SRC/java/de/mibr/hmi/MibrScrollBarUI.java" \
 "$SRC/java/de/mibr/hmi/MibrScrollIndicator.java" \
 "$SRC/java/de/mibr/hmi/MibrOwnedWidgets.java" \
 "$SRC/java/de/mibr/hmi/MibrOemSsmTemplate.java" \
 "$SRC/java/de/mibr/hmi/MibrOemPageEntry.java" \
 "$SRC/java/de/mibr/hmi/MibrMenuKeyBack.java" \
 "$SRC/java/de/mibr/hmi/MibrHomeAnimationMirror.java" \
 "$SRC/java/de/mibr/hmi/MibrOemTileLongPress.java" \
 "$SRC/java/de/mibr/hmi/MibrOwnedSsmPageHost.java" \
 "$SRC/java/de/mibr/hmi/MibrSsmSourceBinding.java" \
 "$SRC/java/de/mibr/hmi/MibrIsolatedSsmServices.java" \
 "$SRC/java/de/mibr/hmi/MibrOwnedSsmRows.java" \
 "$SRC/java/de/mibr/hmi/MibrSsmNativePage.java" \
 "$SRC/java/de/mibr/hmi/MibrHomeList.java" \
 "$SRC/java/mib/mu1440/vehiclespeed/Mvs1Codec.java" \
 "$SRC/java/mib/mu1440/vehiclespeed/Mu1440CarBCSpeedDecoder.java" \
 "$SRC/java/mib/mu1440/vehiclespeed/DsiVehicleSpeedAdapter.java" \
 "$SRC/java/de/mibr/hmi/MibrVdataBridge.java" \
 "$SRC/java/de/mibr/hmi/MibrVdataDiag.java" \
 "$SRC/java/de/mibr/hmi/MibrEngineState.java" \
 "$SRC/java/de/mibr/hmi/MibrViewState.java" \
 "$SRC/java/de/mibr/hmi/MibrVstatusAdapter.java" \
 "$SRC/java/de/mibr/hmi/MibrVstatusSource.java" \
 "$SRC/java/de/mibr/hmi/MibrPlatformDefaults.java" \
 "$SRC/java/de/mibr/hmi/MibrSafeArea.java" \
 "$SRC/java/de/mibr/hmi/MibrDurableSwitch.java" \
 "$SRC/java/de/mibr/hmi/MibrServiceHealth.java" \
 "$SRC/java/de/mibr/hmi/MibrRgiManeuvers.java" \
 "$SRC/java/de/mibr/hmi/MibrRgiGuidance.java" \
 "$SRC/java/de/mibr/hmi/MibrRgiDemo.java" \
 "$SRC/java/de/mibr/hmi/MibrRgiCockpit.java" \
 "$SRC/java/de/mibr/hmi/MibrHomeCio.java" \
 "$SRC/java/de/mibr/hmi/MibrVisualizationService.java" \
 "$SRC/java/generated/de/vw/mib/global/view/internal/WidgetFactoryImpl.java" \
 "$SRC/generated-src/de/vw/mib/cio/internal/Activator.java"
(cd "$OUT/classes" && "$J9_HOME/bin/jar" cf "$OUT/MIBR-HMI-CarPlay-Settings-Home.jar" de/mibr/hmi mib/mu1440/vehiclespeed generated/de/vw/mib/global/view/internal de/vw/mib/cio/internal/Activator.class)
echo MIBR_CARPLAY_SETTINGS_HOME_J9_BUILD_PASS
