#!/bin/sh
set -eu

BIN="${1:-./build/mhi2-wcp-iap2-runtime-config}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

cat >"$TMP/base.cfg" <<'EOF'
[accessory]
name=SKODA AUTO

[WiFi]
enable=no
SSID=OLD
Passphrase=oldsecret
SecurityType=2
Channel=1

[location]
enable=yes
EOF

cat >"$TMP/state" <<'EOF'
SSID=MIB-CarPlay
Passphrase=correcthorse
SecurityType=2
Channel=6
EOF

"$BIN" --base "$TMP/base.cfg" --state "$TMP/state" --output "$TMP/out.cfg" >/dev/null

test "$(grep -c '^\[WiFi\]$' "$TMP/out.cfg")" -eq 1
grep -q '^\[accessory\]$' "$TMP/out.cfg"
grep -q '^\[location\]$' "$TMP/out.cfg"
grep -q '^enable=yes$' "$TMP/out.cfg"
grep -q '^name=wifi$' "$TMP/out.cfg"
grep -q '^carplay=yes$' "$TMP/out.cfg"
grep -q '^SSID=MIB-CarPlay$' "$TMP/out.cfg"
grep -q '^Passphrase=correcthorse$' "$TMP/out.cfg"
grep -q '^SecurityType=2$' "$TMP/out.cfg"
grep -q '^Channel=6$' "$TMP/out.cfg"
! grep -q '^SSID=OLD$' "$TMP/out.cfg"
! grep -q '^Passphrase=oldsecret$' "$TMP/out.cfg"

cat >"$TMP/open.state" <<'EOF'
SSID=MIB-Open
Passphrase=
SecurityType=0
Channel=11
EOF
"$BIN" --base "$TMP/base.cfg" --state "$TMP/open.state" --output "$TMP/open.cfg" >/dev/null
grep -q '^SecurityType=0$' "$TMP/open.cfg"
! grep -q '^Passphrase=' "$TMP/open.cfg"

cat >"$TMP/bad.state" <<'EOF'
SSID=MIB-Bad
Passphrase=correcthorse
SecurityType=1
Channel=6
EOF
if "$BIN" --base "$TMP/base.cfg" --state "$TMP/bad.state" --output "$TMP/bad.cfg" >/dev/null 2>&1; then
    echo "unsupported SecurityType unexpectedly accepted" >&2
    exit 1
fi

echo "iap2 runtime config tests: ok"
