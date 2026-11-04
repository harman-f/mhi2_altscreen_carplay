#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
"${CC:-cc}" -std=c99 -Wall -Wextra -Werror -pedantic \
  "$root/modules/media/source/mibr_media_state.c" \
  "$root/modules/media/tests/test_media_state.c" -o "$tmp/media-test"
"$tmp/media-test"
