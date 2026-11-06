#!/bin/sh
# Read-only status of the MIB Runtime installation (writes nothing, takes no lock).
# Same unit-root overrides as mibr-install.ksh (MIBR_APP, MIBR_ESO, MIBR_SYSTEM, MIBR_IFS).
case $0 in */*) SD=${0%/*} ;; *) SD=. ;; esac
SD=$(cd "$SD" 2>/dev/null && pwd) || exit 2
PKG=${SD%/*}
LOG=
. "$SD/lib/mibr-common.ksh"
trap cleanup 0
mkwork || exit 2
find_sha || { echo "MIBR_STATUS=FAIL no sha256sum"; exit 5; }
VER=$NEW/version
OWN=$VER/ownership
if [ ! -d "$NEW" ]; then echo "MIBR_STATUS=NOT_INSTALLED"; exit 0; fi
echo "root=$LNEW"
if [ -f "$VER/installed-version.properties" ]; then
  for k in product product_version target_profile_id package_sha256 install_id; do echo "$k=$(getkey "$VER/installed-version.properties" $k)"; done
else echo "installed-version.properties=absent"; fi
for f in "$VER"/install-*.receipt; do [ -f "$f" ] && echo "receipt $(basename "$f") state=$(getkey "$f" state)"; done
if [ -f "$NEW/state/boot/disabled" ]; then read -r l < "$NEW/state/boot/disabled"; echo "kill_switch=PRESENT ($l)"; else echo "kill_switch=absent"; fi
drift=0
if [ -f "$VER/installed.manifest" ]; then
  n=0
  while read -r s m t st bk pre; do
    case $s in ''|'#'*) continue ;; esac
    n=$((n+1)); r=$(rebase "$t") || continue
    c=$(sha_of "$r")
    if [ "$c" != "$s" ] && [ "$st" != kept ]; then echo "DRIFT $t state=$st now=$c"; drift=$((drift+1)); fi
  done < "$VER/installed.manifest"
  echo "payload_files=$n drift=$drift"
fi
for f in "$OWN"/*.owned; do
  [ -f "$f" ] || continue
  t=$(getkey "$f" target); r=$(rebase "$t") || continue
  c=$(sha_of "$r"); p=$(getkey "$f" patched_sha256); [ -n "$p" ] || p=$(getkey "$f" post_sha256)
  if [ "$c" = "$p" ]; then s=owned-current; else s=CHANGED; fi
  echo "ownership $(getkey "$f" kind) $t $s"
done
if [ -f "$LSD" ]; then
  lsd_scan "$LSD"; echo "lsd.sh j9=$LSD_J9 runtime_block=$LSD_NB legacy_kit_block=$LSD_OB"
else echo "lsd.sh=absent"; fi
echo "MIBR_STATUS=OK"
