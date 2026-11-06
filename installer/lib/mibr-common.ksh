#!/bin/sh
# Shared helpers of mibr-install.ksh and mibr-status.ksh. Sourced, never run.
# Target: QNX 6.5 pdksh / POSIX sh. Uses only grep, sort, cp, mv, rm, chmod, ls,
# mkdir, df, sync, mount, cat and the package's own sha256sum. No find, date,
# stat, diff, comm, xargs. awk/sed are located lazily (only transforms need them).
#
# Callers set PKG (extracted package root) before sourcing.
#
# Unit roots and their host-test overrides (logical unit path -> real path):
#   /mnt/app -> $MIBR_APP   /mnt/system -> $MIBR_SYSTEM   /mnt/app/eso -> $MIBR_ESO
#   /ifs     -> $MIBR_IFS

APP=${MIBR_APP:-/mnt/app}
SYSTEM=${MIBR_SYSTEM:-/mnt/system}
ESO=${MIBR_ESO:-$APP/eso}
IFS_ROOT=${MIBR_IFS:-/ifs}
ROOT=$APP/root
NEW=$ROOT/mibr
LNEW=/mnt/app/root/mibr
LLSD=/mnt/app/eso/hmi/lsd/lsd.sh
LSD=$ESO/hmi/lsd/lsd.sh
JXE=$IFS_ROOT/lsd.jxe
LOCK=${MIBR_LOCK_FILE:-/tmp/mibr-install.lock}

BEGIN_NEW="# MIBR-RUNTIME BEGIN"
END_NEW="# MIBR-RUNTIME END"
BEGIN_OLD="# MIBR-KIT BEGIN"
END_OLD="# MIBR-KIT END"

LOCKED=0
MNT_APP=0
MNT_SYS=0
RO_FAIL=0
BLOCKS=0
WARNS=0
LOG=${LOG:-}
W=

say(){
  echo "$*"
  if [ -n "$LOG" ]; then echo "$*" >> "$LOG" 2>/dev/null; fi
  return 0
}
warn(){ WARNS=$((WARNS + 1)); say "  WARN  $*"; }
block(){ BLOCKS=$((BLOCKS + 1)); say "  BLOCK $*"; }
ok(){ say "  OK    $*"; }
die(){
  _rc=$1; shift
  say "MIBR_INSTALL=FAIL $*"
  exit "$_rc"
}

# ---------------------------------------------------------------- mounts, lock, cleanup
no_mount(){
  [ "${MIBR_NO_MOUNT:-}" = 1 ] || [ "${MIBR_MIGRATE_NO_MOUNT:-}" = 1 ]
}

# mnt_rw REALPATH: remount the owning partition read-write once.
mnt_rw(){
  case $1 in
    "$SYSTEM"/*|"$SYSTEM")
      if [ "$MNT_SYS" = 0 ] && ! no_mount; then
        mount -uw "$SYSTEM" >/dev/null 2>&1 || return 1
        MNT_SYS=1
      fi ;;
    *)
      if [ "$MNT_APP" = 0 ] && ! no_mount; then
        mount -uw "$APP" >/dev/null 2>&1 || return 1
        MNT_APP=1
      fi ;;
  esac
  return 0
}

mnt_ro(){
  if [ "$MNT_SYS" = 1 ] || [ "$MNT_APP" = 1 ]; then
    sync || { say "  BLOCK sync failed before read-only restore"; RO_FAIL=1; }
  fi
  if [ "$MNT_SYS" = 1 ]; then
    if mount -ur "$SYSTEM" >/dev/null 2>&1; then MNT_SYS=0
    else say "  BLOCK $SYSTEM not back to read-only"; RO_FAIL=1; fi
  fi
  if [ "$MNT_APP" = 1 ]; then
    if mount -ur "$APP" >/dev/null 2>&1; then MNT_APP=0
    else say "  BLOCK $APP not back to read-only"; RO_FAIL=1; fi
  fi
}

cleanup(){
  _crc=$?
  trap '' 0
  mnt_ro
  if [ -n "$W" ]; then rm -rf "$W"; fi
  if [ "$LOCKED" = 1 ]; then rm -f "$LOCK"; fi
  if [ "$RO_FAIL" = 1 ] && [ "$_crc" -eq 0 ]; then
    say "MIBR_INSTALL=FAIL persistent filesystems could not be confirmed read-only"
    _crc=21
  fi
  exit "$_crc"
}

acquire_lock(){
  _n=0
  while [ "$_n" -lt 3 ]; do
    if ( set -C; echo $$ > "$LOCK" ) 2>/dev/null; then LOCKED=1; return 0; fi
    _op=$(cat "$LOCK" 2>/dev/null)
    if [ -z "$_op" ]; then sleep 1; _op=$(cat "$LOCK" 2>/dev/null); fi
    case $_op in
      ''|*[!0-9]*) ;;
      *) if kill -0 "$_op" 2>/dev/null; then say "lock held by live pid $_op"; return 1; fi ;;
    esac
    rm -f "$LOCK"
    _n=$((_n + 1))
  done
  return 1
}

mkwork(){
  W=${TMPDIR:-/tmp}/mibr-install.$$
  rm -rf "$W"
  mkdir "$W" 2>/dev/null || { W=; return 1; }
  return 0
}

# ---------------------------------------------------------------- small helpers
find_cmd(){
  _c=$1
  case $_c in
    */*) [ -x "$_c" ] && { echo "$_c"; return 0; } ;;
    *)
      _old=$IFS
      IFS=:
      for _d in /proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/armle/bin:/mnt/app/armle/usr/bin:$PATH; do
        [ -n "$_d" ] || continue
        if [ -x "$_d/$_c" ]; then IFS=$_old; echo "$_d/$_c"; return 0; fi
      done
      IFS=$_old ;;
  esac
  return 1
}

if [ -x /bin/ksh ]; then SH_BIN=/bin/ksh; else SH_BIN=sh; fi

is_sha(){
  case $1 in
    *[!0123456789abcdef]*) return 1 ;;
  esac
  [ ${#1} -eq 64 ]
}

safe_rel(){
  case $1 in
    ''|/*|*..*|*//*|*' '*|*/) return 1 ;;
  esac
  return 0
}

# Logical unit path -> real path (host tests relocate the roots).
rebase(){
  case $1 in
    *..*|*' '*) return 1 ;;
    /mnt/system/*) echo "$SYSTEM/${1#/mnt/system/}" ;;
    /mnt/app/eso/*) echo "$ESO/${1#/mnt/app/eso/}" ;;
    /mnt/app/*) echo "$APP/${1#/mnt/app/}" ;;
    /ifs/*) echo "$IFS_ROOT/${1#/ifs/}" ;;
    *) return 1 ;;
  esac
}

under_new(){ case $1 in "$LNEW"/*) return 0 ;; esac; return 1; }
is_config(){ case $1 in "$LNEW"/config/*) return 0 ;; esac; return 1; }

find_sha(){
  SHA=${MIBR_SHA256:-}
  if [ -z "$SHA" ]; then
    for _c in "$PKG/installer/bin/sha256sum" "$PKG/installer/sha256sum" "$PKG/installer/lib/sha256sum" "$PKG/common/bin/sha256sum"; do
      if [ -x "$_c" ]; then SHA=$_c; break; fi
    done
  fi
  if [ -z "$SHA" ]; then
    for _c in sha256sum /usr/bin/sha256sum /bin/sha256sum; do
      if command -v "$_c" >/dev/null 2>&1; then SHA=$_c; break; fi
    done
  fi
  [ -n "$SHA" ] || return 1
  export MIBR_SHA256="$SHA"
  return 0
}

# sha_of FILE: hash, or "missing" / "error".
sha_of(){
  if [ ! -f "$1" ]; then echo missing; return 0; fi
  set -- $("$SHA" "$1" 2>/dev/null)
  echo "${1:-error}"
}

# mode_of FILE: 755 / 644 / 600 (the only modes the unit's files use); else fail.
mode_of(){
  set -- $(ls -ld "$1" 2>/dev/null) || return 1
  case ${1:-} in
    -rwxr-xr-x) echo 755 ;;
    -rw-r--r--) echo 644 ;;
    -rw-------) echo 600 ;;
    *) return 1 ;;
  esac
}

size_of(){
  set -- $(ls -l "$1" 2>/dev/null)
  echo "${5:--}"
}

# getkey FILE KEY: value of the first KEY=value line (empty if absent).
getkey(){
  _gk=
  while IFS= read -r _gl || [ -n "$_gl" ]; do
    case $_gl in "$2="*) _gk=${_gl#*=}; break ;; esac
  done < "$1" 2>/dev/null
  echo "$_gk"
}

# put SRC DST SHA MODE: tmp + chmod + mv, read back.
put(){
  _pd=${2%/*}
  mkdir -p "$_pd" || return 1
  _pt=$2.mibr-tmp.$$
  cp "$1" "$_pt" && chmod "$4" "$_pt" && [ "$(sha_of "$_pt")" = "$3" ] && mv "$_pt" "$2" || { rm -f "$_pt"; return 1; }
  [ "$(sha_of "$2")" = "$3" ]
}

# put_text DST MODE: stdin -> tmp + mv (no hash check).
put_text(){
  _pd=${1%/*}
  mkdir -p "$_pd" || return 1
  _pt=$1.mibr-tmp.$$
  cat > "$_pt" && chmod "$2" "$_pt" && mv "$_pt" "$1" || { rm -f "$_pt"; return 1; }
}

# ---------------------------------------------------------------- package integrity
walk(){
  for _e in "$1"/* "$1"/.[!.]*; do
    if [ -L "$_e" ]; then echo "$_e"; continue; fi
    [ -e "$_e" ] || continue
    if [ -d "$_e" ]; then ( walk "$_e" ); else echo "$_e"; fi
  done
}

# verify_package: every PACKAGE.sha256 row matches, no unlisted or symlinked file,
# and the installer's own files are covered. Writes $W/pkg.sums ("hash path").
verify_package(){
  _ps=$PKG/PACKAGE.sha256
  [ -f "$_ps" ] || { say "PACKAGE_SHA256 missing"; return 1; }
  : > "$W/pkg.sums"
  _bad=0
  while IFS= read -r _l || [ -n "$_l" ]; do
    case $_l in ''|'#'*) continue ;; esac
    _h=${_l%%  *}
    _p=${_l#*  }
    if ! is_sha "$_h" || [ "$_l" != "$_h  $_p" ] || ! safe_rel "$_p"; then
      say "PACKAGE_SHA256 malformed row: $_l"; _bad=1; continue
    fi
    if [ "$(sha_of "$PKG/$_p")" != "$_h" ]; then say "PACKAGE_MISMATCH $_p"; _bad=1; continue; fi
    echo "$_h $_p" >> "$W/pkg.sums"
  done < "$_ps"
  for _r in installer/mibr-install.ksh installer/lib/mibr-common.ksh installer/lib/migrate-root.ksh \
            installer/select-profile.ksh installer/config/profiles.list installer/config/root-migration.list \
            installer/config/lsd-block.txt; do
    if ! grep -q " $_r\$" "$W/pkg.sums"; then say "PACKAGE_INCOMPLETE $_r is not covered by PACKAGE.sha256"; _bad=1; fi
  done
  walk "$PKG" > "$W/pkg.files"
  while IFS= read -r _f; do
    _rel=${_f#"$PKG"/}
    case $_rel in PACKAGE.sha256|mibr-install.log) continue ;; esac
    if [ -L "$_f" ]; then say "PACKAGE_SYMLINK $_rel"; _bad=1; continue; fi
    if ! grep -q " $_rel\$" "$W/pkg.sums"; then say "PACKAGE_UNLISTED $_rel"; _bad=1; fi
  done < "$W/pkg.files"
  [ "$_bad" = 0 ]
}

# pkg_sha PATH: recorded sha of a verified package file.
pkg_sha(){
  while read -r _ph _pp; do
    if [ "$_pp" = "$1" ]; then echo "$_ph"; return 0; fi
  done < "$W/pkg.sums"
  return 1
}

# ---------------------------------------------------------------- manifests and receipts
# mf_find FILE TARGET: sets MF_SHA MF_MODE MF_STATE MF_BK MF_PRE from an installed.manifest row.
mf_find(){
  MF_SHA=; MF_MODE=; MF_STATE=; MF_BK=; MF_PRE=
  [ -f "$1" ] || return 1
  while read -r mf_s mf_m mf_t mf_st mf_bk mf_pre; do
    case $mf_s in ''|'#'*) continue ;; esac
    if [ "$mf_t" = "$2" ]; then MF_SHA=$mf_s; MF_MODE=$mf_m; MF_STATE=$mf_st; MF_BK=$mf_bk; MF_PRE=$mf_pre; return 0; fi
  done < "$1"
  return 1
}

# known_state FILE TARGET SHA: label of a known-previous state, or fail.
known_state(){
  [ -f "$1" ] || return 1
  while read -r ks_t ks_s ks_l; do
    case $ks_t in ''|'#'*) continue ;; esac
    if [ "$ks_t" = "$2" ] && [ "$ks_s" = "$3" ]; then echo "${ks_l:-known}"; return 0; fi
  done < "$1"
  return 1
}

# ---------------------------------------------------------------- lsd.sh block handling
# lsd_scan FILE: sets LSD_J9 LSD_NB LSD_NE LSD_OB LSD_OE LSD_DSI LSD_DSI_NO.
lsd_scan(){
  LSD_J9=$(grep -c '^\$J9 ' "$1")
  LSD_NB=$(grep -c "^$BEGIN_NEW" "$1")
  LSD_NE=$(grep -c "^$END_NEW" "$1")
  LSD_OB=$(grep -c "^$BEGIN_OLD" "$1")
  LSD_OE=$(grep -c "^$END_OLD" "$1")
  LSD_DSI=$(grep -c '^DSITRACER_ACTIVATED=' "$1")
  LSD_DSI_NO=$(grep -c '^DSITRACER_ACTIVATED=no$' "$1")
}

emit_block(){
  printf '%s\n' "$BEGIN_NEW $BLOCKVER"
  while IFS= read -r _b || [ -n "$_b" ]; do printf '%s\n' "$_b"; done < "$BLOCKFILE"
  printf '%s\n' "$END_NEW"
}

# lsd_filter IN OUT MODE DSI: copy IN to OUT, handling only our MIBR block(s).
#   MODE install  replace the block in place (or insert before the single J9 line)
#   MODE remove   drop the block
#   DSI  keep | yes | no   value forced onto the DSITRACER_ACTIVATED line
# Needs BLOCKFILE and BLOCKVER for install. Foreign lines are copied verbatim.
lsd_filter(){
  _in=$1; _out=$2; _mode=$3; _dsi=$4
  _placed=0; _skip=0
  : > "$_out" || return 1
  while IFS= read -r _ln || [ -n "$_ln" ]; do
    if [ "$_skip" = 1 ]; then
      case $_ln in
        "$END_NEW"*|"$END_OLD"*) _skip=0 ;;
      esac
      continue
    fi
    case $_ln in
      "$BEGIN_NEW"*|"$BEGIN_OLD"*)
        _skip=1
        if [ "$_mode" = install ] && [ "$_placed" = 0 ]; then emit_block >> "$_out"; _placed=1; fi
        continue ;;
      DSITRACER_ACTIVATED=no|DSITRACER_ACTIVATED=yes)
        if [ "$_dsi" != keep ]; then _ln="DSITRACER_ACTIVATED=$_dsi"; fi ;;
      '$J9 '*)
        if [ "$_mode" = install ] && [ "$_placed" = 0 ]; then emit_block >> "$_out"; _placed=1; fi ;;
    esac
    printf '%s\n' "$_ln" >> "$_out"
  done < "$_in"
  [ "$_skip" = 0 ]
}

# lsd_body_sha FILE: hash of the lines between the markers of the (single) block;
# sets LSD_BODY_KIND to new or old.
lsd_body_sha(){
  : > "$W/body"
  _in=0; LSD_BODY_KIND=
  while IFS= read -r _ln || [ -n "$_ln" ]; do
    if [ "$_in" = 1 ]; then
      case $_ln in "$END_NEW"*|"$END_OLD"*) break ;; esac
      printf '%s\n' "$_ln" >> "$W/body"
      continue
    fi
    case $_ln in
      "$BEGIN_NEW"*) _in=1; LSD_BODY_KIND=new ;;
      "$BEGIN_OLD"*) _in=1; LSD_BODY_KIND=old ;;
    esac
  done < "$1"
  sha_of "$W/body"
}

# lsd_foreign_markers FILE: print the first development-install marker found.
lsd_foreign_markers(){
  [ -f "$PKG/installer/config/legacy-markers.list" ] || return 1
  while IFS= read -r _m || [ -n "$_m" ]; do
    case $_m in ''|'#'*) continue ;; esac
    if grep -qF -- "$_m" "$1"; then echo "$_m"; return 0; fi
  done < "$PKG/installer/config/legacy-markers.list"
  return 1
}
