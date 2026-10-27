#!/usr/bin/env bash
set -euo pipefail

MODULE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd -- "$MODULE/../../.." && pwd)"
OUT="${OUT:-$(mktemp -d)}"
JAVAC="${JAVAC:-javac}"
JAVA="${JAVA:-java}"

mkdir -p "$OUT/generated" "$OUT/classes"
python3 "$MODULE/generate_catalog.py" \
  --registry "$REPO/settings/registry.json" \
  --menu "$MODULE/menu-definition.json" \
  --out-dir "$OUT/generated"
"$JAVAC" -encoding UTF-8 -d "$OUT/classes" \
  "$MODULE/java/de/mibr/hmi/MibrDropdownFrame.java" \
  "$MODULE/tests/MibrDropdownFrameTest.java" \
  "$MODULE/java/de/mibr/hmi/MibrI18n.java" \
  "$MODULE/java/de/mibr/hmi/MibrEngineState.java" \
  "$MODULE/java/de/mibr/hmi/MibrElementSpec.java" \
  "$MODULE/java/de/mibr/hmi/MibrElementTree.java" \
  "$MODULE/java/de/mibr/hmi/MibrElementEngine.java" \
  "$MODULE/java/de/mibr/hmi/MibrCanonicalElementMenu.java" \
  "$MODULE/java/de/mibr/hmi/MibrDraftChoiceModel.java" \
  "$MODULE/java/de/mibr/hmi/MibrPopupEditorModel.java" \
  "$MODULE/java/de/mibr/hmi/MibrVdataDiag.java" \
  "$MODULE/java/de/mibr/hmi/MibrCarPlayMenuModel.java" \
  "$MODULE/java/de/mibr/hmi/MibrV3Protocol.java" \
  "$MODULE/java/de/mibr/hmi/MibrV3Client.java" \
  "$MODULE/java/de/mibr/hmi/MibrV3Session.java" \
  "$MODULE/java/de/mibr/hmi/MibrViewState.java" \
  "$OUT/generated/MibrSettingsCatalog.java" \
  "$OUT/generated/MibrMenuDefinition.java" \
  "$MODULE/tests/MibrViewStateTest.java" \
  "$MODULE/tests/MibrCanonicalElementMenuTest.java" \
  "$MODULE/tests/MibrCarPlayMenuModelTest.java" \
  "$MODULE/tests/MibrV3BindingTest.java" \
  "$MODULE/tests/MibrV3BusyTest.java" \
  "$MODULE/tests/MibrV3QueueTest.java" \
  "$MODULE/tests/MibrV3ShowTest.java"
"$JAVA" -cp "$OUT/classes" de.mibr.hmi.MibrViewStateTest
"$JAVA" -cp "$OUT/classes" de.mibr.hmi.MibrCanonicalElementMenuTest
"$JAVA" -cp "$OUT/classes" de.mibr.hmi.MibrCarPlayMenuModelTest
"$JAVA" -cp "$OUT/classes" de.mibr.hmi.MibrV3BindingTest
"$JAVA" -cp "$OUT/classes" de.mibr.hmi.MibrV3BusyTest
"$JAVA" -cp "$OUT/classes" de.mibr.hmi.MibrV3QueueTest
"$JAVA" -cp "$OUT/classes" de.mibr.hmi.MibrV3ShowTest

"$JAVA" -cp "$OUT/classes" de.mibr.hmi.MibrDropdownFrameTest
