#!/bin/sh
# Exercise only the signal helper with mocks. Never run the vehicle script.
set -eu
case "$0" in */*) test_dir=${0%/*} ;; *) test_dir=. ;; esac
cycle="$test_dir/../btstack-preload/mhi2_wcp_btstack_cycle.sh"
helper=$(awk '/^kill_unexpected\(\)/ {copy=1} copy {print} copy && /^}/ {exit}' "$cycle")
[ -n "$helper" ]
eval "$helper"
say() { :; }
fail() { echo "unexpected fail: $*" >&2; exit 1; }
slay() {
    [ "$*" = '-f -m pid -s 9 12345' ]
    calls=$((calls + 1))
    return "$mock_status"
}
for mock_status in 1 0 2; do
    calls=0
    kill_unexpected 12345
    [ "$calls" -eq 1 ]
    [ "$slay_status" -eq "$mock_status" ]
done
echo 'btstack cycle QNX slay status regression: ok (1=count, 0=ambiguous, 2=diagnostic)'
