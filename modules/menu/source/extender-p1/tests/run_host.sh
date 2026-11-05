#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
javac --release 8 -d "$OUT" "$ROOT/tests/stubs/de/vw/mib/extstartup/spi/ExtendedStartupSPI.java" "$ROOT/tests/stubs/de/vw/mib/extstartup/spi/StartupResumeListener.java" "$ROOT/java/de/mibr/extender/MibrStartupHook.java" "$ROOT/java/de/mibr/extender/MibrExtenderCore.java" "$ROOT/tests/MibrBootstrapTest.java"
java -cp "$OUT" MibrBootstrapTest > "$OUT/stdout" 2> "$OUT/stderr"
grep -qx P1_HOST_TEST_PASS "$OUT/stdout"
[ "$(grep -cx MIBR_EXT_P1_CONSTRUCTED "$OUT/stderr")" = 1 ]
[ "$(grep -cx MIBR_EXT_P1_MODULES_DISABLED "$OUT/stderr")" = 1 ]
[ "$(grep -cx MIBR_EXT_P1_BEFORE_AUTOSTART "$OUT/stderr")" = 1 ]
! grep -q MIBR_EXT_P1_FAILURE "$OUT/stderr"
echo P1_HOST_TEST_PASS
