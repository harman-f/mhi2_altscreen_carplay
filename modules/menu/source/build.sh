#!/usr/bin/env bash
set -euo pipefail

MODULE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd -- "$MODULE/../../.." && pwd)"
: "${J9_HOME:?Set J9_HOME to the IBM J9 SDK that targets class-file major 46}"
: "${LSD_JAR:?Set LSD_JAR to the locally held exact MU1440 lsd.jar}"
: "${OEM_ACTIVATOR_SOURCE:?Set OEM_ACTIVATOR_SOURCE to a locally extracted source file}"
: "${OEM_WIDGET_FACTORY_SOURCE:?Set OEM_WIDGET_FACTORY_SOURCE to a locally extracted source file}"
: "${OUT:?Set OUT to a local build directory outside public Git}"
PROFILE="${PROFILE:-skoda-mu1440-p4526}"
REGISTRY_JSON="${REGISTRY_JSON:-$REPO/settings/registry.json}"

for executable in "$J9_HOME/bin/javac" "$J9_HOME/bin/jar"; do
  test -x "$executable" || { echo "J9_EXECUTABLE_MISSING=$executable" >&2; exit 21; }
done
for input in "$LSD_JAR" "$OEM_ACTIVATOR_SOURCE" "$OEM_WIDGET_FACTORY_SOURCE" "$REGISTRY_JSON"; do
  test -s "$input" || { echo "BUILD_INPUT_MISSING=$input" >&2; exit 22; }
done
# The API lsd.jar is a build input pinned per firmware profile (profile.json hmi.api_jar_sha256).
# A different reconstruction compiles but may not match the unit's runtime classes, so refuse it.
EXPECTED_API_JAR=$(python3 -c 'import json,sys; print((json.load(open(sys.argv[1])).get("hmi") or {}).get("api_jar_sha256") or "")' \
  "$MODULE/../../profiles/$PROFILE/profile.json")
[ -n "$EXPECTED_API_JAR" ] || { echo "ERROR: profile $PROFILE has no hmi.api_jar_sha256" >&2; exit 1; }
ACTUAL_API_JAR=$(sha256sum "$LSD_JAR" | awk '{print $1}')
[ "$ACTUAL_API_JAR" = "$EXPECTED_API_JAR" ] || {
  echo "ERROR: LSD_JAR sha256 $ACTUAL_API_JAR does not match $PROFILE api_jar_sha256 $EXPECTED_API_JAR" >&2; exit 1; }
echo "API_JAR=PASS profile=$PROFILE sha256=$ACTUAL_API_JAR"
mkdir -p "$OUT"
python3 "$MODULE/generate_catalog.py" --registry "$REGISTRY_JSON" --menu "$MODULE/menu-definition.json" --out-dir "$OUT/catalog"
python3 "$MODULE/prepare_oem_sources.py" \
  --activator "$OEM_ACTIVATOR_SOURCE" \
  --widget-factory "$OEM_WIDGET_FACTORY_SOURCE" \
  --out-dir "$OUT/oem-source" \
  --profile "$PROFILE"
mkdir -p "$OUT/classes"
# One JAR per profile: the generated binding names the adapter; its source dirs join the build.
python3 "$MODULE/generate_profile_binding.py" --profile "$PROFILE" --out-dir "$OUT/profile"
mapfile -t ADAPTER_DIRS < <(python3 "$MODULE/generate_profile_binding.py" --profile "$PROFILE" --print-source-dirs)
mapfile -t SOURCES < <(find "$MODULE/java/de/mibr/hmi" "$MODULE/java/mib/mu1440/vehiclespeed" ${ADAPTER_DIRS[@]+"${ADAPTER_DIRS[@]}"} -type f -name '*.java' -print | sort)
"$J9_HOME/bin/javac" -encoding UTF-8 -source 1.2 -target 1.2 \
  -cp "$LSD_JAR" -d "$OUT/classes" \
  "${SOURCES[@]}" \
  "$OUT/profile/de/mibr/hmi/MibrProfileBinding.java" \
  "$OUT/catalog/MibrSettingsCatalog.java" \
  "$OUT/catalog/MibrMenuDefinition.java" \
  "$OUT/oem-source/de/vw/mib/cio/internal/Activator.java" \
  "$OUT/oem-source/generated/de/vw/mib/global/view/internal/WidgetFactoryImpl.java"
(
  cd "$OUT/classes"
  "$J9_HOME/bin/jar" cf "$OUT/MIBR-HMI-CarPlay-Settings-Home.jar" \
    de/mibr/hmi mib/mu1440/vehiclespeed \
    generated/de/vw/mib/global/view/internal \
    de/vw/mib/cio/internal/Activator.class
)
python3 "$MODULE/verify_class_major.py" "$OUT/MIBR-HMI-CarPlay-Settings-Home.jar" --major 46
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$OUT/MIBR-HMI-CarPlay-Settings-Home.jar"
fi
echo "OEM_MENU_J9_BUILD_PASS (local OEM-derived output; do not publish)"
