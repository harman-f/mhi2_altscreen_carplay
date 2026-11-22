#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
"${CC:-cc}" -std=c99 -Wall -Wextra -Werror -pedantic \
  "$root/modules/phone/source/mibr_phone_state.c" \
  "$root/modules/phone/tests/test_phone_state.c" -o "$tmp/phone-test"
"${CC:-cc}" -std=c99 -Wall -Wextra -Werror -pedantic \
  "$root/modules/phone/source/mibr_phone_state.c" \
  "$root/modules/phone/source/mibr_phone_ingress.c" \
  "$root/modules/phone/tests/test_phone_ingress.c" -o "$tmp/phone-ingress"
"$tmp/phone-ingress"
"$tmp/phone-test"
