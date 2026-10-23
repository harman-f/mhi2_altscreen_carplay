#!/usr/bin/env bash
set -euo pipefail

CC="${CC:-cc}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 tools/generate_alt111_settings.py --check

COMMON="-std=gnu99 -Wall -Wextra -Werror -pedantic"
SETTINGS_INC="-Isrc/native/alt111-settings/include -Isrc/native/altscreen111-gen2/include"

"$CC" $COMMON $SETTINGS_INC \
  tests/test_three_views.c src/native/alt111-settings/settings_core.c \
  src/native/altscreen111-gen2/src/alt111_policy.c \
  -o "$TMP/test_three_views"
"$TMP/test_three_views"

"$CC" $COMMON -Isrc/native/vehicle-data \
  tests/test_vdata.c src/native/vehicle-data/mibr_vdata.c src/native/vehicle-data/mvs_core.c \
  -o "$TMP/test_vdata"
"$TMP/test_vdata"

"$CC" $COMMON -Isrc/native/vehicle-data \
  tests/test_vstatus.c src/native/vehicle-data/mibr_vstatus.c \
  -o "$TMP/test_vstatus"
"$TMP/test_vstatus"

echo "INSTALLED_GEN2_HOST_TESTS=PASS"
