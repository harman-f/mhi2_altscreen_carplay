#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

ROOT_TEMP=/tmp
ROOT_PERSIST=/mnt/app/root

usage(){
  echo "usage: $0 status|temp|persist|clear-temp|clear-persist"
  echo "preset changes require a fresh CarPlay negotiation"
  exit 2
}

write_one(){
  ROOT=$1
  NAME=$2
  VALUE=$3
  T="$ROOT/$NAME.new.$$"
  echo "$VALUE" > "$T" || return 1
  mv "$T" "$ROOT/$NAME" || { rm -f "$T" 2>/dev/null || true; return 1; }
  chmod 644 "$ROOT/$NAME" 2>/dev/null || true
}

write_multiline(){
  ROOT=$1
  NAME=$2
  SRC=$3
  T="$ROOT/$NAME.new.$$"
  cat "$SRC" > "$T" || return 1
  mv "$T" "$ROOT/$NAME" || { rm -f "$T" 2>/dev/null || true; return 1; }
  chmod 644 "$ROOT/$NAME" 2>/dev/null || true
}

apply_profile(){
  LAYER=$1
  if [ "$LAYER" = persistent ]; then
    mount -uw /mnt/app 2>/dev/null || { echo "OMONOB790_PROFILE=FAIL mount_rw"; exit 10; }
    ROOT=$ROOT_PERSIST
  else
    ROOT=$ROOT_TEMP
  fi

  VIEW=/tmp/mibr-omonob790-viewareas.$$
  DISP=/tmp/mibr-omonob790-display.$$
  D2=/tmp/mibr-omonob790-keyframes.$$
  {
    echo "enabled=1"
    echo "count=1"
    echo "initial=0"
    echo "transition_ms=0"
    echo "view0.x=0"
    echo "view0.y=0"
    echo "view0.w=1010"
    echo "view0.h=376"
    echo "view0.safe.x=202"
    echo "view0.safe.y=16"
    echo "view0.safe.w=606"
    echo "view0.safe.h=344"
    echo "view0.adjacent=0"
  } > "$VIEW" || exit 11
  {
    echo "widthPixels=1010"
    echo "heightPixels=376"
    echo "widthPhysical=202"
    echo "heightPhysical=75"
    echo "uuid=b7e6c5a0-2222-4000-8000-000000000002"
  } > "$DISP" || exit 11
  {
    echo "enabled=0"
    echo "event_delay_ms=250"
    echo "min_gap_ms=1000"
    echo "watchdog_ms=0"
  } > "$D2" || exit 11

  RC=0
  write_one "$ROOT" mibr-carplay111-compat-profile omonob790 || RC=1
  [ "$RC" -eq 0 ] && write_one "$ROOT" mibr-carplay111-fps 40 || RC=1
  [ "$RC" -eq 0 ] && write_one "$ROOT" mibr-carplay111-sourceversion 950.7.1 || RC=1
  [ "$RC" -eq 0 ] && write_one "$ROOT" mibr-carplay111-url maps:/car/instrumentcluster/map || RC=1
  [ "$RC" -eq 0 ] && write_multiline "$ROOT" mibr-carplay111-display.conf "$DISP" || RC=1
  [ "$RC" -eq 0 ] && write_multiline "$ROOT" mibr-carplay111-viewareas.conf "$VIEW" || RC=1
  [ "$RC" -eq 0 ] && write_multiline "$ROOT" mibr-carplay111-keyframes.conf "$D2" || RC=1

  rm -f "$VIEW" "$DISP" "$D2" 2>/dev/null || true

  if [ "$LAYER" = persistent ]; then
    sync
    mount -ur /mnt/app 2>/dev/null || true
  fi

  [ "$RC" -eq 0 ] || { echo "OMONOB790_PROFILE=FAIL write layer=$LAYER"; exit 12; }
  echo "OMONOB790_PROFILE=SET layer=$LAYER"
  echo "apply=CarPlay_reconnect_required"
}

show_file(){
  NAME=$1
  DEF=$2
  if [ -r "$ROOT_TEMP/$NAME" ]; then
    echo "$NAME.source=temp"
    cat "$ROOT_TEMP/$NAME"
  elif [ -r "$ROOT_PERSIST/$NAME" ]; then
    echo "$NAME.source=persistent"
    cat "$ROOT_PERSIST/$NAME"
  else
    echo "$NAME.source=default"
    echo "$DEF"
  fi
}

status(){
  echo "=== OMONOB790 FUNCTIONAL-PARITY PROFILE ==="
  show_file mibr-carplay111-compat-profile mibr
  show_file mibr-carplay111-fps 30
  show_file mibr-carplay111-sourceversion 1005.8.1
  show_file mibr-carplay111-url maps:/car/instrumentcluster
  echo "--- display ---"
  show_file mibr-carplay111-display.conf "widthPixels=1010 heightPixels=376 widthPhysical=200 heightPhysical=74"
  echo "--- viewareas ---"
  show_file mibr-carplay111-viewareas.conf "M.I.B. defaults"
  echo "--- legacy D2 ---"
  show_file mibr-carplay111-keyframes.conf "M.I.B. defaults"
  echo "required_parity=1010x376,202x75,maxFPS40,sourceVersion950.7.1,features10,input3,safe606x344@202,16"
  echo "legacy_d2=disabled_in_parity_preset"
}

clear_layer(){
  LAYER=$1
  if [ "$LAYER" = persistent ]; then
    mount -uw /mnt/app 2>/dev/null || exit 10
    ROOT=$ROOT_PERSIST
  else
    ROOT=$ROOT_TEMP
  fi
  for NAME in     mibr-carplay111-compat-profile     mibr-carplay111-fps     mibr-carplay111-sourceversion     mibr-carplay111-url     mibr-carplay111-display.conf     mibr-carplay111-viewareas.conf     mibr-carplay111-keyframes.conf
  do
    rm -f "$ROOT/$NAME" 2>/dev/null || true
  done
  if [ "$LAYER" = persistent ]; then
    sync
    mount -ur /mnt/app 2>/dev/null || true
  fi
  echo "OMONOB790_PROFILE=CLEARED layer=$LAYER"
}

case "${1:-status}" in
  status) status ;;
  temp|persist) apply_profile "$1" ;;
  clear-temp) clear_layer temp ;;
  clear-persist) clear_layer persistent ;;
  *) usage ;;
esac
