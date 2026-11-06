#!/bin/sh
# MIB Runtime installer: check / apply / uninstall / rollback for one extracted package.
# Run from the unit's shell (QNX pdksh) or any POSIX sh on a host:
#
#   ksh installer/mibr-install.ksh --check                 read-only report (default); writes nothing on the unit
#   ksh installer/mibr-install.ksh --apply [--authorize-single-writer]
#   ksh installer/mibr-install.ksh --uninstall [--purge]   (also: installer/mibr-uninstall.ksh)
#   ksh installer/mibr-install.ksh --rollback <install-id>
#   ksh installer/mibr-status.ksh                          read-only status
#   --id <install-id>                                      override the derived install id (A-Z a-z 0-9 . _ -)
#
# Exit: 0 ok | 2 usage | 3 profile selection (unknown/ambiguous/disabled/train/unreadable)
#       4 package verification | 5 missing tool | 10 BLOCK (nothing written) | 11 lock busy
#       12 mount | 20 migration | 21 filesystem not back to read-only | 30 write/verify failure
#       99 injected test failure
#
# --apply order, every step fail-closed (steps 1-4 never write to the unit):
#   1 session log in the package dir, exit trap (always mount -ur), lock /tmp/mibr-install.lock
#   2 PACKAGE.sha256: every listed file matches, no unlisted file, no symlink
#   3 profile: installer/select-profile.ksh with the train read from the EEPROM
#   4 classify every target by hash (stock / package / known-previous / owned / foreign), precompute
#     every OEM transform and its result hash, check lsd.sh; any BLOCK ends here
#   5 root migration (installer/lib/migrate-root.ksh run --id <id>; kill switch first)
#   5b backups of every file about to change -> mibr/backup/<id>/oem/ (+ MANIFEST with hashes)
#   6 payload (tmp + chmod + mv + read-back), config only when absent
#   7 OEM variants (ownership receipt first, then the write)
#   8 defaults on a first install only
#   9 receipts: installed.manifest, components.manifest, installed-version.properties, install-<id>.receipt
#   7b lsd.sh block LAST (the hook that makes the unit load MIBR), then receipt state=complete
#   10 sync, read-only
# Re-running after any interruption continues (all steps are idempotent for the same install id).
#
# Rollback semantics (exact): --rollback <id> restores, for every row of
#   mibr/backup/<id>/oem/MANIFEST, the bytes that existed before install <id> (OEM variants, lsd.sh,
#   payload files outside mibr/ that were replaced or created), after checking the current bytes still
#   equal what install <id> wrote (otherwise BLOCK, nothing written). lsd.sh is restored last. The legacy
#   trees are never touched by any step (M1 copies, it does not move), so restoring the previous lsd.sh
#   re-enables the previous package's hooks together with its disabled/enabled state. mibr/ itself
#   (payload, config, state, kill switch, backup) stays in place unreferenced; ownership receipts of <id> are
#   removed and install-<id>.receipt gets state=rolled-back.
#
# Uninstall: restores only what ownership receipts and installed.manifest prove is ours; OEM files return
#   to the recorded stock bytes after a hash check; the mibr/ payload is removed; config the user changed,
#   state/, backup/ and logs/ stay unless --purge. A MIBR block in lsd.sh without receipt or known content
#   is left untouched (warning). Legacy marker "# MIBR-KIT" is recognised when it is ours.

SELF=$0
case $SELF in */*) SD=${SELF%/*} ;; *) SD=. ;; esac
SD=$(cd "$SD" 2>/dev/null && pwd) || { echo "MIBR_INSTALL=FAIL cannot resolve installer directory"; exit 2; }
PKG=${SD%/*}
USAGE="usage: mibr-install.ksh [--check] | --apply [--authorize-single-writer] | --uninstall [--purge] | --rollback <install-id> [--id <install-id>]"

MODE=check
RB_ID=
ID_OPT=
PURGE=0
SW=0
while [ $# -gt 0 ]; do
  case $1 in
    --check) MODE=check ;;
    --apply) MODE=apply ;;
    --uninstall) MODE=uninstall ;;
    --rollback) MODE=rollback; [ $# -ge 2 ] || { echo "$USAGE"; exit 2; }; RB_ID=$2; shift ;;
    --id) [ $# -ge 2 ] || { echo "$USAGE"; exit 2; }; ID_OPT=$2; shift ;;
    --purge) PURGE=1 ;;
    --authorize-single-writer) SW=1 ;;
    *) echo "$USAGE"; exit 2 ;;
  esac
  shift
done
[ "$PURGE" = 0 ] || [ "$MODE" = uninstall ] || { echo "$USAGE"; exit 2; }
[ "$SW" = 0 ] || [ "$MODE" = apply ] || { echo "$USAGE"; exit 2; }
for _v in "$ID_OPT" "$RB_ID"; do
  case $_v in
    *[!A-Za-z0-9._-]*|.*) echo "bad install id (allowed: A-Z a-z 0-9 . _ -)"; exit 2 ;;
  esac
done
if [ "$MODE" = rollback ] && [ -z "$RB_ID" ]; then echo "$USAGE"; exit 2; fi

if [ "$MODE" = check ]; then LOG=; else LOG=${MIBR_LOG:-$PKG/mibr-install.log}; fi
. "$SD/lib/mibr-common.ksh"

trap cleanup 0
trap 'exit 130' 1 2 15

inject(){
  [ "${MIBR_INSTALL_FAIL_AT:-}" = "$1" ] || return 0
  say "MIBR_INSTALL=INJECTED_FAILURE at=$1"
  exit 99
}

# ---------------------------------------------------------------- step 1/2: log, lock, package
mkwork || die 2 "cannot create work directory"
if [ -n "$LOG" ]; then
  echo "=== mibr-install $MODE pid $$ ===" >> "$LOG" 2>/dev/null || die 30 "cannot write session log $LOG"
fi
if [ "$MODE" != check ]; then
  acquire_lock || die 11 "install lock busy: $LOCK"
fi
find_sha || die 5 "no sha256sum (package ships installer/bin/sha256sum)"
say "MIBR_INSTALL=START mode=$MODE package=$PKG"
verify_package || die 4 "package verification failed (nothing was written)"
PKGSHA=$(sha_of "$PKG/PACKAGE.sha256")
PKG12=$(echo "$PKGSHA" | cut -c1-12)
if [ -n "$ID_OPT" ]; then ID=$ID_OPT; else ID=p$PKG12; fi
BLOCKVER=$PKG12
BLOCKFILE=$PKG/installer/config/lsd-block.txt
ok "package verified ($(grep -c . "$W/pkg.sums") files), install id $ID"

PKGVER=-
if [ -f "$PKG/package.json" ]; then
  _v=$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$PKG/package.json" 2>/dev/null | head -1)
  [ -n "$_v" ] && PKGVER=$_v
fi

OWN=$NEW/version/ownership
PREVMF=$NEW/version/installed.manifest

own_name(){
  _o=${1#/}; _r=
  while :; do
    case $_o in
      */*) _r=$_r${_o%%/*}_; _o=${_o#*/} ;;
      *) _r=$_r$_o; break ;;
    esac
  done
  echo "$_r"
}

# ---------------------------------------------------------------- step 3: profile
read_train(){
  TRAIN=
  if [ -n "${MIBR_TRAIN_CMD:-}" ]; then
    TRAIN=$("$MIBR_TRAIN_CMD" 2>/dev/null)
  else
    _awk=$(find_cmd awk) || return 1
    TRAIN=$(on -f rcc /net/rcc/usr/apps/modifyE2P r 3A0 19 2>/dev/null | "$_awk" '
      function hv(c, p) { p=index("0123456789abcdef",tolower(c)); return p ? p-1 : -1 }
      function byte(s, a,b) { a=hv(substr(s,1,1)); b=hv(substr(s,2,1)); if (a<0 || b<0) return -1; return a*16+b }
      { line=$0
        if (line !~ /^0x[0-9A-Fa-f]+/) next
        sub(/^0x[0-9A-Fa-f]+[^0-9A-Fa-f]+/,"",line)
        gsub(/[^0-9A-Fa-f]/,"",line)
        for (i=1; i+1<=length(line); i+=2) { n=byte(substr(line,i,2)); if (n>=32 && n<=126) out=out sprintf("%c",n) } }
      END { gsub(/[^A-Za-z0-9_-]/,"",out); if (length(out)) print out }')
  fi
  case $TRAIN in ''|*[!A-Za-z0-9_-]*) TRAIN=; return 1 ;; esac
  return 0
}

select_profile(){
  read_train || die 3 "EEPROM train unreadable (no profile selection without it)"
  PROFILE_OUT=$("$SH_BIN" "$PKG/installer/select-profile.ksh" "$PKG/installer/config/profiles.list" \
    --jxe "$JXE" --train "$TRAIN" 2>"$W/sel.err")
  _src=$?
  [ "$_src" -eq 0 ] || die 3 "profile selection failed (select-profile exit $_src): $(cat "$W/sel.err")"
  PROFILE=${PROFILE_OUT#PROFILE=}
  safe_rel "$PROFILE" || die 3 "bad profile id from selector"
  [ -d "$PKG/profiles/$PROFILE" ] || die 3 "selected profile $PROFILE is not part of this package"
  ok "profile $PROFILE (train $TRAIN)"
}

# ---------------------------------------------------------------- step 4: plan (read-only)
kind_mode(){ case $1 in bin/*|scripts/*) echo 755 ;; *) echo 644 ;; esac; }

append_manifest(){ # package-relative manifest path
  while read -r _a _b _c _d _x; do
    case $_a in ''|'#'*) continue ;; esac
    if [ -z "$_d" ] || [ -n "$_x" ] || ! is_sha "$_a" || ! safe_rel "$_d"; then
      block "malformed payload manifest row in $1: $_a $_b $_c $_d"; continue
    fi
    case $_b in [0-7][0-7][0-7]|[0-7][0-7][0-7][0-7]) ;; *) block "bad mode '$_b' for $_c"; continue ;; esac
    case $_d in
      common/*|"profiles/$PROFILE/"*) ;;
      *) block "payload source outside common/ and the selected profile: $_d"; continue ;;
    esac
    _ph=$(pkg_sha "$_d") || { block "payload source not in package: $_d"; continue; }
    [ "$_ph" = "$_a" ] || { block "payload hash differs from package hash: $_d"; continue; }
    echo "$_a $_b $_c $_d" >> "$W/rows"
  done < "$PKG/$1"
}

derive_rows(){
  while read -r _h _p; do
    _t=
    case $_p in
      common/config/*) _r=config/${_p#common/config/} ;;
      common/*/*)
        _r=${_p#common/}; _r=${_r#*/}
        case $_r in bin/*|scripts/*|config/*) ;; *) continue ;; esac ;;
      "profiles/$PROFILE/display/platform-defaults.conf") _r=config/platform/defaults.conf ;;
      "profiles/$PROFILE/"*)
        _r=${_p#profiles/$PROFILE/}
        case $_r in bin/*|scripts/*|config/*) ;; *) continue ;; esac ;;
      *) continue ;;
    esac
    echo "$_h $(kind_mode "$_r") $LNEW/$_r $_p" >> "$W/rows"
  done < "$W/pkg.sums"
}

payload_target_ok(){
  case $1 in
    "$LNEW"/*|/mnt/app/eso/lib/*|/mnt/app/eso/hmi/lsd/jars/*) rebase "$1" >/dev/null ;;
    *) return 1 ;;
  esac
}

# stock_source TARGET STOCKSHA: path of verified stock bytes (own receipt, then legacy kit backup).
stock_source(){
  _rf=$OWN/$(own_name "$1").owned
  if [ -f "$_rf" ] && [ "$(getkey "$_rf" stock_sha256)" = "$2" ]; then
    _sb=$NEW/$(getkey "$_rf" stock_backup)
    if [ "$(sha_of "$_sb")" = "$2" ]; then echo "$_sb"; return 0; fi
  fi
  _lb=$ROOT/mibr-kit/backup$1
  if [ "$(sha_of "$_lb")" = "$2" ]; then echo "$_lb"; return 0; fi
  return 1
}

plan_payload(){
  : > "$W/rows"; : > "$W/payload.plan"
  if [ -f "$PKG/installer/config/payload.manifest" ]; then
    SRC_MODE=manifest
    append_manifest installer/config/payload.manifest
    if [ -f "$PKG/profiles/$PROFILE/payload.manifest" ]; then append_manifest "profiles/$PROFILE/payload.manifest"; fi
  else
    SRC_MODE=derived
    derive_rows
  fi
  KNOWN=$PKG/profiles/$PROFILE/integration/known-states.list
  _n=0
  while read -r _h _m _t _s; do
    _n=$((_n + 1))
    if ! payload_target_ok "$_t"; then block "payload target outside the allowed roots: $_t"; continue; fi
    if grep -qF " $_t " "$W/payload.plan"; then block "duplicate payload target $_t"; continue; fi
    _real=$(rebase "$_t")
    if [ -L "$_real" ] || { [ -e "$_real" ] && [ ! -f "$_real" ]; }; then block "$_t is not a regular file"; continue; fi
    _cur=$(sha_of "$_real")
    _act=; _cls=
    if [ "$_cur" = missing ]; then _act=create; _cls=absent
    elif [ "$_cur" = "$_h" ]; then _act=skip; _cls=package
    elif is_config "$_t"; then _act=keep; _cls=user-owned
    elif mf_find "$PREVMF" "$_t" && [ "$MF_SHA" = "$_cur" ]; then _act=replace; _cls=previous-own
    elif _lbl=$(known_state "$KNOWN" "$_t" "$_cur"); then _act=replace; _cls=known-previous:$_lbl
    else block "foreign file at $_t (sha256 $_cur is neither stock, package nor a known previous state)"; continue
    fi
    echo "$_act $_h $_m $_t $_s $_cls" >> "$W/payload.plan"
  done < "$W/rows"
  [ "$_n" -gt 0 ] || block "package carries no payload"
  # files of the previous install that this package no longer ships (inside mibr/, not config)
  : > "$W/obsolete.list"
  if [ -f "$PREVMF" ]; then
    while read -r _s _m _t _st _bk _pre; do
      case $_s in ''|'#'*) continue ;; esac
      under_new "$_t" || continue
      is_config "$_t" && continue
      grep -qF " $_t " "$W/payload.plan" || echo "$_t $_s" >> "$W/obsolete.list"
    done < "$PREVMF"
  fi
  say "  payload: $_n rows ($SRC_MODE): $(grep -c '^create' "$W/payload.plan") create, $(grep -c '^replace' "$W/payload.plan") replace, $(grep -c '^skip' "$W/payload.plan") unchanged, $(grep -c '^keep' "$W/payload.plan") kept (user-owned)"
}

plan_variants(){
  : > "$W/var.plan"
  VAR=$PKG/profiles/$PROFILE/integration/variants.list
  if [ ! -f "$VAR" ]; then say "  variants: none (no variants.list)"; return 0; fi
  _n=0
  while read -r _t _s _p _tf _ts _m _x; do
    case $_t in ''|'#'*) continue ;; esac
    _n=$((_n + 1))
    if [ -z "$_ts" ] || [ -n "$_x" ] || ! is_sha "$_s" || ! is_sha "$_p" || ! is_sha "$_ts"; then
      block "malformed variants row: $_t"; continue
    fi
    case $_t in
      /mnt/system/*|/mnt/app/eso/*) ;;
      *) block "variant target outside /mnt/system and /mnt/app/eso: $_t"; continue ;;
    esac
    if under_new "$_t" || ! _real=$(rebase "$_t"); then block "bad variant target $_t"; continue; fi
    case $_tf in "profiles/$PROFILE/integration/"*) ;; *) block "transform outside the profile integration dir: $_tf"; continue ;; esac
    _kh=$(pkg_sha "$_tf") || { block "transform not in package: $_tf"; continue; }
    [ "$_kh" = "$_ts" ] || { block "transform hash differs from variants.list: $_tf"; continue; }
    case $_tf in
      *.awk|*.sed|*.sh|*.ksh) ;;
      *) block "unsupported transform kind (TODO: .block/.patch semantics undefined): $_tf"; continue ;;
    esac
    if grep -qF " $_t " "$W/var.plan"; then block "duplicate variant target $_t"; continue; fi
    if [ -L "$_real" ] || [ ! -f "$_real" ]; then block "OEM target missing or not a regular file: $_t"; continue; fi
    _cur=$(sha_of "$_real")
    _in=; _cls=; _act=apply
    if [ "$_cur" = "$_p" ]; then
      _act=skip; _cls=package
    elif [ "$_cur" = "$_s" ]; then
      _in=$_real; _cls=stock
    elif _lbl=$(known_state "$KNOWN" "$_t" "$_cur") || { [ -f "$OWN/$(own_name "$_t").owned" ] && [ "$(getkey "$OWN/$(own_name "$_t").owned" patched_sha256)" = "$_cur" ] && _lbl=owned; }; then
      if _in=$(stock_source "$_t" "$_s"); then _cls=previous:$_lbl
      else block "$_t is in a previous state ($_lbl) but no verified stock bytes are available"; continue
      fi
    else
      block "foreign state at $_t (sha256 $_cur is neither stock, package nor a known previous state)"; continue
    fi
    _mode=$_m
    if [ -z "$_mode" ]; then _mode=$(mode_of "$_real") || { block "unrecognised file mode at $_t"; continue; }; fi
    case $_mode in [0-7][0-7][0-7]|[0-7][0-7][0-7][0-7]) ;; *) block "bad mode $_mode for $_t"; continue ;; esac
    _out=-
    if [ "$_act" = apply ]; then
      _out=$W/var.out.$_n
      case $_tf in
        *.awk) _tool=$(find_cmd awk) || { block "awk not found for $_tf"; continue; }
               "$_tool" -f "$PKG/$_tf" "$_in" > "$_out" 2>"$W/var.err" ;;
        *.sed) _tool=$(find_cmd sed) || { block "sed not found for $_tf"; continue; }
               "$_tool" -f "$PKG/$_tf" "$_in" > "$_out" 2>"$W/var.err" ;;
        *) "$SH_BIN" "$PKG/$_tf" < "$_in" > "$_out" 2>"$W/var.err" ;;
      esac
      _trc=$?
      if [ "$_trc" -ne 0 ]; then block "transform failed (exit $_trc) for $_t: $(head -1 "$W/var.err")"; continue; fi
      if [ "$(sha_of "$_out")" != "$_p" ]; then block "transform result for $_t has the wrong hash (expected $_p)"; continue; fi
    fi
    echo "$_n $_act $_t $_s $_p $_mode $_in $_cls $_out $_tf" >> "$W/var.plan"
    say "  variant $_t: $_cls -> $_act"
  done < "$VAR"
}

legacy_kit_evidence(){
  [ -f "$ROOT/mibr-kit/installed.manifest" ] && return 0
  [ -f "$ROOT/mibr-kit/installed-version.properties" ] && return 0
  [ -f "$NEW/version/installed-version.properties" ] && [ "$(getkey "$NEW/version/installed-version.properties" product)" = MIBR-CarPlay ] && return 0
  return 1
}

plan_lsd(){
  LSD_ACTION=none
  if [ -L "$LSD" ] || [ ! -f "$LSD" ]; then block "lsd.sh not found at $LLSD"; return 0; fi
  lsd_scan "$LSD"
  [ "$LSD_J9" = 1 ] || { block "found $LSD_J9 J9 start lines in lsd.sh, expected exactly 1"; return 0; }
  _fm=$(lsd_foreign_markers "$LSD") && { block "lsd.sh carries a development-install marker ('$_fm'); migrate that unit manually"; return 0; }
  if [ "$LSD_NB" != "$LSD_NE" ] || [ "$LSD_OB" != "$LSD_OE" ] || [ $((LSD_NB + LSD_OB)) -gt 1 ]; then
    block "broken or multiple MIBR block markers in lsd.sh (runtime $LSD_NB/$LSD_NE, kit $LSD_OB/$LSD_OE)"; return 0
  fi
  [ "$LSD_DSI" = 1 ] || { block "DSITRACER_ACTIVATED line found $LSD_DSI times, expected exactly 1"; return 0; }
  _dsi=$(grep '^DSITRACER_ACTIVATED=' "$LSD")
  case $_dsi in DSITRACER_ACTIVATED=no|DSITRACER_ACTIVATED=yes) ;; *) block "unexpected DSITRACER_ACTIVATED value"; return 0 ;; esac
  LSD_FLIP=0
  [ "$LSD_DSI_NO" = 1 ] && LSD_FLIP=1
  if [ "$LSD_OB" = 1 ]; then
    _bs=$(lsd_body_sha "$LSD")
    if [ -f "$OWN/lsd-block.owned" ]; then _why=receipt
    elif known_state "$PKG/installer/config/known-lsd-blocks.list" "$_bs" "$_bs" >/dev/null 2>&1; then _why=known-content
    elif _kl=$(grep -v '^#' "$PKG/installer/config/known-lsd-blocks.list" 2>/dev/null | grep "^$_bs " | head -1) && [ -n "$_kl" ]; then _why=known-content
    elif legacy_kit_evidence; then _why=legacy-kit-state
    else block "legacy MIBR-KIT block in lsd.sh without ownership proof (no receipt, unknown content, no kit state)"; return 0
    fi
    say "  lsd.sh: legacy MIBR-KIT block ours by $_why, will be replaced in place"
  elif [ "$LSD_NB" = 1 ]; then
    say "  lsd.sh: MIBR block present, will be replaced in place"
  else
    say "  lsd.sh: no MIBR block, will be inserted before the J9 line"
  fi
  _dsiarg=keep
  [ "$LSD_DSI_NO" = 1 ] && _dsiarg=yes
  lsd_filter "$LSD" "$W/lsd.new" install "$_dsiarg" || { block "cannot build the new lsd.sh"; return 0; }
  lsd_scan "$W/lsd.new"
  if [ "$LSD_J9" != 1 ] || [ "$LSD_NB" != 1 ] || [ "$LSD_NE" != 1 ] || [ "$LSD_OB" != 0 ] || [ "$LSD_OE" != 0 ]; then
    block "new lsd.sh failed the structure check (J9 $LSD_J9, block $LSD_NB/$LSD_NE)"; return 0
  fi
  # round trip: removing our block from old and new must give identical foreign content
  lsd_filter "$LSD" "$W/lsd.rt1" remove no && lsd_filter "$W/lsd.new" "$W/lsd.rt2" remove no \
    && [ "$(sha_of "$W/lsd.rt1")" = "$(sha_of "$W/lsd.rt2")" ] || { block "round-trip check of the new lsd.sh failed (foreign content would change)"; return 0; }
  LSD_PRE=$(sha_of "$LSD")
  LSD_POST=$(sha_of "$W/lsd.new")
  LSD_MODE=$(mode_of "$LSD") || { block "unrecognised file mode at lsd.sh"; return 0; }
  if [ "$LSD_PRE" = "$LSD_POST" ]; then LSD_ACTION=skip; else LSD_ACTION=apply; fi
}

plan_migration(){
  LEGACY_PRESENT=0
  for _d in altscreen-u2 mibr-kit mibr-v3 mibr-rgi; do [ -d "$ROOT/$_d" ] && LEGACY_PRESENT=1; done
  for _f in "$ROOT"/mibr-*.enabled; do [ -e "$_f" ] && LEGACY_PRESENT=1; done
  "$SH_BIN" "$PKG/installer/lib/migrate-root.ksh" plan --app "$APP" > "$W/mig.plan" 2>&1
  _mrc=$?
  cat "$W/mig.plan" >> "${LOG:-/dev/null}" 2>/dev/null
  if [ "$_mrc" -ne 0 ]; then
    block "root migration plan failed (exit $_mrc): $(tail -1 "$W/mig.plan")"
  else
    say "  migration plan: $(grep -c '^migrate ' "$W/mig.plan") to copy, $(grep -c '^skip-equal ' "$W/mig.plan") equal, legacy present=$LEGACY_PRESENT, $(grep '^legacy_disabled=' "$W/mig.plan" | head -1)"
  fi
}

plan_space(){
  _need=$((4096))
  _kb=${MIBR_FREE_KB:-}
  if [ -z "$_kb" ]; then
    set -- $(df -k "$APP" 2>/dev/null | tail -1)
    _kb=${4:-}
  fi
  case $_kb in
    ''|*[!0-9]*) warn "free space on $APP could not be determined" ;;
    *) if [ "$_kb" -lt "$_need" ]; then block "only $_kb KiB free on $APP (need $_need)"; else ok "free space $_kb KiB"; fi ;;
  esac
}

plan_apply(){
  say "[4] plan"
  plan_payload
  plan_variants
  plan_lsd
  plan_migration
  plan_space
  if [ "$SW" = 1 ]; then
    block "--authorize-single-writer: the target path of the single-writer gate is undecided (registry storage group boot.single_writer_gate has target 'tbd'); nothing is created. TODO owner decision"
  fi
}

# ---------------------------------------------------------------- writes
bk_row(){ # TARGET: sets BK_KIND BK_PRE BK_POST BK_MODE BK_REL from the MANIFEST
  BK_KIND=; BK_PRE=; BK_POST=; BK_MODE=; BK_REL=
  [ -f "$BKM" ] || return 1
  while read -r bk_k bk_t bk_pre bk_post bk_m bk_r; do
    if [ "$bk_t" = "$1" ]; then BK_KIND=$bk_k; BK_PRE=$bk_pre; BK_POST=$bk_post; BK_MODE=$bk_m; BK_REL=$bk_r; return 0; fi
  done < "$BKM"
  return 1
}

step_migrate(){
  say "[5] root migration"
  mkdir -p "$NEW" || die 30 "cannot create $NEW"
  MIBR_MIGRATE_NO_MOUNT=1 MIBR_LOCK_FILE="$LOCK.migrate" MIBR_SHA256="$SHA" \
    "$SH_BIN" "$PKG/installer/lib/migrate-root.ksh" run --app "$APP" --id "$ID" > "$W/mig.out" 2>&1
  _mrc=$?
  cat "$W/mig.out" >> "${LOG:-/dev/null}" 2>/dev/null
  tail -3 "$W/mig.out"
  [ "$_mrc" -eq 0 ] || die 20 "root migration failed (exit $_mrc); the kill switch stays as migrate-root left it"
}

step_backup(){
  say "[5b] backups"
  BK=$NEW/backup/$ID/oem
  BKM=$BK/MANIFEST
  mkdir -p "$BK/pre" "$BK/stock" || die 30 "cannot create $BK"
  : > "$W/bk.cand"
  while read -r _act _s _m _t _src _cls; do
    case $_act in replace|create) under_new "$_t" || echo "payload $_t $_s $_m - -" >> "$W/bk.cand" ;; esac
  done < "$W/payload.plan"
  while read -r _n _act _t _s _p _m _in _cls _out _tf; do
    [ "$_act" = apply ] || continue
    if [ "$_in" = "$(rebase "$_t")" ]; then echo "variant $_t $_p $_m - -" >> "$W/bk.cand"
    else echo "variant $_t $_p $_m $_in $_s" >> "$W/bk.cand"; fi
  done < "$W/var.plan"
  if [ "$LSD_ACTION" = apply ]; then echo "lsd $LLSD $LSD_POST $LSD_MODE - -" >> "$W/bk.cand"; fi
  : > "$W/bk.new"
  while read -r _k _t _post _m _ssrc _ssha; do
    _real=$(rebase "$_t"); _rel=${_t#/}
    if [ -n "$_ssrc" ] && [ "$_ssrc" != - ]; then
      _sb=$BK/stock/$_rel
      if [ "$(sha_of "$_sb")" != "$_ssha" ]; then
        mkdir -p "${_sb%/*}" && cp "$_ssrc" "$_sb" && [ "$(sha_of "$_sb")" = "$_ssha" ] || die 30 "stock backup failed for $_t"
      fi
    fi
    bk_row "$_t" && continue
    _cur=$(sha_of "$_real")
    if [ "$_cur" = missing ]; then
      echo "$_k $_t absent $_post $_m -" >> "$W/bk.new"
    else
      mkdir -p "$BK/pre/${_rel%/*}" && cp "$_real" "$BK/pre/$_rel" && [ "$(sha_of "$BK/pre/$_rel")" = "$_cur" ] || die 30 "backup failed for $_t"
      echo "$_k $_t $_cur $_post $_m pre/$_rel" >> "$W/bk.new"
    fi
  done < "$W/bk.cand"
  { [ -f "$BKM" ] && cat "$BKM"; cat "$W/bk.new"; } > "$W/bk.merged"
  put "$W/bk.merged" "$BKM" "$(sha_of "$W/bk.merged")" 644 || die 30 "cannot write backup manifest"
  sync
  ok "backup manifest $(grep -c . "$BKM") rows"
}

step_payload(){
  say "[6] payload"
  _first=1
  while read -r _act _h _m _t _s _cls; do
    case $_act in create|replace) ;; *) continue ;; esac
    _real=$(rebase "$_t")
    put "$PKG/$_s" "$_real" "$_h" "$_m" || die 30 "cannot install $_t"
    if [ "$_first" = 1 ]; then _first=0; inject payload_mid; fi
  done < "$W/payload.plan"
  while read -r _t _s; do
    _real=$(rebase "$_t")
    if [ "$(sha_of "$_real")" = "$_s" ]; then rm -f "$_real" || die 30 "cannot remove obsolete $_t"; say "  removed obsolete $_t"; fi
  done < "$W/obsolete.list"
}

write_variant_receipt(){ # n target stock patched mode
  _rn=$(own_name "$2")
  case $_rn in *[!A-Za-z0-9._-]*) die 30 "unusable receipt name for $2" ;; esac
  _rel=${2#/}
  if [ -f "$BK/stock/$_rel" ]; then _sbk=backup/$ID/oem/stock/$_rel
  else
    bk_row "$2" && [ "$BK_PRE" = "$3" ] || die 30 "no stock backup for $2"
    _sbk=backup/$ID/oem/$BK_REL
  fi
  [ "$(sha_of "$NEW/$_sbk")" = "$3" ] || die 30 "stock backup of $2 does not hash to the stock sha"
  mkdir -p "$OWN" || die 30 "cannot create ownership dir"
  {
    echo "kind=variant"
    echo "target=$2"
    echo "install_id=$ID"
    echo "stock_sha256=$3"
    echo "patched_sha256=$4"
    echo "mode=$5"
    echo "stock_backup=$_sbk"
  } | put_text "$OWN/$_rn.owned" 644 || die 30 "cannot write ownership receipt for $2"
}

step_variants(){
  say "[7] OEM integration"
  _first=1
  while read -r _n _act _t _s _p _m _in _cls _out _tf; do
    [ "$_act" = apply ] || continue
    write_variant_receipt "$_n" "$_t" "$_s" "$_p" "$_m"
    if [ "$_first" = 1 ]; then _first=0; inject variants_mid; fi
    mnt_rw "$(rebase "$_t")" || die 12 "cannot remount for $_t"
    put "$_out" "$(rebase "$_t")" "$_p" "$_m" || die 30 "cannot write $_t"
    say "  patched $_t"
  done < "$W/var.plan"
}

step_defaults(){
  say "[8] defaults"
  DR=$NEW/version/install-defaults.receipt
  if [ -f "$DR" ]; then ok "not a first install (defaults receipt present): defaults untouched"; return 0; fi
  mkdir -p "$NEW/version" || die 30 "cannot create version dir"
  : > "$W/def.rows"
  if [ "$LEGACY_PRESENT" = 1 ]; then
    echo "skipped=legacy-install-present" >> "$W/def.rows"
    ok "upgrade from a legacy install: no defaults written"
  else
    for _d in parity-drive:mibr-parity-drive.enabled cpvc:mibr-cpvc.enabled; do
      _f=$NEW/config/features/${_d#*:}
      if [ -e "$_f" ]; then echo "present ${_d#*:}" >> "$W/def.rows"; continue; fi
      printf '1\n' > "$W/def.val"
      put "$W/def.val" "$_f" "$(sha_of "$W/def.val")" 644 || die 30 "cannot create default ${_d#*:}"
      echo "created $LNEW/config/features/${_d#*:} $(sha_of "$_f")" >> "$W/def.rows"
    done
    echo "not-written=autodirect-value,single-writer-gate (target paths undecided)" >> "$W/def.rows"
  fi
  put "$W/def.rows" "$DR" "$(sha_of "$W/def.rows")" 644 || die 30 "cannot write defaults receipt"
}

step_receipts(){ # $1 = state
  say "[9] receipts ($1)"
  mkdir -p "$NEW/version" "$OWN" || die 30 "cannot create version dirs"
  if [ "$1" = pending ]; then
    # installed.manifest: sha mode target state backup-rel pre-sha
    { echo "# sha256 mode target state backup presha   (install $ID)"
      while read -r _act _h _m _t _s _cls; do
        _st=same; _bk=-; _pre=-
        if is_config "$_t"; then
          case $_act in
            create) _st=created ;;
            keep) _st=kept ;;
            skip) _st=created; mf_find "$PREVMF" "$_t" && _st=$MF_STATE ;;
          esac
        elif under_new "$_t"; then
          case $_act in create|replace) _st=new ;; skip) _st=new; mf_find "$PREVMF" "$_t" && _st=$MF_STATE ;; esac
        else
          if bk_row "$_t" && [ "$BK_KIND" = payload ]; then
            if [ "$BK_PRE" = absent ]; then _st=new; else _st=replaced; _bk=backup/$ID/oem/$BK_REL; _pre=$BK_PRE; fi
          elif mf_find "$PREVMF" "$_t"; then _st=$MF_STATE; _bk=$MF_BK; _pre=$MF_PRE
          fi
        fi
        echo "$_h $_m $_t $_st $_bk $_pre"
      done < "$W/payload.plan"
      # carried rows of the previous install outside mibr/ that this package no longer lists
      if [ -f "$PREVMF" ]; then
        while read -r _s _m _t _st _bk _pre; do
          case $_s in ''|'#'*) continue ;; esac
          under_new "$_t" && continue
          grep -qF " $_t " "$W/payload.plan" || echo "$_s $_m $_t $_st $_bk $_pre"
        done < "$PREVMF"
      fi
    } > "$W/installed.manifest"
    put "$W/installed.manifest" "$PREVMF" "$(sha_of "$W/installed.manifest")" 644 || die 30 "cannot write installed.manifest"
    # components.manifest (MIBR_COMPONENTS/1: id|version|sha256|size|path)
    { echo "MIBR_COMPONENTS/1"
      while read -r _s _m _t _st _bk _pre; do
        case $_s in ''|'#'*) continue ;; esac
        case $_t in "$LNEW"/bin/*) ;; *) continue ;; esac
        _real=$(rebase "$_t")
        echo "${_t##*/}|$PKGVER|$(sha_of "$_real")|$(size_of "$_real")|$_t"
      done < "$PREVMF"
      echo "end=1"
    } > "$W/components.manifest"
    put "$W/components.manifest" "$NEW/version/components.manifest" "$(sha_of "$W/components.manifest")" 644 || die 30 "cannot write components.manifest"
    _brand=GENERIC
    case $PROFILE in skoda-*) _brand=SKODA ;; seat-*) _brand=SEAT ;; esac
    { echo "identity_schema=1"
      echo "product=MIBR-CarPlay"
      echo "product_version=$PKGVER"
      echo "target_profile_id=$PROFILE"
      echo "target_brand=$_brand"
      echo "identity_stage=installed"
      echo "package_sha256=$PKGSHA"
      echo "install_id=$ID"
    } > "$W/ivp"
    put "$W/ivp" "$NEW/version/installed-version.properties" "$(sha_of "$W/ivp")" 644 || die 30 "cannot write installed-version.properties"
  fi
  { echo "install_id=$ID"
    echo "state=$1"
    echo "profile=$PROFILE"
    echo "package_sha256=$PKGSHA"
    echo "package_version=$PKGVER"
    echo "jxe_sha256=$(sha_of "$JXE")"
    echo "train=$TRAIN"
    echo "legacy_present=$LEGACY_PRESENT"
    echo "payload_rows=$(grep -c . "$W/payload.plan")"
    echo "variants=$(grep -c . "$W/var.plan")"
    echo "lsd_block=MIBR-RUNTIME"
  } > "$W/ir"
  put "$W/ir" "$NEW/version/install-$ID.receipt" "$(sha_of "$W/ir")" 644 || die 30 "cannot write install receipt"
}

step_lsd(){
  say "[7b] lsd.sh hook"
  case $LSD_ACTION in
    skip) ok "lsd.sh already carries the current block" ;;
    apply)
      bk_row "$LLSD" || die 30 "no backup row for lsd.sh"
      _flip=$LSD_FLIP
      [ -f "$OWN/lsd-block.owned" ] && [ "$(getkey "$OWN/lsd-block.owned" dsitracer_flipped)" = 1 ] && _flip=1
      lsd_body_sha "$W/lsd.new" >/dev/null
      { echo "kind=lsd-block"
        echo "target=$LLSD"
        echo "install_id=$ID"
        echo "marker=MIBR-RUNTIME"
        echo "pre_sha256=$BK_PRE"
        echo "post_sha256=$LSD_POST"
        echo "mode=$LSD_MODE"
        echo "dsitracer_flipped=$_flip"
        echo "backup=backup/$ID/oem/$BK_REL"
      } | put_text "$OWN/lsd-block.owned" 644 || die 30 "cannot write lsd ownership receipt"
      inject before_lsd_write
      mnt_rw "$LSD" || die 12 "cannot remount for lsd.sh"
      put "$W/lsd.new" "$LSD" "$LSD_POST" "$LSD_MODE" || die 30 "cannot write lsd.sh"
      lsd_scan "$LSD"
      [ "$LSD_J9" = 1 ] && [ "$LSD_NB" = 1 ] && [ "$LSD_OB" = 0 ] || die 30 "lsd.sh failed the post-write structure check"
      say "  lsd.sh hook installed" ;;
  esac
}

apply_main(){
  plan_apply
  if [ "$BLOCKS" -gt 0 ]; then die 10 "$BLOCKS BLOCK(s); nothing was written"; fi
  say "[5-10] writing"
  mnt_rw "$NEW" || die 12 "cannot remount $APP read-write"
  [ -z "$(cat "$W/var.plan")" ] || mnt_rw "$SYSTEM/x" || die 12 "cannot remount $SYSTEM read-write"
  step_migrate; inject after_migrate
  step_backup; inject after_backup
  step_payload; inject after_payload
  step_variants; inject after_variants
  step_defaults; inject after_defaults
  step_receipts pending; inject after_receipts
  step_lsd; inject after_lsd
  step_receipts complete
  _vo=$("$SH_BIN" "$PKG/installer/lib/migrate-root.ksh" verify --app "$APP" --id "$ID" 2>&1)
  case $_vo in
    *"install-in-progress"*) die 20 "migration kill switch still install-in-progress: $_vo" ;;
    *MIBR_MIGRATE_VERIFY=OK*) ok "migration verify" ;;
    *) warn "migration verify: $(echo "$_vo" | tail -2)" ;;
  esac
  inject final
  sync
  say "MIBR_INSTALL=OK id=$ID profile=$PROFILE warnings=$WARNS"
  say "REBOOT_REQUIRED=YES"
}

check_main(){
  select_profile
  plan_apply
  if [ "$BLOCKS" -gt 0 ]; then
    say "MIBR_INSTALL=CHECK_BLOCKED blocks=$BLOCKS profile=$PROFILE"
    exit 10
  fi
  say "MIBR_INSTALL=CHECK_OK profile=$PROFILE id=$ID warnings=$WARNS"
}

# ---------------------------------------------------------------- uninstall
prune(){
  (
    [ -d "$1" ] || exit 0
    for _x in "$1"/* "$1"/.[!.]*; do
      if [ -d "$_x" ] && [ ! -L "$_x" ]; then prune "$_x"; fi
    done
    for _x in "$1"/* "$1"/.[!.]*; do
      if [ -e "$_x" ] || [ -L "$_x" ]; then exit 0; fi
    done
    rm -r "$1" 2>/dev/null
  )
}

un_plan(){
  say "[uninstall plan]"
  : > "$W/un.var"; UN_LSD=none
  # lsd.sh
  if [ -f "$LSD" ]; then
    lsd_scan "$LSD"
    if [ $((LSD_NB + LSD_OB)) -gt 1 ] || [ "$LSD_NB" != "$LSD_NE" ] || [ "$LSD_OB" != "$LSD_OE" ]; then
      block "broken or multiple MIBR block markers in lsd.sh"
    elif [ $((LSD_NB + LSD_OB)) = 0 ]; then
      UN_LSD=drop
    elif [ $((LSD_NB + LSD_OB)) = 1 ]; then
      _ours=
      if [ -f "$OWN/lsd-block.owned" ]; then _ours=receipt
      else
        _bs=$(lsd_body_sha "$LSD")
        if grep -v '^#' "$PKG/installer/config/known-lsd-blocks.list" 2>/dev/null | grep -q "^$_bs "; then _ours=known-content; fi
      fi
      if [ -n "$_ours" ]; then
        _flip=keep
        if [ -f "$OWN/lsd-block.owned" ] && [ "$(getkey "$OWN/lsd-block.owned" dsitracer_flipped)" = 1 ] && [ "$LSD_DSI_NO" = 0 ]; then _flip=no; fi
        lsd_filter "$LSD" "$W/lsd.un" remove "$_flip" || block "cannot build lsd.sh without the MIBR block"
        lsd_scan "$W/lsd.un"
        if [ "$LSD_J9" != 1 ] || [ $((LSD_NB + LSD_OB)) != 0 ]; then block "lsd.sh without the block fails the structure check"; fi
        UN_LSD=remove
        say "  lsd.sh: MIBR block ours by $_ours, will be removed"
      else
        warn "lsd.sh carries a MIBR block without ownership receipt or known content: left untouched"
      fi
    fi
  fi
  # OEM variants
  for _rf in "$OWN"/*.owned; do
    [ -f "$_rf" ] || continue
    [ "$(getkey "$_rf" kind)" = variant ] || continue
    _t=$(getkey "$_rf" target); _ss=$(getkey "$_rf" stock_sha256); _ps=$(getkey "$_rf" patched_sha256)
    _bk=$NEW/$(getkey "$_rf" stock_backup); _m=$(getkey "$_rf" mode)
    _real=$(rebase "$_t") || { block "bad target in $_rf"; continue; }
    _cur=$(sha_of "$_real")
    if [ "$_cur" = "$_ps" ]; then
      if [ "$(sha_of "$_bk")" != "$_ss" ]; then block "stock backup of $_t is missing or damaged"; continue; fi
      echo "restore $_t $_bk $_m $_rf" >> "$W/un.var"
      say "  variant $_t: will be restored to stock"
    elif [ "$_cur" = "$_ss" ]; then
      echo "drop $_t - - $_rf" >> "$W/un.var"
      say "  variant $_t: already stock, receipt will be dropped"
    else
      block "$_t was changed after install (sha256 $_cur): not restoring over foreign bytes"
    fi
  done
  # payload
  : > "$W/un.pay"
  if [ -f "$PREVMF" ]; then
    while read -r _s _m _t _st _bk _pre; do
      case $_s in ''|'#'*) continue ;; esac
      _real=$(rebase "$_t") || { block "bad target in installed.manifest: $_t"; continue; }
      _cur=$(sha_of "$_real")
      if under_new "$_t"; then
        case $_st in
          kept) continue ;;
          created) if [ "$_cur" = "$_s" ]; then echo "delete $_t - -" >> "$W/un.pay"; elif [ "$_cur" != missing ]; then warn "kept user-modified config $_t"; fi ;;
          *) if [ "$_cur" = "$_s" ]; then echo "delete $_t - -" >> "$W/un.pay"; elif [ "$_cur" != missing ]; then warn "kept modified payload file $_t"; fi ;;
        esac
      else
        case $_st in
          new) if [ "$_cur" = "$_s" ]; then echo "delete $_t - -" >> "$W/un.pay"; elif [ "$_cur" != missing ]; then warn "kept modified file $_t"; fi ;;
          replaced)
            if [ "$_cur" = "$_s" ]; then
              if [ "$(sha_of "$NEW/$_bk")" != "$_pre" ]; then block "backup of replaced $_t is missing or damaged"; else echo "restore $_t $NEW/$_bk $_m" >> "$W/un.pay"; fi
            elif [ "$_cur" != "$_pre" ]; then warn "kept modified file $_t"; fi ;;
        esac
      fi
    done < "$PREVMF"
  fi
  say "  payload: $(grep -c '^delete' "$W/un.pay") delete, $(grep -c '^restore' "$W/un.pay") restore"
}

un_apply(){
  mnt_rw "$NEW" || die 12 "cannot remount $APP read-write"
  [ ! -s "$W/un.var" ] || mnt_rw "$SYSTEM/x" || die 12 "cannot remount $SYSTEM read-write"
  # 1. hook first: the unit stops loading MIBR before anything it needs disappears
  if [ "$UN_LSD" = remove ]; then
    lsd_scan "$W/lsd.un"
    _mode=$(mode_of "$LSD") || die 30 "unrecognised lsd.sh mode"
    mnt_rw "$LSD" || die 12 "cannot remount for lsd.sh"
    put "$W/lsd.un" "$LSD" "$(sha_of "$W/lsd.un")" "$_mode" || die 30 "cannot write lsd.sh"
    say "  lsd.sh block removed"
  fi
  inject un_after_lsd
  if [ "$UN_LSD" != none ]; then rm -f "$OWN/lsd-block.owned"; fi
  # 2. OEM variants back to stock
  while read -r _a _t _bk _m _rf; do
    case $_a in
      restore) mnt_rw "$(rebase "$_t")" || die 12 "remount"
               put "$_bk" "$(rebase "$_t")" "$(sha_of "$_bk")" "$_m" || die 30 "cannot restore $_t"
               say "  restored $_t" ;;
    esac
    rm -f "$_rf"
  done < "$W/un.var"
  inject un_after_variants
  # 3. payload
  while read -r _a _t _bk _m; do
    case $_a in
      delete) rm -f "$(rebase "$_t")" || die 30 "cannot remove $_t" ;;
      restore) put "$_bk" "$(rebase "$_t")" "$(sha_of "$_bk")" "$_m" || die 30 "cannot restore $_t" ;;
    esac
  done < "$W/un.pay"
  # 4. receipts and empty directories
  if [ -f "$NEW/version/install-defaults.receipt" ]; then
    while read -r _w _p _s; do
      [ "$_w" = created ] || continue
      _real=$(rebase "$_p")
      if [ "$(sha_of "$_real")" = "$_s" ]; then rm -f "$_real"; fi
    done < "$NEW/version/install-defaults.receipt"
  fi
  for _f in "$NEW"/version/install-*.receipt; do
    [ -f "$_f" ] || continue
    case $_f in */install-defaults.receipt) continue ;; esac
    _iid=$(getkey "$_f" install_id)
    if [ -n "$_iid" ] && [ -d "$NEW/backup/$_iid" ]; then cp "$_f" "$NEW/backup/$_iid/install.receipt.uninstalled" 2>/dev/null; fi
    rm -f "$_f"
  done
  rm -f "$NEW/version/install-defaults.receipt" "$NEW/version/components.manifest" "$NEW/version/installed-version.properties"
  rm -f "$OWN"/*.owned
  rm -f "$PREVMF"
  prune "$OWN"
  prune "$NEW/bin"; prune "$NEW/scripts"; prune "$NEW/config"
  if [ "$PURGE" = 1 ]; then
    rm -rf "$NEW" || die 30 "cannot purge $NEW"
    say "  purged $LNEW (backup and logs removed)"
  fi
  sync
  say "MIBR_INSTALL=UNINSTALL_OK warnings=$WARNS purge=$PURGE"
  say "REBOOT_REQUIRED=YES"
}

uninstall_main(){
  if [ ! -d "$NEW" ]; then say "MIBR_INSTALL=NOTHING_INSTALLED ($LNEW absent)"; return 0; fi
  un_plan
  if [ "$BLOCKS" -gt 0 ]; then die 10 "$BLOCKS BLOCK(s); nothing was written"; fi
  un_apply
}

# ---------------------------------------------------------------- rollback
rollback_main(){
  BK=$NEW/backup/$RB_ID/oem
  BKM=$BK/MANIFEST
  say "[rollback plan] id $RB_ID"
  [ -f "$BKM" ] || die 10 "no OEM backup manifest for install id $RB_ID ($BKM)"
  : > "$W/rb.plan"
  while read -r _k _t _pre _post _m _bkr; do
    case $_k in ''|'#'*) continue ;; esac
    _real=$(rebase "$_t") || { block "bad target $_t"; continue; }
    _cur=$(sha_of "$_real")
    [ "$_cur" = error ] && { block "cannot hash $_t"; continue; }
    if [ "$_cur" = "$_pre" ] || { [ "$_pre" = absent ] && [ "$_cur" = missing ]; }; then
      say "  $_k $_t: already in the pre-install state"; continue
    fi
    if [ "$_cur" = "$_post" ]; then
      if [ "$_pre" != absent ] && [ "$(sha_of "$BK/$_bkr")" != "$_pre" ]; then block "backup of $_t is missing or damaged"; continue; fi
      echo "$_k $_t $_pre $_m $_bkr" >> "$W/rb.plan"
      say "  $_k $_t: will be restored"
    else
      block "$_t changed after install $RB_ID (sha256 $_cur): not restoring over foreign bytes"
    fi
  done < "$BKM"
  if [ "$BLOCKS" -gt 0 ]; then die 10 "$BLOCKS BLOCK(s); nothing was written"; fi
  mnt_rw "$NEW" || die 12 "cannot remount $APP read-write"
  [ ! -s "$W/rb.plan" ] || mnt_rw "$SYSTEM/x" || die 12 "cannot remount $SYSTEM read-write"
  for _pass in other lsd; do
    while read -r _k _t _pre _m _bkr; do
      if [ "$_pass" = lsd ] && [ "$_k" != lsd ]; then continue; fi
      if [ "$_pass" = other ] && [ "$_k" = lsd ]; then continue; fi
      _real=$(rebase "$_t")
      if [ "$_pre" = absent ]; then rm -f "$_real" || die 30 "cannot remove $_t"
      else put "$BK/$_bkr" "$_real" "$_pre" "$_m" || die 30 "cannot restore $_t"; fi
      say "  restored $_t"
      [ "$_pass" = other ] && inject rb_mid
    done < "$W/rb.plan"
  done
  for _rf in "$OWN"/*.owned; do
    [ -f "$_rf" ] || continue
    if [ "$(getkey "$_rf" install_id)" = "$RB_ID" ]; then rm -f "$_rf"; fi
  done
  if [ -f "$NEW/version/install-$RB_ID.receipt" ]; then
    sed 's/^state=.*/state=rolled-back/' "$NEW/version/install-$RB_ID.receipt" > "$W/rb.receipt" \
      && put "$W/rb.receipt" "$NEW/version/install-$RB_ID.receipt" "$(sha_of "$W/rb.receipt")" 644 || die 30 "cannot update install receipt"
  fi
  sync
  say "MIBR_INSTALL=ROLLBACK_OK id=$RB_ID"
  say "REBOOT_REQUIRED=YES"
}

# ---------------------------------------------------------------- dispatch
case $MODE in
  check) check_main ;;
  apply) select_profile; apply_main ;;
  uninstall) uninstall_main ;;
  rollback) rollback_main ;;
esac
exit 0
