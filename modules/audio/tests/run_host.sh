#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
"${CC:-cc}" -std=c99 -Wall -Wextra -Werror -pedantic \
  "$root/modules/audio/source/mibr_audio_gate.c" \
  "$root/modules/audio/tests/test_audio_gate.c" -o "$tmp/audio-gate"
"${CC:-cc}" -std=c99 -Wall -Wextra -Werror -pedantic \
  "$root/modules/audio/source/mibr_audio_gate.c" \
  "$root/modules/audio/source/mibr_audio_owner.c" \
  "$root/modules/audio/tests/test_audio_owner.c" -o "$tmp/audio-owner"
"$tmp/audio-owner"
"$tmp/audio-gate"

# Host-only cross-module lifecycle test: no OEM/PCM/BAP/runtime writes.
"${CC:-cc}" -std=c99 -Wall -Wextra -Werror -pedantic \
  "$root/modules/media/source/mibr_media_state.c" \
  "$root/modules/media/source/mibr_media_ingress.c" \
  "$root/modules/phone/source/mibr_phone_state.c" \
  "$root/modules/phone/source/mibr_phone_ingress.c" \
  "$root/modules/audio/source/mibr_audio_gate.c" \
  "$root/modules/audio/source/mibr_audio_owner.c" \
  "$root/modules/audio/tests/test_cross_feature_session.c" -o "$tmp/cross-feature"
"$tmp/cross-feature"
