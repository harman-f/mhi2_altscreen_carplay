#!/usr/bin/env bash
set -euo pipefail
CC="${CC:-cc}"
SRC="src/native/altscreen111-gen2"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
"$CC" -std=c99 -O2 -Wall -Wextra -Werror -pedantic \
  -I"$SRC/include" "$SRC/src/alt111_zoom.c" tests/alt111_zoom_test.c \
  -o "$OUT/alt111_zoom_test"
"$OUT/alt111_zoom_test"
