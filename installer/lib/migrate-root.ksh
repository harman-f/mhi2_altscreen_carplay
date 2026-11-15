#!/bin/sh
# M1 root migration: copy persistent DATA from legacy roots into the single
# new root as one fail-safe transaction. Location only, no format change.
# Legacy trees are never modified or deleted. No consumer is switched.
# Target: QNX 6.5 ksh / POSIX sh. No bashisms or GNU-only tools.
#
# Usage: migrate-root.ksh plan|run|verify|rollback [--app DIR] [--id ID] [--map FILE]
# Exit: 0 ok, 1 verify/rollback failure, 2 usage/map, 10 kill-switch/state,
#       11 lock held, 12 mount, 20 conflict, 30 copy/hash failure, 99 injected.
# Env: MIBR_SHA256, MIBR_MIGRATE_NO_MOUNT=1, MIBR_LOCK_FILE (default
#      /tmp/mibr-install.lock), MIBR_MIGRATE_FAIL_AT=c|d|e|f|h1|h2 (tests).

case $0 in */*) SELF_DIR=${0%/*} ;; *) SELF_DIR=. ;; esac
# The unit has no sha256sum of its own: the package helper, or MIBR_SHA256 (host tests).
SHA=${MIBR_SHA256:-}
if [ -z "$SHA" ]; then
  for _c in "$SELF_DIR/sha256sum" "$SELF_DIR/../bin/sha256sum" "$SELF_DIR/../../common/bin/sha256sum"; do
    if [ -x "$_c" ]; then SHA=$_c; break; fi
  done
fi
# Tools this script needs beyond the shell: cat cp mv rm mkdir grep mount sync sleep kill.
# No printf, sed, tr, awk, sort, uniq or find (absent from the MU1440 PATH).
LOCK=${MIBR_LOCK_FILE:-/tmp/mibr-install.lock}
APP=/mnt/app
ID=
MAP=$SELF_DIR/../config/root-migration.list
CMD=${1:-}
[ $# -gt 0 ] && shift

# Exact legacy single files (besides the mibr-*.enabled glob) that may be
# snapshotted and mapped. Explicit allowlist, not a wildcard.
LEGACY_SINGLES="mibr-deploy-most20-owned mibr-deploy-navignore-owned
mibr-direct-output-fps mibr-isotx2-gate-disable mibr-parity-statistics-enabled
mibr-parity-status-enabled mibr-carplay111-bit26.force-off
mibr-carplay111-bit26.force-on mibr-carplay111-nav.maneuverLayout
mibr-carplay111-nav.showCompass mibr-carplay111-nav.showETA
mibr-carplay111-nav.showSpeedLimit mibr-carplay111-nav.surface
mibr-carplay111-safearea.conf"
# Excluded from the legacy-unchanged checks of verify/rollback (still
# snapshotted): the legacy boot guard keeps incrementing this counter on
# every boot until consumers are switched, so it legitimately changes.
VERIFY_SKIP="mibr-kit/boot-count"
VSKIP=
# Migrated targets the installer rewrites in step [9] (receipts): the legacy
# copy is migrated first, then replaced by the new identity, so verify must not
# compare them with the legacy hash. The legacy bytes stay in the backup snapshot.
VERIFY_TARGET_SKIP="version/installed-version.properties version/components.manifest"

LOCKED=0
MOUNTED=0
TMPD=

cleanup(){
  rc=$?
  trap '' 0
  [ -n "$TMPD" ] && rm -rf "$TMPD"
  [ "$LOCKED" = 1 ] && rm -f "$LOCK"
  if [ "$MOUNTED" = 1 ]; then mount -ur "$APP" >/dev/null 2>&1; fi
  exit "$rc"
}
trap cleanup 0
trap 'exit 130' 1 2 15

die(){
  _rc=$1; shift
  echo "MIBR_MIGRATE=FAIL $*"
  exit "$_rc"
}

hashf(){
  set -- $("$SHA" "$1" 2>/dev/null)
  [ -n "${1:-}" ] || return 1
  echo "$1"
}

# out LINE: one line verbatim (no printf on the unit; echo interprets backslashes).
if [ "$( (print -r -- '-n a\tb') 2>/dev/null)" = '-n a\tb' ]; then
  out(){ print -r -- "$1"; }
else
  out(){
    cat <<MIBR_OUT_EOF
$1
MIBR_OUT_EOF
  }
fi

# kv FILE KEY: value of the first KEY=value line (empty if absent).
kv(){
  _kv=
  while IFS= read -r _kl || [ -n "$_kl" ]; do
    case $_kl in "$2="*) _kv=${_kl#*=}; break ;; esac
  done < "$1" 2>/dev/null
  out "$_kv"
}

# walkf DIR: every regular file below DIR (symlinks skipped), like find DIR -type f.
walkf(){
  for _e in "$1"/* "$1"/.[!.]*; do
    if [ -L "$_e" ]; then continue; fi
    if [ -d "$_e" ]; then ( walkf "$_e" ); elif [ -f "$_e" ]; then out "$_e"; fi
  done
}

first_line(){
  _l=
  read -r _l < "$1" 2>/dev/null
  echo "$_l"
}

inject(){
  [ "${MIBR_MIGRATE_FAIL_AT:-}" = "$1" ] || return 0
  echo "MIBR_MIGRATE=INJECTED_FAILURE at=$1"
  exit 99
}

while [ $# -gt 0 ]; do
  case $1 in
    --app) [ $# -ge 2 ] || die 2 "--app needs a value"; APP=$2; shift 2 ;;
    --id) [ $# -ge 2 ] || die 2 "--id needs a value"; ID=$2; shift 2 ;;
    --map) [ $# -ge 2 ] || die 2 "--map needs a value"; MAP=$2; shift 2 ;;
    *) die 2 "unknown option $1" ;;
  esac
done

ROOT=$APP/root
NEW=$ROOT/mibr
DIS=$NEW/state/boot/disabled

# /tmp on QNX MU1440 (= /dev/shmem) holds no directories: prefer /ramdisk, then /fs/tmpfs.
TMPD=
for _td in ${TMPDIR:-} /ramdisk /fs/tmpfs /tmp; do
  [ -n "$_td" ] && [ -d "$_td" ] || continue
  if mkdir "$_td/mibr-migrate.$$" 2>/dev/null; then TMPD=$_td/mibr-migrate.$$; break; fi
done
[ -n "$TMPD" ] || die 2 "cannot create temp dir"
[ -n "$SHA" ] || die 2 "no sha256 helper (package ships one; host: MIBR_SHA256)"

need_id(){
  [ -n "$ID" ] || die 2 "$CMD needs --id"
  case $ID in
    *[!A-Za-z0-9._-]*|.*) die 2 "bad id (allowed: A-Z a-z 0-9 . _ -)" ;;
  esac
}

safe_rel(){
  case $1 in
    ''|/*|*..*|*//*|*' '*|*/) return 1 ;;
  esac
  return 0
}

legacy_ok(){
  case $1 in
    altscreen-u2/*|mibr-kit/*|mibr-v3/*|mibr-rgi/*) return 0 ;;
    */*) return 1 ;;
    mibr-*.enabled) return 0 ;;
  esac
  for _s in $LEGACY_SINGLES; do [ "$1" = "$_s" ] && return 0; done
  return 1
}

# Validate the map and write $TMPD/map.list ("legacy new kind" per line).
load_map(){
  [ -r "$MAP" ] || die 2 "map not readable: $MAP"
  : > "$TMPD/map.list"; : > "$TMPD/map.c1"; : > "$TMPD/map.c2"
  while read -r m1 m2 m3 m4 m5; do
    case $m1 in ''|'#'*) continue ;; esac
    [ -n "$m3" ] && [ -z "$m5" ] || die 2 "map: bad line: $m1 $m2 $m3 $m4 $m5"
    case $m4 in ''|m2-pending) ;; *) die 2 "map: unknown marker '$m4' for $m1" ;; esac
    case $m3 in file|presence) ;; *) die 2 "map: unknown kind '$m3' for $m1" ;; esac
    safe_rel "$m1" || die 2 "map: unsafe legacy path: $m1"
    safe_rel "$m2" || die 2 "map: unsafe new path: $m2"
    legacy_ok "$m1" || die 2 "map: legacy path outside legacy roots: $m1"
    case $m2 in version/migration-*) die 2 "map: reserved target $m2" ;; esac
    grep -qxF -- "$m1" "$TMPD/map.c1" && die 2 "map: duplicate legacy path"
    grep -qxF -- "$m2" "$TMPD/map.c2" && die 2 "map: duplicate new path"
    out "$m1" >> "$TMPD/map.c1"
    out "$m2" >> "$TMPD/map.c2"
    out "$m1 $m2 $m3" >> "$TMPD/map.list"
  done < "$MAP"
}

# Relative list of every legacy file into $TMPD/legacy.list.
list_legacy(){
  : > "$TMPD/legacy.abs"
  for d in altscreen-u2 mibr-kit mibr-v3 mibr-rgi; do
    if [ -d "$ROOT/$d" ] && [ ! -L "$ROOT/$d" ]; then walkf "$ROOT/$d" >> "$TMPD/legacy.abs"; fi
  done
  for f in "$ROOT"/mibr-*.enabled; do
    if [ -f "$f" ]; then echo "$f" >> "$TMPD/legacy.abs"; fi
  done
  for f in $LEGACY_SINGLES; do
    if [ -f "$ROOT/$f" ]; then echo "$ROOT/$f" >> "$TMPD/legacy.abs"; fi
  done
  : > "$TMPD/legacy.list"
  while IFS= read -r p; do
    r=${p#"$ROOT"/}
    grep -qxF -- "$r" "$TMPD/legacy.list" || out "$r" >> "$TMPD/legacy.list"
  done < "$TMPD/legacy.abs"
}

# Relative paths that are neither mapped nor the handled kill switch.
list_unmapped(){
  : > "$TMPD/unmapped.list"
  while read -r u; do
    [ "$u" = "mibr-kit/disabled" ] && continue
    if grep -qxF -- "$u" "$TMPD/map.c1"; then continue; fi
    echo "$u" >> "$TMPD/unmapped.list"
  done < "$TMPD/legacy.list"
}

# verify_sums DIR SUMSFILE: every "<hash>  <rel>" line must match DIR/<rel>.
verify_sums(){
  vd=$1; vs=$2; vrc=0
  [ -f "$vs" ] || { echo "missing $vs"; return 1; }
  while IFS= read -r vl; do
    [ -n "$vl" ] || continue
    vh=${vl%%  *}; vp=${vl#*  }
    [ -n "$VSKIP" ] && [ "$vp" = "$VSKIP" ] && continue
    vc=$(hashf "$vd/$vp") || vc=
    if [ "$vc" != "$vh" ]; then echo "mismatch $vp"; vrc=1; fi
  done < "$vs"
  return $vrc
}

cp_into(){
  case $2 in */*) mkdir -p "${2%/*}" || return 1 ;; esac
  cp -p "$1" "$2"
}

acquire_lock(){
  n=0
  while [ $n -lt 3 ]; do
    if ( set -C; echo $$ > "$LOCK" ) 2>/dev/null; then LOCKED=1; return 0; fi
    op=$(cat "$LOCK" 2>/dev/null)
    if [ -z "$op" ]; then sleep 1; op=$(cat "$LOCK" 2>/dev/null); fi
    case $op in
      ''|*[!0-9]*) ;;
      *) if kill -0 "$op" 2>/dev/null; then
           echo "lock held by live pid $op"
           return 1
         fi ;;
    esac
    rm -f "$LOCK"
    n=$((n+1))
  done
  return 1
}

enter_rw(){
  acquire_lock || die 11 "install lock busy: $LOCK"
  if [ "${MIBR_MIGRATE_NO_MOUNT:-}" != 1 ]; then
    mount -uw "$APP" >/dev/null 2>&1 || die 12 "cannot remount $APP rw"
    MOUNTED=1
  fi
}

# write_disabled LINE1 [LINE2]: tmp + mv, sync, read back.
write_disabled(){
  mkdir -p "$NEW/state/boot" 2>/dev/null || return 1
  [ -d "$NEW/state/boot" ] || return 1
  wt=$DIS.tmp.$$
  if [ $# -ge 2 ]; then
    { out "$1"; out "$2"; } > "$wt" || { rm -f "$wt"; return 1; }
  else
    out "$1" > "$wt" || { rm -f "$wt"; return 1; }
  fi
  mv "$wt" "$DIS" || { rm -f "$wt"; return 1; }
  sync
  we=$(for wl in "$@"; do out "$wl"; done)
  wa=$(cat "$DIS" 2>/dev/null)
  [ "$we" = "$wa" ]
}

# Final kill-switch state from the receipt, then drop staging.
finalize(){
  ld=$(kv "$RC" legacy_disabled)
  if [ "$ld" = 1 ]; then
    txt=$(kv "$RC" legacy_disabled_text)
    write_disabled "migrated-disabled $ID: $txt" || die 10 "cannot write final kill switch"
  else
    rm -f "$DIS"
    [ ! -e "$DIS" ] || die 10 "cannot remove kill switch"
  fi
  inject h2
  rm -rf "$NEW/.staging-$ID"
  sync
}

# done_id: install id of a completed migration receipt, empty if none.
# The legacy trees are kept as migration source only (E4); once one migration
# completed, the new root is authoritative and is never migrated again.
done_id(){
  for _r in "$NEW"/version/migration-*.receipt; do
    [ -f "$_r" ] || continue
    grep -x 'state=complete' "$_r" >/dev/null 2>&1 || continue
    _i=${_r##*/migration-}; echo "${_i%.receipt}"; return 0
  done
  return 1
}

do_plan(){
  load_map
  list_legacy
  list_unmapped
  conf=0
  ld=0; pl=
  [ -e "$ROOT/mibr-kit/disabled" ] && ld=1
  if [ -e "$DIS" ]; then
    pl=$(first_line "$DIS")
    case $pl in install-in-progress*) ;; *) ld=1 ;; esac
  fi
  echo "legacy_disabled=$ld"
  # An interrupted run (receipt complete, kill switch still install-in-progress)
  # is not done yet: run --id finalizes it through its idempotence path.
  # The same holds for a leftover staging dir (interrupted after the kill switch
  # was finalized).
  case ${pl:-} in install-in-progress*) _ip=1 ;; *) _ip=0 ;; esac
  for _s in "$NEW"/.staging-*; do [ -e "$_s" ] && _ip=1; done
  if [ $_ip = 0 ] && _done=$(done_id); then
    echo "already-migrated $_done"
    # Map rows added after that migration: legacy source present, new target absent.
    # The installer copies these once (never over an existing target).
    while read -r l n k; do
      [ "$k" = file ] || continue
      # identity/receipt files belong to the current install, never to a late copy
      case $n in version/*) continue ;; esac
      [ -f "$ROOT/$l" ] && [ ! -L "$ROOT/$l" ] || continue
      [ -e "$NEW/$n" ] || [ -L "$NEW/$n" ] || echo "late $l $n"
    done < "$TMPD/map.list"
    echo "MIBR_MIGRATE_PLAN=DONE id=$_done"
    return 0
  fi
  while read -r l n k; do
    [ -f "$ROOT/$l" ] || continue
    if [ -e "$NEW/$n" ] || [ -L "$NEW/$n" ]; then
      a=$(hashf "$ROOT/$l"); b=$(hashf "$NEW/$n")
      if [ -n "$a" ] && [ "$a" = "$b" ]; then
        echo "skip-equal $l $n"
      else
        echo "conflict $l $n"; conf=1
      fi
    else
      echo "migrate $l $n"
    fi
  done < "$TMPD/map.list"
  while read -r u; do echo "unmapped $u"; done < "$TMPD/unmapped.list"
  if [ $conf = 1 ]; then echo "MIBR_MIGRATE_PLAN=CONFLICT"; return 20; fi
  echo "MIBR_MIGRATE_PLAN=OK"
  return 0
}

do_run(){
  need_id
  load_map
  enter_rw
  RC=$NEW/version/migration-$ID.receipt
  BK=$NEW/backup/$ID
  ST=$NEW/.staging-$ID

  # b. idempotence
  if [ -f "$RC" ] && grep -x 'state=complete' "$RC" >/dev/null 2>&1; then
    cur=
    [ -e "$DIS" ] && cur=$(first_line "$DIS")
    case $cur in
      "install-in-progress $ID") finalize ;;
      install-in-progress*) die 10 "another migration is in progress: $cur" ;;
    esac
    rm -rf "$ST"
    echo "MIBR_MIGRATE=ALREADY_COMPLETE id=$ID"
    return 0
  fi

  # c. kill switch first
  mkdir -p "$NEW/state/boot" 2>/dev/null && [ -d "$NEW/state/boot" ] \
    || die 10 "cannot create $NEW/state/boot"
  LEGACY_DISABLED=0; DTEXT=; PRIOR=
  if [ -e "$ROOT/mibr-kit/disabled" ]; then
    LEGACY_DISABLED=1; DTEXT=$(first_line "$ROOT/mibr-kit/disabled")
  fi
  if [ -e "$DIS" ] || [ -L "$DIS" ]; then
    cur=$(first_line "$DIS")
    case $cur in
      install-in-progress*)
        PRIOR=$(kv "$DIS" prior) ;;
      *) PRIOR=${cur:-disabled} ;;
    esac
    if [ -n "$PRIOR" ]; then
      LEGACY_DISABLED=1
      [ -n "$DTEXT" ] || DTEXT=${PRIOR#migrated-disabled *: }
    fi
  fi
  if [ -n "$PRIOR" ]; then
    write_disabled "install-in-progress $ID" "prior=$PRIOR" \
      || die 10 "cannot write kill switch"
  else
    write_disabled "install-in-progress $ID" || die 10 "cannot write kill switch"
  fi
  inject c

  # d. snapshot
  list_legacy
  mkdir -p "$BK/legacy" || die 30 "cannot create backup dir"
  : > "$BK/SHA256SUMS.tmp" || die 30 "cannot write backup sums"
  while read -r rel; do
    h=$(hashf "$ROOT/$rel") || die 30 "hash failed: $rel"
    cp_into "$ROOT/$rel" "$BK/legacy/$rel" || die 30 "snapshot copy failed: $rel"
    echo "$h  $rel" >> "$BK/SHA256SUMS.tmp"
  done < "$TMPD/legacy.list"
  mv "$BK/SHA256SUMS.tmp" "$BK/SHA256SUMS" || die 30 "cannot write SHA256SUMS"
  verify_sums "$BK/legacy" "$BK/SHA256SUMS" > "$TMPD/v.out" \
    || die 30 "snapshot verify failed: $(cat "$TMPD/v.out")"
  sync
  inject d

  # e. staging
  rm -rf "$ST"
  mkdir -p "$ST" || die 30 "cannot create staging"
  : > "$TMPD/staged.list"
  while read -r l n k; do
    [ -f "$ROOT/$l" ] || continue
    cp_into "$ROOT/$l" "$ST/$n" || die 30 "staging copy failed: $l"
    a=$(hashf "$ROOT/$l") || die 30 "hash failed: $l"
    b=$(hashf "$ST/$n") || die 30 "hash failed: staged $n"
    [ "$a" = "$b" ] || die 30 "staging hash mismatch: $l"
    echo "$l $n $a" >> "$TMPD/staged.list"
  done < "$TMPD/map.list"
  list_unmapped
  inject e

  # f. place, never overwrite
  cf=0
  while read -r l n h; do
    if [ -e "$NEW/$n" ] || [ -L "$NEW/$n" ]; then
      t=$(hashf "$NEW/$n") || t=
      if [ "$t" != "$h" ]; then echo "CONFLICT $n"; cf=1; fi
    fi
  done < "$TMPD/staged.list"
  [ $cf = 0 ] || die 20 "conflict: target differs from legacy (kill switch stays)"
  while read -r l n h; do
    if [ -e "$NEW/$n" ]; then continue; fi
    case $n in */*) mkdir -p "$NEW/${n%/*}" || die 30 "cannot create parent of $n" ;; esac
    mv "$ST/$n" "$NEW/$n" || die 30 "place failed: $n"
  done < "$TMPD/staged.list"
  sync
  inject f

  # g. boot counter moves only through the map (mibr-kit/boot-count row).

  # h. commit
  mkdir -p "$NEW/version" || die 30 "cannot create version dir"
  {
    echo "id=$ID"
    echo "state=complete"
    echo "legacy_disabled=$LEGACY_DISABLED"
    [ "$LEGACY_DISABLED" = 1 ] && echo "legacy_disabled_text=$DTEXT"
    while read -r l n h; do echo "migrated $l $n $h"; done < "$TMPD/staged.list"
    _nu=0; while read -r u; do _nu=$((_nu + 1)); done < "$TMPD/unmapped.list"
    echo "unmapped=$_nu"
    while read -r u; do echo "unmapped $u"; done < "$TMPD/unmapped.list"
  } > "$RC.tmp.$$" && mv "$RC.tmp.$$" "$RC" || die 30 "cannot write receipt"
  sync
  inject h1
  finalize
  echo "MIBR_MIGRATE=OK id=$ID legacy_disabled=$LEGACY_DISABLED"
  return 0
}

do_verify(){
  need_id
  RC=$NEW/version/migration-$ID.receipt
  vf=0
  if [ ! -f "$RC" ] || ! grep -x 'state=complete' "$RC" >/dev/null 2>&1; then
    echo "receipt missing or not complete"; vf=1
  else
    while read -r w l n h; do
      [ "$w" = migrated ] || continue
      case " $VERIFY_TARGET_SKIP " in *" $n "*) continue ;; esac
      t=$(hashf "$NEW/$n") || t=
      [ "$t" = "$h" ] || { echo "target mismatch $n"; vf=1; }
    done < "$RC"
  fi
  if [ -e "$DIS" ]; then
    pl=$(first_line "$DIS")
    case $pl in install-in-progress*) echo "kill switch still install-in-progress"; vf=1 ;; esac
  fi
  VSKIP=$VERIFY_SKIP
  verify_sums "$ROOT" "$NEW/backup/$ID/SHA256SUMS" > "$TMPD/v.out" || {
    while IFS= read -r vo; do out "legacy $vo"; done < "$TMPD/v.out"; vf=1; }
  if [ $vf = 0 ]; then echo "MIBR_MIGRATE_VERIFY=OK id=$ID"; return 0; fi
  echo "MIBR_MIGRATE_VERIFY=FAIL id=$ID"
  return 1
}

do_rollback(){
  need_id
  have=0
  for s in "$NEW"/.staging-*; do [ -e "$s" ] && have=1; done
  if [ $have = 1 ]; then
    enter_rw
    for s in "$NEW"/.staging-*; do [ -e "$s" ] && rm -rf "$s"; done
  fi
  if [ -f "$NEW/backup/$ID/SHA256SUMS" ]; then
    VSKIP=$VERIFY_SKIP
    if verify_sums "$ROOT" "$NEW/backup/$ID/SHA256SUMS" > "$TMPD/v.out"; then
      echo "legacy trees intact"
    else
      cat "$TMPD/v.out"; echo "MIBR_MIGRATE_ROLLBACK=LEGACY_CHANGED"; return 1
    fi
  else
    echo "no snapshot for id=$ID; legacy trees are never written by this tool"
  fi
  if [ -e "$DIS" ]; then echo "note: kill switch present: $(first_line "$DIS")"; fi
  echo "MIBR_MIGRATE_ROLLBACK=OK id=$ID"
  return 0
}

case $CMD in
  plan) do_plan; exit $? ;;
  run) do_run; exit $? ;;
  verify) do_verify; exit $? ;;
  rollback) do_rollback; exit $? ;;
  *) die 2 "usage: migrate-root.ksh plan|run|verify|rollback [--app DIR] [--id ID] [--map FILE]" ;;
esac
