#!/bin/ksh
set -u

SELF=$0
case "$SELF" in
  */*) ROOT=${SELF%/*} ;;
  *) ROOT=. ;;
esac
ROOT=$(cd "$ROOT" 2>/dev/null && pwd) || exit 2

PAYLOAD=$ROOT/payload
RUNTIME=$ROOT/runtime
SHA=${MIBR_SHA256:-$PAYLOAD/sha256sum}
TEE=${MIBR_TEE:-$PAYLOAD/tee}
MEDIA_ROOT=$ROOT
SESSION_HELPER=$RUNTIME/deployment/session.sh

[ -r "$SESSION_HELPER" ] || { echo "MIBR_INSTALL=FAIL missing_session_helper=$SESSION_HELPER"; exit 20; }
. "$SESSION_HELPER" || { echo "MIBR_INSTALL=FAIL cannot_source_session_helper"; exit 20; }

if [ "${MIBR_LOG_ACTIVE:-0}" != "1" ]; then
  [ -x "$SHA" ] || { echo "MIBR_INSTALL=FAIL missing_sha256_helper=$SHA"; exit 20; }
  [ -x "$TEE" ] || { echo "MIBR_INSTALL=FAIL missing_tee_helper=$TEE"; exit 20; }
  mibr_prepare_session install "$MEDIA_ROOT" "$TEE" "$SHA" || {
    echo "MIBR_INSTALL=FAIL cannot_create_sd_issue_log rc=$?"
    exit 20
  }
  echo "Logging complete install session to $MIBR_LOG_FILE"
  mibr_run_logged "$0" "$@"
  exit $?
fi

mibr_vehicle_summary || echo "WARN vehicle_summary_failed"

MEDIA_ROOT=$ROOT
MEDIA_RW=0
DST=/mnt/app/root/altscreen-u2
LSD=/mnt/app/eso/hmi/lsd/lsd.sh
APP_RW=0

media_rw(){
  [ "$MEDIA_RW" -eq 1 ] && return 0
  case "$MEDIA_ROOT" in
    /net/mmx/fs/*)
      mount -uw "$MEDIA_ROOT" 2>/dev/null || return 1
      ;;
  esac
  TEST="$MEDIA_ROOT/.mibr-altscreen-write-test.$$"
  touch "$TEST" 2>/dev/null || return 1
  [ -f "$TEST" ] || return 1
  rm -f "$TEST" 2>/dev/null || return 1
  MEDIA_RW=1
  return 0
}

app_rw(){
  [ "$APP_RW" -eq 1 ] && return 0
  mount -uw /mnt/app 2>/dev/null || return 1
  APP_RW=1
  return 0
}

app_ro(){
  if [ "$APP_RW" -eq 1 ]; then
    sync 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    APP_RW=0
  fi
}

cleanup(){
  app_ro
}
trap cleanup 0 1 2 15

EXPECTED_AIRPLAY=193a4fd9101ec2aa05e7159cfa307b96500810d379ca74a194f172adc13a46b5
EXPECTED_GEN2=094e3f1abfbf949f8c11b27e048e8213e5fc71178e62efd3c56deed8ee3bf8d8
EXPECTED_REMUX=b761a8741682e3cbc6e05f5fe1705475c34c4805d1cd1ce09333274a301e735e
EXPECTED_GATE=05673010a88c25022145ffb4e75d3715eaf686f4127ac188e91a52f512b9d957
EXPECTED_NAVIGNORE=b065bab0e1c58f8439a3bdd73d2d4cb6060cbac1c943e5b425425eb453c94b34
EXPECTED_MOST20=dbd45609fe4ba69948d39e9e649b224484f680f6aa7934b68c261a4d360ea5bb
EXPECTED_LSD_JXE=a55d9cfb69c5756f8202b7f7aa4079d4d5b637ae4c2fd0fe723f1d6816cbeea8

hashf(){
  set -- $("$SHA" "$1" 2>/dev/null)
  [ -n "${1:-}" ] || return 1
  echo "$1"
}

fail(){
  echo "MIBR_INSTALL=FAIL $*"
  app_ro
  exit 20
}

find_cmd(){
  C=$1
  case "$C" in
    */*) [ -x "$C" ] && { echo "$C"; return 0; } ;;
    *)
      OLDIFS=$IFS
      IFS=:
      for D in /proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/armle/bin:/mnt/app/armle/usr/bin; do
        [ -n "$D" ] || D=.
        if [ -x "$D/$C" ]; then
          IFS=$OLDIFS
          echo "$D/$C"
          return 0
        fi
      done
      IFS=$OLDIFS
      ;;
  esac
  return 1
}

require_cmds(){
  for C in "$@"; do
    find_cmd "$C" >/dev/null 2>&1 || fail "missing_required_command=$C"
  done
}

check_hash(){
  F=$1
  E=$2
  [ -r "$F" ] || fail "missing=$F"
  H=$(hashf "$F") || fail "hash_failed=$F"
  [ "$H" = "$E" ] || fail "hash_mismatch=$F expected=$E actual=$H"
  echo "PASS hash $F $H"
}

java_scan_state(){
  JARDIR=/mnt/app/eso/hmi/lsd/jars
  NAVJAR=$JARDIR/MIBR-NavIgnore.jar
  MOSTJAR=$JARDIR/MIBR-Most20FPS.jar
  JAVA_CONFLICT=0
  JAVA_NEEDS_PAYLOAD=0
  JAVA_OLD_DYNAMIC=0
  JAVA_EXACT_NAV_ACTIVE=0
  JAVA_EXACT_MOST20_ACTIVE=0
  JAVA_REASON=""

  NAVREFS=$(awk 'index($0,"MIBR-NavIgnore.jar"){n++} END{print n+0}' "$LSD" 2>/dev/null)
  MOSTREFS=$(awk 'index($0,"MIBR-Most20FPS.jar"){n++} END{print n+0}' "$LSD" 2>/dev/null)
  FOREIGNREFS=$(awk '
    index($0,"-Xbootclasspath/p:") && index($0,"/lsd/jars/") &&
      !index($0,"MIBR-NavIgnore.jar") && !index($0,"MIBR-Most20FPS.jar") {n++}
    END{print n+0}' "$LSD" 2>/dev/null)

  grep -Fq 'Find and append jar files' "$LSD" 2>/dev/null && JAVA_OLD_DYNAMIC=1

  NAVHASH=""
  MOSTHASH=""
  [ -r "$NAVJAR" ] && NAVHASH=$(hashf "$NAVJAR" 2>/dev/null)
  [ -r "$MOSTJAR" ] && MOSTHASH=$(hashf "$MOSTJAR" 2>/dev/null)

  [ "$NAVREFS" -gt 1 ] && { JAVA_CONFLICT=1; JAVA_REASON="$JAVA_REASON duplicate_navignore_ref"; }
  [ "$MOSTREFS" -gt 1 ] && { JAVA_CONFLICT=1; JAVA_REASON="$JAVA_REASON duplicate_most20_ref"; }
  [ "$FOREIGNREFS" -gt 0 ] && { JAVA_CONFLICT=1; JAVA_REASON="$JAVA_REASON foreign_bootclasspath_ref"; }
  [ "$JAVA_OLD_DYNAMIC" -eq 1 ] && { JAVA_CONFLICT=1; JAVA_REASON="$JAVA_REASON old_dynamic_jar_loader"; }

  [ "$NAVREFS" -eq 1 ] && [ "$NAVHASH" = "$EXPECTED_NAVIGNORE" ] && JAVA_EXACT_NAV_ACTIVE=1
  [ "$MOSTREFS" -eq 1 ] && [ "$MOSTHASH" = "$EXPECTED_MOST20" ] && JAVA_EXACT_MOST20_ACTIVE=1

  if [ "$NAVREFS" -gt 0 ]; then
    if [ "$NAVHASH" != "$EXPECTED_NAVIGNORE" ]; then
      JAVA_CONFLICT=1; JAVA_NEEDS_PAYLOAD=1; JAVA_REASON="$JAVA_REASON navignore_hash_or_file_mismatch"
    fi
  elif [ -r "$NAVJAR" ] && [ "$NAVHASH" != "$EXPECTED_NAVIGNORE" ]; then
    JAVA_CONFLICT=1; JAVA_NEEDS_PAYLOAD=1; JAVA_REASON="$JAVA_REASON unreferenced_wrong_navignore"
  fi

  if [ "$MOSTREFS" -gt 0 ]; then
    if [ "$MOSTHASH" != "$EXPECTED_MOST20" ]; then
      JAVA_CONFLICT=1; JAVA_NEEDS_PAYLOAD=1; JAVA_REASON="$JAVA_REASON most20_hash_or_file_mismatch"
    fi
  elif [ -r "$MOSTJAR" ] && [ "$MOSTHASH" != "$EXPECTED_MOST20" ]; then
    JAVA_CONFLICT=1; JAVA_NEEDS_PAYLOAD=1; JAVA_REASON="$JAVA_REASON unreferenced_wrong_most20"
  fi

  for P in "$JARDIR/MIBR-DirectVCPolicy.jar" "$JARDIR/NavActiveIgnore.jar"; do
    if [ -e "$P" ]; then
      JAVA_CONFLICT=1
      JAVA_REASON="$JAVA_REASON known_patch_artifact"
    fi
  done

  echo "java_navignore_refs=$NAVREFS"
  echo "java_most20_refs=$MOSTREFS"
  echo "java_foreign_bootclasspath_refs=$FOREIGNREFS"
  echo "java_old_dynamic_loader=$JAVA_OLD_DYNAMIC"
  echo "java_navignore_hash=${NAVHASH:-ABSENT}"
  echo "java_most20_hash=${MOSTHASH:-ABSENT}"
  echo "java_exact_nav_active=$JAVA_EXACT_NAV_ACTIVE"
  echo "java_exact_most20_active=$JAVA_EXACT_MOST20_ACTIVE"
  if [ "$JAVA_CONFLICT" -eq 1 ]; then
    echo "JAVA_STATE=FOREIGN reason=$JAVA_REASON"
    return 30
  fi
  echo "JAVA_STATE=CLEAN"
  return 0
}

find_clean_java_backup(){
  for B in "$LSD.bu" "$LSD.mibr-directvc-stock" "$LSD.mibr-most20fps-stock" "$LSD.mibr-navignore-stock"; do
    [ -r "$B" ] || continue
    grep -Fq 'Find and append jar files' "$B" 2>/dev/null && continue
    grep -Fq '/lsd/jars/' "$B" 2>/dev/null && continue
    grep -Fq 'NavActiveIgnore' "$B" 2>/dev/null && continue
    grep -Fq 'MIBR-' "$B" 2>/dev/null && continue
    echo "$B"
    return 0
  done
  return 1
}

normalize_java_state(){
  JARDIR=/mnt/app/eso/hmi/lsd/jars
  NAVJAR=$JARDIR/MIBR-NavIgnore.jar
  MOSTJAR=$JARDIR/MIBR-Most20FPS.jar
  TMP=/tmp/lsd.sh.mibr-deploy-normalize.$$
  KEEP_NAV=0
  KEEP_MOST=0

  if [ -r "$NAVJAR" ]; then
    H=$(hashf "$NAVJAR" 2>/dev/null)
    [ "$H" = "$EXPECTED_NAVIGNORE" ] && KEEP_NAV=1
  fi
  if [ -r "$MOSTJAR" ]; then
    H=$(hashf "$MOSTJAR" 2>/dev/null)
    [ "$H" = "$EXPECTED_MOST20" ] && KEEP_MOST=1
  fi

  app_rw || fail "java_normalize_mount_app_rw"

  if grep -Fq 'Find and append jar files' "$LSD" 2>/dev/null; then
    B=$(find_clean_java_backup 2>/dev/null) || {
      app_ro
      fail "java_old_dynamic_loader_without_clean_backup"
    }
    echo "Restoring clean pre-Java lsd.sh backup: $B"
    cp "$B" "$TMP" || fail "java_copy_clean_backup"
  else
    awk -v keep_nav="$KEEP_NAV" -v keep_most="$KEEP_MOST" '
      BEGIN { nav_seen=0; most_seen=0 }
      $0 == "# MIBR NAVIGNORE" { next }
      $0 == "# MIBR MOST20FPS" { next }
      $0 == "# MIBR DIRECT-VC POLICY" { next }
      $0 == "#Append jar files" { next }
      index($0,"-Xbootclasspath/p:") && index($0,"/lsd/jars/") {
        if (keep_nav && index($0,"MIBR-NavIgnore.jar") && !nav_seen) {
          print; nav_seen=1
        } else if (keep_most && index($0,"MIBR-Most20FPS.jar") && !most_seen) {
          print; most_seen=1
        }
        next
      }
      { print }
    ' "$LSD" > "$TMP" || fail "java_normalize_lsd"
  fi

  chmod 755 "$TMP" 2>/dev/null || true
  mv "$TMP" "$LSD" || fail "java_install_normalized_lsd"

  for P in "$JARDIR/MIBR-DirectVCPolicy.jar" "$JARDIR/NavActiveIgnore.jar"; do
    if [ -e "$P" ]; then
      echo "Removing archived known conflicting Java artifact: $P"
      rm -f "$P" "$P.new" 2>/dev/null || fail "java_remove_conflicting_artifact=$P"
    fi
  done

  if [ -r "$NAVJAR" ]; then
    H=$(hashf "$NAVJAR" 2>/dev/null)
    if [ "$H" != "$EXPECTED_NAVIGNORE" ]; then
      echo "Removing archived incompatible NavIgnore before exact replacement: hash=$H"
      rm -f "$NAVJAR" "$NAVJAR.new" 2>/dev/null || fail "java_remove_wrong_navignore"
    fi
  fi
  if [ -r "$MOSTJAR" ]; then
    H=$(hashf "$MOSTJAR" 2>/dev/null)
    if [ "$H" != "$EXPECTED_MOST20" ]; then
      echo "Removing archived incompatible Most20 before exact replacement: hash=$H"
      rm -f "$MOSTJAR" "$MOSTJAR.new" 2>/dev/null || fail "java_remove_wrong_most20"
    fi
  fi

  app_ro
  echo "JAVA_NORMALIZE=PASS"
}

handle_java_conflict(){
  echo
  echo "Existing Java patch state differs from the validated NavIgnore + Most20 setup."
  echo "The original state has already been archived in this SD session."

  if [ "$JAVA_EXACT_NAV_ACTIVE" -ne 1 ]; then
    H=$(hashf "$PAYLOAD/MIBR-NavIgnore.jar" 2>/dev/null)
    [ "$H" = "$EXPECTED_NAVIGNORE" ] || fail "replacement_navignore_hash_mismatch=$H"
    echo "Bundled exact NavIgnore payload verified before Java normalization."
  fi
  if [ "$JAVA_EXACT_MOST20_ACTIVE" -ne 1 ]; then
    H=$(hashf "$PAYLOAD/MIBR-Most20FPS.jar" 2>/dev/null)
    [ "$H" = "$EXPECTED_MOST20" ] || fail "replacement_most20_hash_mismatch=$H"
    echo "Bundled exact Most20 payload verified before Java normalization."
  fi

  case "${MIBR_FOREIGN_JAVA_ACTION:-ask}" in
    archive-replace)
      ANSWER=C
      echo "Foreign Java action pre-authorized by MIBR_FOREIGN_JAVA_ACTION=archive-replace"
      ;;
    abort)
      ANSWER=Q
      ;;
    *)
      echo
      echo "Choose:"
      echo "  C = continue: archive is already on SD, deactivate foreign Java boot patches, then use exact NavIgnore + Most20"
      echo "  Q = abort now without changing Java state"
      echo "Enter C or Q:"
      read ANSWER
      ;;
  esac

  case "$ANSWER" in
    C|c)
      echo "JAVA_USER_DECISION=ARCHIVE_AND_CONTINUE"
      normalize_java_state
      ;;
    *)
      echo "JAVA_USER_DECISION=ABORT"
      return 30
      ;;
  esac
  return 0
}

preflight(){
  echo "=== MHI2 AltScreen MU1440 developer install preflight ==="
  [ -x "$SHA" ] || fail "missing_sha256_helper=$SHA"
  [ -x "$TEE" ] || fail "missing_tee_helper=$TEE"
  require_cmds mount cp mv chmod sync mkdir rm touch sleep grep awk wc cat pidin on slay /bin/sh /bin/ksh /eso/bin/apps/dmdt
  media_rw || fail "deployment_media_not_writable=$MEDIA_ROOT"
  echo "PASS deployment_media_rw=$MEDIA_ROOT"
  [ -r /mnt/app/eso/lib/libairplay.so ] || fail "not_mmx_target"
  [ -r "$LSD" ] || fail "missing_lsd_startup=$LSD"
  AIR=$(hashf /mnt/app/eso/lib/libairplay.so) || fail "libairplay_hash_failed"
  [ "$AIR" = "$EXPECTED_AIRPLAY" ] || fail "unsupported_libairplay=$AIR"
  echo "PASS libairplay=$AIR"
  check_hash /mnt/app/eso/hmi/lsd/lsd.jxe "$EXPECTED_LSD_JXE"

  check_hash "$PAYLOAD/libaltscreen111.so" "$EXPECTED_GEN2"
  check_hash "$PAYLOAD/direct-ts-remux" "$EXPECTED_REMUX"
  check_hash "$PAYLOAD/libmibr_isotx2_gate.so" "$EXPECTED_GATE"
  check_hash "$PAYLOAD/MIBR-NavIgnore.jar" "$EXPECTED_NAVIGNORE"
  check_hash "$PAYLOAD/MIBR-Most20FPS.jar" "$EXPECTED_MOST20"

  [ -r "$RUNTIME/auto-direct/common.sh" ] || fail "runtime_common_missing"
  [ -r "$RUNTIME/auto-direct/patch_carplay.sh" ] || fail "patch_carplay_missing"
  [ -r "$RUNTIME/auto-direct/restore_stock.sh" ] || fail "restore_stock_missing"
  [ -r "$RUNTIME/isotx2-gate/install_preload.sh" ] || fail "gate_installer_missing"
  [ -r "$RUNTIME/isotx2-gate/restore_preload.sh" ] || fail "gate_restore_missing"

  echo "=== Java state scan ==="
  java_scan_state
  JAVA_SCAN_RC=$?
  if [ "$JAVA_SCAN_RC" -eq 30 ]; then
    mibr_archive_java_state preflight-foreign || fail "java_archive_failed"
    echo "PREFLIGHT=ATTENTION java_state_requires_user_decision"
    return 30
  elif [ "$JAVA_SCAN_RC" -ne 0 ]; then
    fail "java_scan_failed_rc_$JAVA_SCAN_RC"
  fi

  echo "=== DisplayManager gate preflight ==="
  MIBR_GATE_LIB="$PAYLOAD/libmibr_isotx2_gate.so" MIBR_SHA256="$SHA" \
    "$RUNTIME/isotx2-gate/install_preload.sh" --check || fail "gate_preflight_rc_$?"

  for SPEC in "NavIgnore:MIBR-NavIgnore.jar:$EXPECTED_NAVIGNORE" "Most20:MIBR-Most20FPS.jar:$EXPECTED_MOST20"; do
    NAME=${SPEC%%:*}
    REST=${SPEC#*:}
    JARNAME=${REST%%:*}
    EXPECT=${REST#*:}
    REFS=$(awk -v n="$JARNAME" 'index($0,n){c++} END{print c+0}' "$LSD" 2>/dev/null)
    case "$REFS" in
      0)
        [ -r "$PAYLOAD/$JARNAME" ] || fail "${NAME}_required expected=$EXPECT"
        H=$(hashf "$PAYLOAD/$JARNAME") || fail "${NAME}_hash_failed"
        [ "$H" = "$EXPECT" ] || fail "${NAME}_hash_mismatch=$H"
        grep -q '^\$J9' "$LSD" 2>/dev/null || fail "${NAME}_lsd_insertion_point_missing"
        echo "INFO ${NAME}_payload=valid insertion_point=PASS"
        ;;
      1)
        JAR=/mnt/app/eso/hmi/lsd/jars/$JARNAME
        [ -r "$JAR" ] || fail "${NAME}_bootclasspath_without_jar"
        H=$(hashf "$JAR") || fail "installed_${NAME}_hash_failed"
        [ "$H" = "$EXPECT" ] || fail "installed_${NAME}_hash_mismatch=$H"
        echo "INFO ${NAME}=already_installed hash=$H"
        ;;
      *)
        fail "${NAME}_duplicate_bootclasspath_refs=$REFS"
        ;;
    esac
  done

  echo "PREFLIGHT=PASS"
}

stage_runtime(){
  echo "=== stage internal runtime ==="
  app_rw || fail "mount_app_rw"
  mkdir -p "$DST/bin" "$DST/scripts" "$DST/config" "$DST/logs" "$DST/backup" || fail "runtime_dirs"

  cp "$PAYLOAD/libaltscreen111.so" "$DST/bin/libaltscreen111.so.new" || fail "copy_gen2"
  chmod 755 "$DST/bin/libaltscreen111.so.new" 2>/dev/null || true
  mv "$DST/bin/libaltscreen111.so.new" "$DST/bin/libaltscreen111.so" || fail "install_gen2_stage"

  cp "$PAYLOAD/direct-ts-remux" "$DST/bin/direct-ts-remux.new" || fail "copy_remux"
  chmod 755 "$DST/bin/direct-ts-remux.new" 2>/dev/null || true
  mv "$DST/bin/direct-ts-remux.new" "$DST/bin/direct-ts-remux" || fail "install_remux_stage"

  cp "$SHA" "$DST/bin/sha256sum.new" || fail "copy_sha256"
  chmod 755 "$DST/bin/sha256sum.new" 2>/dev/null || true
  mv "$DST/bin/sha256sum.new" "$DST/bin/sha256sum" || fail "install_sha256"

  cp "$TEE" "$DST/bin/tee.new" || fail "copy_tee"
  chmod 755 "$DST/bin/tee.new" 2>/dev/null || true
  mv "$DST/bin/tee.new" "$DST/bin/tee" || fail "install_tee"

  for F in common.sh patch_carplay.sh restore_stock.sh verify_carplay111_boot.sh direct_ts_auto_enable.sh direct_ts_auto_disable.sh direct_ts_auto_start.sh direct_ts_auto_stop.sh direct_ts_auto_status.sh direct_ts_auto_supervisor.sh direct_ts_auto_watchdog.sh writev_gate.sh; do
    [ -r "$RUNTIME/auto-direct/$F" ] || fail "missing_runtime_$F"
    cp "$RUNTIME/auto-direct/$F" "$DST/scripts/$F.new" || fail "copy_$F"
    chmod 755 "$DST/scripts/$F.new" 2>/dev/null || true
    mv "$DST/scripts/$F.new" "$DST/scripts/$F" || fail "install_$F"
  done

  for F in gen2_keyframes.sh gen2_resync.sh gen2_status.sh; do
    [ -r "$RUNTIME/diagnostics/$F" ] || fail "missing_runtime_$F"
    cp "$RUNTIME/diagnostics/$F" "$DST/scripts/$F.new" || fail "copy_$F"
    chmod 755 "$DST/scripts/$F.new" 2>/dev/null || true
    mv "$DST/scripts/$F.new" "$DST/scripts/$F" || fail "install_$F"
  done

  F=gen2_nav_config.sh
  [ -r "$RUNTIME/navigation/$F" ] || fail "missing_runtime_$F"
  cp "$RUNTIME/navigation/$F" "$DST/scripts/$F.new" || fail "copy_$F"
  chmod 755 "$DST/scripts/$F.new" 2>/dev/null || true
  mv "$DST/scripts/$F.new" "$DST/scripts/$F" || fail "install_$F"

  cp "$RUNTIME/auto-direct/altscreen111.conf" "$DST/config/altscreen111.conf.new" || fail "copy_config"
  chmod 644 "$DST/config/altscreen111.conf.new" 2>/dev/null || true
  mv "$DST/config/altscreen111.conf.new" "$DST/config/altscreen111.conf" || fail "install_config"

  echo "$MEDIA_ROOT" > "$DST/config/deployment_media_root.new" || fail "write_deployment_media_root"
  chmod 644 "$DST/config/deployment_media_root.new" 2>/dev/null || true
  mv "$DST/config/deployment_media_root.new" "$DST/config/deployment_media_root" || fail "install_deployment_media_root"

  app_ro
  echo "STAGE_RUNTIME=PASS"
}

install_required_navignore(){
  if [ ! -r "$PAYLOAD/MIBR-NavIgnore.jar" ]; then
    return 0
  fi

  JARDIR=/mnt/app/eso/hmi/lsd/jars
  JAR=$JARDIR/MIBR-NavIgnore.jar
  TMP=/tmp/lsd.sh.mibr-deploy-navignore.$$
  MARKER='# MIBR NAVIGNORE'
  OWNED=/mnt/app/root/mibr-deploy-navignore-owned

  if grep -Fq 'MIBR-NavIgnore.jar' "$LSD" 2>/dev/null; then
    [ -r "$JAR" ] || fail "navignore_bootclasspath_without_jar"
    H=$(hashf "$JAR") || fail "installed_navignore_hash_failed"
    [ "$H" = "$EXPECTED_NAVIGNORE" ] || fail "installed_navignore_unknown_hash=$H"
    echo "NAVIGNORE=ALREADY_PRESENT"
    return 0
  fi

  app_rw || fail "navignore_mount_app_rw"
  mkdir -p "$JARDIR" || fail "navignore_jardir"
  cp "$PAYLOAD/MIBR-NavIgnore.jar" "$JAR.new" || fail "navignore_copy"
  chmod 644 "$JAR.new" 2>/dev/null || true
  mv "$JAR.new" "$JAR" || fail "navignore_install_jar"

  awk -v marker="$MARKER" '
    BEGIN { done=0 }
    !done && /^\$J9/ {
      print marker
      print "BOOTCLASSPATH=\"$BOOTCLASSPATH -Xbootclasspath/p:$BASE_DIR/lsd/jars/MIBR-NavIgnore.jar\""
      done=1
    }
    { print }
    END { if (!done) exit 42 }
  ' "$LSD" > "$TMP" || fail "navignore_patch_lsd"
  chmod 755 "$TMP" 2>/dev/null || true
  mv "$TMP" "$LSD" || fail "navignore_install_lsd"
  : > "$OWNED" || fail "navignore_owned_marker"
  app_ro
  echo "NAVIGNORE=INSTALLED"
}

install_required_most20(){
  JARDIR=/mnt/app/eso/hmi/lsd/jars
  JAR=$JARDIR/MIBR-Most20FPS.jar
  TMP=/tmp/lsd.sh.mibr-deploy-most20.$$
  MARKER='# MIBR MOST20FPS'
  OWNED=/mnt/app/root/mibr-deploy-most20-owned

  if grep -Fq 'MIBR-Most20FPS.jar' "$LSD" 2>/dev/null; then
    [ -r "$JAR" ] || fail "most20_bootclasspath_without_jar"
    H=$(hashf "$JAR") || fail "installed_most20_hash_failed"
    [ "$H" = "$EXPECTED_MOST20" ] || fail "installed_most20_unknown_hash=$H"
    echo "MOST20=ALREADY_PRESENT"
    return 0
  fi

  app_rw || fail "most20_mount_app_rw"
  mkdir -p "$JARDIR" || fail "most20_jardir"
  cp "$PAYLOAD/MIBR-Most20FPS.jar" "$JAR.new" || fail "most20_copy"
  chmod 644 "$JAR.new" 2>/dev/null || true
  mv "$JAR.new" "$JAR" || fail "most20_install_jar"

  awk -v marker="$MARKER" '
    BEGIN { done=0 }
    !done && /^\$J9/ {
      print marker
      print "BOOTCLASSPATH=\"$BOOTCLASSPATH -Xbootclasspath/p:$BASE_DIR/lsd/jars/MIBR-Most20FPS.jar\""
      done=1
    }
    { print }
    END { if (!done) exit 42 }
  ' "$LSD" > "$TMP" || fail "most20_patch_lsd"
  chmod 755 "$TMP" 2>/dev/null || true
  mv "$TMP" "$LSD" || fail "most20_install_lsd"
  : > "$OWNED" || fail "most20_owned_marker"
  app_ro
  echo "MOST20=INSTALLED"
}

apply(){
  preflight
  PRC=$?
  if [ "$PRC" -eq 30 ]; then
    handle_java_conflict
    JRC=$?
    if [ "$JRC" -ne 0 ]; then
      echo "MIBR_INSTALL=ABORTED java_state_not_changed"
      exit "$JRC"
    fi
    echo "=== re-run preflight after Java normalization ==="
    preflight || fail "post_java_preflight_failed_rc_$?"
  elif [ "$PRC" -ne 0 ]; then
    exit "$PRC"
  fi

  stage_runtime

  echo "=== install DisplayManager isoTX2 gate preload ==="
  MIBR_GATE_LIB="$PAYLOAD/libmibr_isotx2_gate.so" MIBR_SHA256="$SHA" \
    "$RUNTIME/isotx2-gate/install_preload.sh" --apply || fail "gate_preload_rc_$?"

  echo "=== prepare persistent CarPlay Stream111 preload ==="
  "$DST/scripts/patch_carplay.sh" || fail "patch_carplay_rc_$?"

  install_required_navignore
  install_required_most20

  echo "=== normalize D2 keyframe recovery default ==="
  app_rw || fail "d2_default_mount_app_rw"
  rm -f /mnt/app/root/mibr-alt111-keyframe-policy.enabled 2>/dev/null || true
  app_ro
  "$DST/scripts/gen2_keyframes.sh" clear-persist >/dev/null 2>&1 || fail "d2_clear_persist"
  echo "D2_KEYFRAMES=DEFAULT enabled=1 event_delay_ms=250 watchdog_ms=1000 min_gap_ms=1000"

  echo "=== set deployment navigation default ==="
  "$DST/scripts/gen2_nav_config.sh" profile map-rich || fail "map_rich_profile"

  echo "=== enable Auto-Direct persistence without pre-reboot runtime takeover ==="
  MIBR_PREPARE_ONLY=1 "$DST/scripts/direct_ts_auto_enable.sh" || fail "auto_direct_prepare_rc_$?"

  echo
  echo "MIBR_INSTALL=PASS"
  echo "navigation_profile=map-rich"
  echo "most20=enabled_by_default"
  echo "d2_keyframes=default"
  echo "d2_watchdog_ms=1000"
  echo "REBOOT_REQUIRED=YES"
  echo "After reboot: ./status.sh"
  echo "Temporary D2 off: /mnt/app/root/altscreen-u2/scripts/gen2_keyframes.sh off"
  echo "Persistent D2 off: /mnt/app/root/altscreen-u2/scripts/gen2_keyframes.sh persist off"
}

case "${1:---check}" in
  --check) preflight ;;
  --apply) apply ;;
  *) echo "Usage: $0 [--check|--apply]"; exit 2 ;;
esac
