#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later

BASE=/mnt/app/root/altscreen-u2
TARGET=/mnt/system/etc/eso/production/smartphone_integrator.json
EXPECTED_AIRPLAY=193a4fd9101ec2aa05e7159cfa307b96500810d379ca74a194f172adc13a46b5
EXPECTED_SMARTPHONE=dd925b8a85ad1acc9d88dd5e7aedabc3118c1c8299e107bbaa99b4c145c807be

export PATH=.:/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/media/gracenote/bin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin:/mnt/app/armle/usr/sbin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD
export GEM=1

# Installed runtime is self-contained under /mnt/app/root/altscreen-u2.
# Persistent logs prefer the deployment SD/USB medium when available. This
# preserves the proven M.I.B. writable-media behavior without importing its
# BASICS/GLOBALS or depending on an apps/ tree.
VOLUME="$BASE"
SHA256="$BASE/bin/sha256sum"
TEE="$BASE/bin/tee"
TIMESTAMP="/net/rcc/usr/bin/date +%Y_%m_%d_%H_%M_%S"
TMP="/net/rcc/dev/shmem"
DEPLOY_MEDIA_FILE="$BASE/config/deployment_media_root"
DEPLOY_MEDIA_ROOT=""
U2_STORAGE_READY=0
U2_LOG_ON_MEDIA=0

set_log_root(){
  BACKUPFOLDER=$1
  LOG="$BACKUPFOLDER/U2-LOG.txt"
  DIRECT_LOG_ROOT="$BACKUPFOLDER/direct-ts"
  DIRECT_MASTER_LOG="$DIRECT_LOG_ROOT/DIRECT-TS.log"
}

set_log_root /tmp/mibr-altscreen-logs
if [ -r "$DEPLOY_MEDIA_FILE" ]; then
  DEPLOY_MEDIA_ROOT=$(cat "$DEPLOY_MEDIA_FILE" 2>/dev/null)
  case "$DEPLOY_MEDIA_ROOT" in
    /net/mmx/fs/*)
      U2_LOG_ON_MEDIA=1
      set_log_root "$DEPLOY_MEDIA_ROOT/mhi2-altscreen-logs"
      ;;
    *)
      DEPLOY_MEDIA_ROOT=""
      ;;
  esac
fi

CARPLAY_HOOK=/mnt/app/eso/lib/libmibr_carplay111.so
CARPLAY_BACKDIR=/mnt/app/root/mibr-carplay111-backup
DIRECT_FPS_OVERRIDE_FILE=/mnt/app/root/mibr-direct-output-fps
SOURCE_FPS_OVERRIDE_FILE=/mnt/app/root/mibr-carplay111-fps
BACKUP=$CARPLAY_BACKDIR/smartphone_integrator.json.stock
BACKUP_SHA=$CARPLAY_BACKDIR/smartphone_integrator.json.stock.sha256

runtime_find_cmd(){
  CMD=$1
  case "$CMD" in
    */*) [ -x "$CMD" ] && { echo "$CMD"; return 0; } ;;
    *)
      OLDIFS=$IFS
      IFS=:
      FOUND=""
      for D in $PATH; do
        [ -n "$D" ] || D=.
        if [ -x "$D/$CMD" ]; then FOUND="$D/$CMD"; break; fi
      done
      IFS=$OLDIFS
      [ -n "$FOUND" ] && { echo "$FOUND"; return 0; }
      ;;
  esac
  return 1
}

runtime_emit(){
  MSG="$*"
  if [ -x "${TEE:-}" ] && [ -n "${LOG:-}" ] && [ -n "${BACKUPFOLDER:-}" ] && [ -d "$BACKUPFOLDER" ]; then
    echo "$MSG" | "$TEE" -a "$LOG" 2>/dev/null || {
      echo "$MSG"
      echo "$MSG" >> "$LOG" 2>/dev/null || true
    }
  else
    echo "$MSG"
    [ -n "${LOG:-}" ] && echo "$MSG" >> "$LOG" 2>/dev/null || true
  fi
}

runtime_require_cmds(){
  MISSING=0
  for CMD in "$@"; do
    runtime_find_cmd "$CMD" >/dev/null 2>&1 || {
      runtime_emit "ERROR missing required runtime command: $CMD"
      MISSING=1
    }
  done
  [ "$MISSING" -eq 0 ]
}

process_line(){
  NAME=$1
  pidin ar 2>/dev/null | awk -v n="$NAME" '
    index($0,n) && $0 !~ /awk -v n=/ && $0 !~ /grep/ { print; exit }
  '
}

process_running(){
  [ -n "$(process_line "$1")" ]
}

smartphone_restart_count(){
  process_line smartphone_integrator | awk '
    {
      for(i=1;i<=NF;i++) {
        if($i=="-sm-restart" && (i+1)<=NF) { print $(i+1); exit }
      }
    }
  '
}

carplay_stack_health(){
  process_running smartphone_integrator && process_running dio_manager
}

prepare_log_storage(){
  if [ "$U2_STORAGE_READY" = "1" ]; then
    [ -d "$BACKUPFOLDER" ] || return 1
    return 0
  fi

  if [ "$U2_LOG_ON_MEDIA" = "1" ]; then
    if ! mount -uw "$DEPLOY_MEDIA_ROOT" 2>/dev/null; then
      runtime_emit "WARN deployment media unavailable for logging; using /tmp"
      U2_LOG_ON_MEDIA=0
      set_log_root /tmp/mibr-altscreen-logs
    fi
  fi

  if ! mkdir -p "$BACKUPFOLDER" 2>/dev/null; then
    if [ "$U2_LOG_ON_MEDIA" = "1" ]; then
      runtime_emit "WARN deployment media log directory unavailable; using /tmp"
      U2_LOG_ON_MEDIA=0
      set_log_root /tmp/mibr-altscreen-logs
      mkdir -p "$BACKUPFOLDER" 2>/dev/null || return 1
    else
      return 1
    fi
  fi

  TEST="$BACKUPFOLDER/.write-test-$$"
  if ! touch "$TEST" 2>/dev/null || [ ! -f "$TEST" ]; then
    rm -f "$TEST" 2>/dev/null || true
    if [ "$U2_LOG_ON_MEDIA" = "1" ]; then
      runtime_emit "WARN deployment media is not writable; using /tmp"
      U2_LOG_ON_MEDIA=0
      set_log_root /tmp/mibr-altscreen-logs
      mkdir -p "$BACKUPFOLDER" 2>/dev/null || return 1
      TEST="$BACKUPFOLDER/.write-test-$$"
      touch "$TEST" 2>/dev/null || return 1
      [ -f "$TEST" ] || return 1
    else
      return 1
    fi
  fi
  rm -f "$TEST" 2>/dev/null || true
  [ -f "$LOG" ] || echo "MU1440 AltScreen runtime" > "$LOG" 2>/dev/null || true
  mkdir -p "$DIRECT_LOG_ROOT" 2>/dev/null || true
  U2_STORAGE_READY=1
  export U2_STORAGE_READY U2_LOG_ON_MEDIA
  return 0
}

runtime_init(){
  [ -d "$BASE" ] || { runtime_emit "ERROR package root missing: $BASE"; return 1; }
  [ -x "$SHA256" ] || {
    runtime_emit "ERROR bundled SHA-256 helper missing/not executable: $SHA256"
    return 2
  }
  [ -x "$TEE" ] || {
    runtime_emit "ERROR bundled tee helper missing/not executable: $TEE"
    return 3
  }
  return 0
}

runtime_init_durable(){
  runtime_init
  RC=$?
  if [ "$RC" -ne 0 ]; then
    runtime_emit "ERROR runtime/log bootstrap failed rc=$RC"
    return "$RC"
  fi
  prepare_log_storage || {
    runtime_emit "ERROR durable log storage is not writable: $BASE/logs"
    runtime_emit "ERROR runtime/log bootstrap failed rc=4"
    return 4
  }
  return 0
}

timestamp_now(){
  if [ -x /net/rcc/usr/bin/date ]; then
    /net/rcc/usr/bin/date +%Y%m%d-%H%M%S 2>/dev/null && return 0
  fi
  echo "run-$$"
}

stamp(){ timestamp_now; }

log(){
  MSG="$(timestamp_now) $*"
  runtime_emit "$MSG"
}

emit_to_file(){
  OUT=$1
  shift
  MSG="$*"
  if [ -x "$TEE" ]; then
    if [ -n "${LOG:-}" ]; then
      echo "$MSG" | "$TEE" -a "$OUT" "$LOG" 2>/dev/null || true
    else
      echo "$MSG" | "$TEE" -a "$OUT" 2>/dev/null || true
    fi
  else
    echo "$MSG"
    echo "$MSG" >> "$OUT" 2>/dev/null || true
    [ -n "${LOG:-}" ] && echo "$MSG" >> "$LOG" 2>/dev/null || true
  fi
}

hash256(){
  HLINE=$("$SHA256" "$1" 2>/dev/null) || return $?
  set -- $HLINE
  [ -n "$1" ] || return 1
  echo "$1"
}

hash256_line(){
  H=$(hash256 "$1") || return $?
  echo "$H  $1"
}

run_dmdt(){ (cd /eso 2>/dev/null && IPL_CONFIG_DIR=/etc/eso/production LD_LIBRARY_PATH=/eso/lib:/lib:/usr/lib /eso/bin/apps/dmdt "$@"); }

route(){
  C=$1; D=$2; V=${3:-4}
  log "DMDT route: context=$C displayable=$D display=$V"
  run_dmdt dc "$C" "$D" >> "$BACKUPFOLDER/dmdt.log" 2>&1
  R1=$?
  run_dmdt sc "$V" "$C" >> "$BACKUPFOLDER/dmdt.log" 2>&1
  R2=$?
  [ $R1 -eq 0 ] && [ $R2 -eq 0 ]
}

stock_route(){ route 70 33 4; }

find_displaymanager_config(){
  for p in /etc/eso/production/displaymanager.json /mnt/system/etc/eso/production/displaymanager.json /mnt/app/eso/production/displaymanager.json; do
    [ -r "$p" ] && { echo "$p"; return 0; }
  done
  return 1
}

find_iso_driver(){
  for p in /sbin/devp-iso-mmx-mib2 /proc/boot/devp-iso-mmx-mib2 /bin/devp-iso-mmx-mib2; do
    [ -x "$p" ] && { echo "$p"; return 0; }
  done
  runtime_find_cmd devp-iso-mmx-mib2 2>/dev/null
}

dump_most_contract(){
  echo "-- MOST/DCIVIDEO endpoint contract --"
  ls -l /dev/mlb/isoTX1 /dev/mlb/isoTX2 2>/dev/null || true
  ls -l /net/rcc/dev/name/local/inic/isoTX1 /net/rcc/dev/name/local/inic/isoTX2 2>/dev/null || true

  DMCONF=$(find_displaymanager_config 2>/dev/null)
  if [ -n "$DMCONF" ]; then
    echo "displaymanager_config=$DMCONF"
    echo "-- stock displaymanager MOST-related lines --"
    grep -n -E 'most_encoder|isoTX2|nv_|video_over_most' "$DMCONF" 2>/dev/null || true
  else
    echo "WARN displaymanager.json not found in known locations"
  fi

  echo "-- isoTX2 open-file owners --"
  pidin fds 2>/dev/null | grep -E '(/dev/mlb/isoTX2|/dev/name/local/inic/isoTX2|devp-iso-mmx-mib2)' || true
  echo "-- displaymanager fds --"
  pidin -p displaymanagementProc fds 2>/dev/null | grep -E '(isoTX|mlb|MOST|most)' ||
    pidin -p displaymanager fds 2>/dev/null | grep -E '(isoTX|mlb|MOST|most)' || true

  DRV=$(find_iso_driver 2>/dev/null)
  if [ -n "$DRV" ]; then
    echo "iso_driver=$DRV"
    USECMD=$(runtime_find_cmd use 2>/dev/null)
    [ -n "$USECMD" ] && "$USECMD" "$DRV" 2>&1 || true
    STRINGSCMD=$(runtime_find_cmd strings 2>/dev/null)
    [ -n "$STRINGSCMD" ] && "$STRINGSCMD" "$DRV" 2>/dev/null |
      grep -Ei 'usage|isoTX|isoRX|packet|size|buffer|queue|transmit|receive|mlb|devctl|ioctl' || true
  fi
}

load_altscreen_config(){
  CONF="$BASE/config/altscreen111.conf"
  [ -r "$CONF" ] || { log "ERROR missing $CONF"; return 1; }
  . "$CONF"

  : ${ALTSCREEN111_PORT:=6031}
  : ${ALTSCREEN111_TEE_PORT:=19820}
  : ${ALTSCREEN111_WIDTH:=1010}
  : ${ALTSCREEN111_HEIGHT:=376}
  : ${ALTSCREEN111_FPS:=30}
  : ${DIRECT_OUTPUT_FPS:=30}
  : ${DIRECT_PACE:=1}
  : ${DIRECT_PACE_BUFFER:=3}
  : ${ALTSCREEN111_AUTO_SHOW:=1}
  : ${ALTSCREEN111_URL:=maps:/car/instrumentcluster/map}

  case "$ALTSCREEN111_PORT:$ALTSCREEN111_TEE_PORT:$ALTSCREEN111_WIDTH:$ALTSCREEN111_HEIGHT:$ALTSCREEN111_FPS:$ALTSCREEN111_AUTO_SHOW:$DIRECT_OUTPUT_FPS:$DIRECT_PACE:$DIRECT_PACE_BUFFER" in
    *[!0-9:]*|'') log "ERROR invalid numeric AltScreen/direct output config"; return 1 ;;
  esac
  case "$DIRECT_OUTPUT_FPS" in
    20|25|30) ;;
    *) log "ERROR DIRECT_OUTPUT_FPS must be 20, 25 or 30"; return 1 ;;
  esac
  case "$DIRECT_PACE" in
    0|1) ;;
    *) log "ERROR DIRECT_PACE must be 0 or 1"; return 1 ;;
  esac
  case "$DIRECT_PACE_BUFFER" in
    1|2|3|4|5|6) ;;
    *) log "ERROR DIRECT_PACE_BUFFER must be 1..6"; return 1 ;;
  esac
  if [ -r "$DIRECT_FPS_OVERRIDE_FILE" ]; then
    FPS_OVERRIDE=$(cat "$DIRECT_FPS_OVERRIDE_FILE" 2>/dev/null)
    case "$FPS_OVERRIDE" in
      20|25|30) DIRECT_OUTPUT_FPS=$FPS_OVERRIDE ;;
      *) log "WARN ignoring invalid direct FPS override: $FPS_OVERRIDE" ;;
    esac
  fi
  case "$ALTSCREEN111_URL" in
    *\"*|*\\*) log "ERROR invalid ALTSCREEN111_URL"; return 1 ;;
  esac
  return 0
}

direct_log(){
  mkdir -p "$DIRECT_LOG_ROOT" 2>/dev/null || true
  MSG="$(timestamp_now) $*"
  if [ -x "$TEE" ]; then
    echo "$MSG" | "$TEE" -a "$LOG" "$DIRECT_MASTER_LOG" 2>/dev/null || true
  else
    echo "$MSG"
    [ -n "${LOG:-}" ] && echo "$MSG" >> "$LOG" 2>/dev/null || true
    echo "$MSG" >> "$DIRECT_MASTER_LOG" 2>/dev/null || true
  fi
}

direct_new_run(){
  STAGE=$1
  runtime_init_durable || return 1
  mkdir -p "$DIRECT_LOG_ROOT" 2>/dev/null || return 1
  DIRECT_RUN=$DIRECT_LOG_ROOT/$(stamp)-$STAGE
  mkdir -p "$DIRECT_RUN" 2>/dev/null || return 1
  echo "$DIRECT_RUN"
}

direct_snapshot(){
  OUTDIR=$1
  mkdir -p "$OUTDIR" 2>/dev/null || return 1
  timestamp_now > "$OUTDIR/date.txt" 2>/dev/null || true
  uname -a > "$OUTDIR/uname.txt" 2>/dev/null || true
  pidin ar > "$OUTDIR/pidin.txt" 2>/dev/null || true
  pidin fds > "$OUTDIR/pidin-fds.txt" 2>/dev/null || true
  pidin -p displaymanagementProc fds > "$OUTDIR/displaymanager-fds.txt" 2>/dev/null ||
    pidin -p displaymanager fds > "$OUTDIR/displaymanager-fds.txt" 2>/dev/null || true
  run_dmdt gs > "$OUTDIR/dmdt-gs.txt" 2>&1 || true
  ls -l /dev/mlb/isoTX2 /net/rcc/dev/name/local/inic/isoTX2 > "$OUTDIR/isoTX2-ls.txt" 2>&1 || true
  DMCONF=$(find_displaymanager_config 2>/dev/null)
  [ -n "$DMCONF" ] && cp "$DMCONF" "$OUTDIR/displaymanager.json" 2>/dev/null || true
  [ -r /tmp/altscreen111.log ] && cp /tmp/altscreen111.log "$OUTDIR/altscreen111.log" 2>/dev/null || true
}
