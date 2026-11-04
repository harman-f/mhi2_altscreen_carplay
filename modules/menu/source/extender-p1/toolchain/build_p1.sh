#!/bin/sh
# Exact target IBM-J9 build only; no vehicle operations.
set -eu
: "${J9_HOME:=/jdk}"
: "${LSD_JAR:=/stock/lsd.jar}"
: "${SRC:=/src}"
: "${OUT:=/out}"
test -x "$J9_HOME/bin/javac" && test -x "$J9_HOME/bin/jar" || { echo J9_SDK_MISSING >&2; exit 21; }
test -s "$LSD_JAR" || { echo EXACT_TARGET_LSD_JAR_MISSING >&2; exit 22; }
mkdir -p "$OUT/classes"
"$J9_HOME/bin/javac" -source 1.2 -target 1.2 -cp "$LSD_JAR" -d "$OUT/classes" \
 "$SRC/java/de/mibr/extender/MibrStartupHook.java" \
 "$SRC/java/de/mibr/extender/MibrExtenderCore.java"
(cd "$OUT/classes" && "$J9_HOME/bin/jar" cf "$OUT/MIBR-Extender-P1-BootProbe.jar" de/mibr/extender/MibrStartupHook.class de/mibr/extender/MibrExtenderCore.class)
echo P1_J9_COMPILE_PASS
