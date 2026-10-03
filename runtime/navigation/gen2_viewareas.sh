#!/bin/ksh
# SPDX-License-Identifier: GPL-3.0-or-later
set -u

NAME=mibr-carplay111-viewareas.conf
TEMP=/tmp/$NAME
PERSIST=/mnt/app/root/$NAME
REQUEST=/tmp/mibr-alt111-viewarea-request
STATUS=/tmp/mibr-alt111-gen2.status

usage(){
  echo "usage:"
  echo "  $0 status"
  echo "  $0 temp-default|persist-default"
  echo "  $0 temp-set KEY VALUE"
  echo "  $0 persist-set KEY VALUE"
  echo "  $0 clear-temp|clear-persist"
  echo "  $0 select {0|1}"
  echo "definition changes require CarPlay reconnect; select is live"
  exit 2
}
source_file(){
  [ -r "$TEMP" ] && { echo "$TEMP"; return; }
  [ -r "$PERSIST" ] && { echo "$PERSIST"; return; }
  echo ""
}
source_name(){
  [ -r "$TEMP" ] && { echo temp; return; }
  [ -r "$PERSIST" ] && { echo persistent; return; }
  echo default
}
emit_default(){
  cat <<'EOF'
enabled=1
count=2
initial=0
transition_ms=0
view0.x=0
view0.y=0
view0.w=1010
view0.h=376
view0.safe.x=0
view0.safe.y=0
view0.safe.w=1010
view0.safe.h=376
view0.adjacent=1
view1.x=0
view1.y=0
view1.w=1010
view1.h=376
view1.safe.x=0
view1.safe.y=58
view1.safe.w=1010
view1.safe.h=248
view1.adjacent=0
EOF
}
status(){
  echo "=== GEN2 VIEWAREAS ==="
  echo "source=$(source_name)"
  F=$(source_file)
  [ -n "$F" ] && cat "$F" || emit_default
  echo "temporary_path=$TEMP"
  echo "persistent_path=$PERSIST"
  echo "apply_definition=reconnect"
  echo "apply_select=live"
  [ -r "$STATUS" ] && grep -E '^(control_session|projection_desired|shown_ack|view_count|desired_view|acknowledged_view)=' "$STATUS" 2>/dev/null || true
}
write_default(){
  L=$1
  [ "$L" = persistent ] && { mount -uw /mnt/app 2>/dev/null || exit 12; TGT=$PERSIST; } || TGT=$TEMP
  T="$TGT.new.$$"
  emit_default > "$T" || exit 13
  mv "$T" "$TGT" || exit 14
  chmod 644 "$TGT" 2>/dev/null || true
  [ "$L" = persistent ] && { sync; mount -ur /mnt/app 2>/dev/null || true; }
}
valid_key(){
  case "$1" in
    enabled|count|initial|transition_ms|view0.x|view0.y|view0.w|view0.h|view0.safe.x|view0.safe.y|view0.safe.w|view0.safe.h|view0.adjacent|view1.x|view1.y|view1.w|view1.h|view1.safe.x|view1.safe.y|view1.safe.w|view1.safe.h|view1.adjacent) return 0 ;;
    *) return 1 ;;
  esac
}
set_key(){
  L=$1; K=$2; V=$3
  valid_key "$K" || usage
  case "$V" in ''|*[!0-9-]*) usage ;; esac
  if [ "$L" = persistent ]; then
    mount -uw /mnt/app 2>/dev/null || exit 12
    TGT=$PERSIST
    [ -r "$PERSIST" ] && F=$PERSIST || F=
  else
    TGT=$TEMP
    F=$(source_file)
  fi
  BASE="$TGT.base.$$"
  if [ -n "$F" ]; then cp "$F" "$BASE" || exit 13; else emit_default > "$BASE" || exit 13; fi
  T="$TGT.new.$$"
  awk -F= -v k="$K" -v v="$V" '
    BEGIN{done=0}
    $1==k {print k "=" v; done=1; next}
    {print}
    END{if(!done) print k "=" v}
  ' "$BASE" > "$T" || exit 14
  rm -f "$BASE" 2>/dev/null || true
  mv "$T" "$TGT" || exit 15
  chmod 644 "$TGT" 2>/dev/null || true
  [ "$L" = persistent ] && { sync; mount -ur /mnt/app 2>/dev/null || true; }
}
select_view(){
  IDX=$1
  [ "$IDX" = 0 ] || [ "$IDX" = 1 ] || usage

  if [ -r "$STATUS" ]; then
    SESSION=$(awk -F= '/^control_session=/{print $2; exit}' "$STATUS" 2>/dev/null)
    READY=$(awk -F= '/^command_ready=/{print $2; exit}' "$STATUS" 2>/dev/null)
    COUNT=$(awk -F= '/^view_count=/{print $2; exit}' "$STATUS" 2>/dev/null)
    [ "${SESSION:-0}" != 0 ] && [ "${READY:-0}" = 1 ] || {
      echo "GEN2_VIEWAREA_SELECT=NO_ACTIVE_SESSION"
      exit 22
    }
    [ -z "${COUNT:-}" ] || [ "$IDX" -lt "$COUNT" ] || {
      echo "GEN2_VIEWAREA_SELECT=INVALID_FOR_ACTIVE_COUNT index=$IDX count=$COUNT"
      exit 23
    }
  fi

  echo "$IDX" > "$REQUEST.new.$" || exit 20
  mv "$REQUEST.new.$" "$REQUEST" || exit 21
  echo "GEN2_VIEWAREA_SELECT=REQUESTED index=$IDX"

  I=0
  while [ "$I" -lt 30 ]; do
    ACK=
    [ -r "$STATUS" ] && ACK=$(awk -F= '/^acknowledged_view=/{print $2; exit}' "$STATUS" 2>/dev/null)
    if [ "$ACK" = "$IDX" ]; then
      echo "GEN2_VIEWAREA_SELECT=CONFIRMED index=$IDX"
      return 0
    fi
    I=$((I+1))
    if command -v usleep >/dev/null 2>&1; then usleep 100000; else sleep 1; fi
  done

  echo "GEN2_VIEWAREA_SELECT=NOT_CONFIRMED index=$IDX acknowledged=${ACK:-unknown}"
  exit 24
}
case "${1:-status}" in
  status) status ;;
  temp-default) write_default temp; status ;;
  persist-default) write_default persistent; status ;;
  temp-set|persist-set)
    [ "$#" -eq 3 ] || usage
    [ "$1" = temp-set ] && L=temp || L=persistent
    set_key "$L" "$2" "$3"
    status
    ;;
  clear-temp)
    rm -f "$TEMP" 2>/dev/null || true
    status
    ;;
  clear-persist)
    mount -uw /mnt/app 2>/dev/null || exit 12
    rm -f "$PERSIST" 2>/dev/null || true
    sync
    mount -ur /mnt/app 2>/dev/null || true
    status
    ;;
  select)
    [ "$#" -eq 2 ] || usage
    select_view "$2"
    ;;
  *) usage ;;
esac
