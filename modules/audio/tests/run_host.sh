#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
"${CC:-cc}" -std=c99 -Wall -Wextra -Werror -pedantic \
  "$root/modules/audio/source/mibr_audio_gate.c" \
  "$root/modules/audio/tests/test_audio_gate.c" -o "$tmp/audio-gate"
"$tmp/audio-gate"
