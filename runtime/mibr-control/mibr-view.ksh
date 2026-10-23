#!/bin/ksh
# mibr-view.ksh step | resync | get | set <key> <value> | persistnow <gen>
# "Bildbereich folgt Cockpit-Ansicht" (r55). The virtual cockpit cycles through five views with the right roller PUSH
# (KEY40, one step per KST=1). This helper keeps the position of that cycle and, when "follow" is on, sets the live
# safe area (viewarea.selected, temp layer) for the three map views.
#   views (position): 0 Voll, 1 Wide, 2 Reichweite (no map), 3 Sporttacho (coding option, no map), 4 Center
#   areas (viewarea.selected): 0 Wide, 1 Voll, 2 Center
# resync (r57): KEY40 held long. The owner stands on the view "rs" (cfg, default 0 = Voll) and holds the key; the long
# press itself also steps the cockpit once, so the cockpit then shows the view AFTER rs: the position becomes next(rs).
# Persistent state (flash, written only on change, debounced for key presses): $DIR/cfg and $DIR/pos.
# Live state (RAM): $POS (position), $GEN (debounce generation), $LOCK.
# Output of get/set: key=value lines, last line result=<OK|BAD_VALUE|BUSY|...>.
# Never writes OEM state; the only external effect is the alt111-settings CLI (live layer) and the own state dir.
DIR=${MIBR_VIEW_DIR:-/mnt/app/root/mibr-view}
MNT=${MIBR_VIEW_MOUNT:-/mnt/app}
NOMOUNT=${MIBR_VIEW_NOMOUNT:-0}
CLI=${MIBR_VIEW_CLI:-/mnt/app/root/altscreen-u2/bin/alt111-settings}
POS=${MIBR_VIEW_POS:-/tmp/mibr-view.pos}
GEN=${MIBR_VIEW_GEN:-/tmp/mibr-view.gen}
LOCK=${MIBR_VIEW_LOCK:-/tmp/mibr-view.lock}
AREA=${MIBR_VIEW_AREA:-/tmp/mibr-carplay111-viewarea-selected}
LOG=${MIBR_VIEW_LOG:-/tmp/mibr-view.log}
DEBOUNCE=${MIBR_VIEW_DEBOUNCE:-20}
SELF=$0
SHELLX=${MIBR_VIEW_SHELL:-/bin/ksh}
CLIPFX=${MIBR_VIEW_CLI_PREFIX:-}

say(){ echo "$1"; }
note(){ echo "$1" >> "$LOG" 2>/dev/null; }

cfgget(){
    # cfgget <key> <default>
    v=
    if [ -f "$DIR/cfg" ]; then
        while IFS= read -r line; do
            k=${line%%=*}
            if [ "$k" = "$1" ]; then v=${line#*=}; fi
        done < "$DIR/cfg"
    fi
    [ -n "$v" ] || v=$2
    echo "$v"
}
valid(){
    case "$1" in
        follow|sport) case "$2" in 0|1) return 0 ;; esac ;;
        m0|m1|m4) case "$2" in 0|1|2) return 0 ;; esac ;;
        pos|rs) case "$2" in 0|1|2|3|4) return 0 ;; esac ;;
    esac
    return 1
}
rw(){ [ "$NOMOUNT" = 1 ] || mount -uw "$MNT" 2>/dev/null; }
ro(){ [ "$NOMOUNT" = 1 ] || { sync; mount -ur "$MNT" 2>/dev/null; }; }
# write one file under $DIR atomically (temp + mv on the same filesystem); $1 = name, stdin-free: content in $2
putfile(){
    rw || return 1
    [ -d "$DIR" ] || mkdir "$DIR" 2>/dev/null
    if echo "$2" > "$DIR/$1.new.$$" 2>/dev/null && mv "$DIR/$1.new.$$" "$DIR/$1" 2>/dev/null; then
        ro; return 0
    fi
    rm -f "$DIR/$1.new.$$"; ro; return 1
}
curpos(){
    p=
    [ -s "$POS" ] && read p < "$POS"
    if [ -z "$p" ] && [ -s "$DIR/pos" ]; then read p < "$DIR/pos"; fi
    case "$p" in 0|1|2|3|4) ;; *) p=0 ;; esac
    echo "$p"
}
areafor(){
    # areafor <pos> -> area index or empty (no map view / nothing to do)
    case "$1" in
        0) cfgget m0 1 ;;
        1) cfgget m1 0 ;;
        4) cfgget m4 2 ;;
        *) echo ;;
    esac
}
apply(){
    # apply <pos>: only when follow=1 and the view shows a map
    [ "$(cfgget follow 0)" = 1 ] || return 0
    a=$(areafor "$1")
    [ -n "$a" ] || return 0
    c=; [ -s "$AREA" ] && read c < "$AREA"
    [ "$c" = "$a" ] && return 0
    if [ -f "$CLI" ]; then
        $CLIPFX "$CLI" set --key viewarea.selected --value "$a" --layer temp >/dev/null 2>&1 || { note "APPLY_FAILED pos=$1 area=$a"; return 1; }
        note "APPLY pos=$1 area=$a"
    fi
    return 0
}
dump(){
    say "follow=$(cfgget follow 0)"
    say "sport=$(cfgget sport 1)"
    say "m0=$(cfgget m0 1)"
    say "m1=$(cfgget m1 0)"
    say "m4=$(cfgget m4 2)"
    say "rs=$(cfgget rs 0)"
    say "pos=$(curpos)"
}
finish(){
    dump; say "result=$1"
    rm -f "$LOCK"
    [ "$1" = OK ] && exit 0
    exit 1
}
# /tmp on the unit is a RAM filesystem without mkdir/rmdir: the lock is a pid file created with noclobber.
getlock(){
    if ( set -C; echo $$ > "$LOCK" ) 2>/dev/null; then return 0; fi
    p=; read p < "$LOCK" 2>/dev/null
    if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then return 1; fi
    rm -f "$LOCK"
    ( set -C; echo $$ > "$LOCK" ) 2>/dev/null
}
bump(){
    g=0; [ -s "$GEN" ] && read g < "$GEN"
    case "$g" in ''|*[!0-9]*) g=0 ;; esac
    g=$((g+1)); echo "$g" > "$GEN" 2>/dev/null
    echo "$g"
}
persistnow(){
    # run in the background after a key press burst: only the newest generation writes
    sleep "$DEBOUNCE"
    g=; [ -s "$GEN" ] && read g < "$GEN"
    [ "$g" = "$1" ] || exit 0
    p=$(curpos); s=; [ -s "$DIR/pos" ] && read s < "$DIR/pos"
    [ "$p" = "$s" ] && exit 0
    putfile pos "$p" && note "PERSIST pos=$p"
    exit 0
}
case "$1" in
    persistnow) persistnow "$2" ;;
esac
getlock || { say "result=BUSY"; exit 1; }
case "$1" in
    get) finish OK ;;
    step)
        p=$(curpos)
        n=$(( (p+1) % 5 ))
        if [ "$n" -eq 3 ] && [ "$(cfgget sport 1)" = 0 ]; then n=4; fi
        echo "$n" > "$POS" 2>/dev/null
        apply "$n"
        g=$(bump)
        note "STEP $p -> $n"
        rm -f "$LOCK"
        $SHELLX "$SELF" persistnow "$g" </dev/null >/dev/null 2>&1 &
        exit 0 ;;
    set)
        valid "$2" "$3" || finish BAD_VALUE
        if [ "$2" = pos ]; then
            if [ "$3" -eq 3 ] && [ "$(cfgget sport 1)" = 0 ]; then finish BAD_VALUE; fi
            echo "$3" > "$POS" 2>/dev/null
            putfile pos "$3" || finish WRITE_FAILED
            apply "$3"
            bump >/dev/null
            finish OK
        fi
        # rewrite the whole cfg with the changed key (five short lines)
        f=$(cfgget follow 0); s=$(cfgget sport 1); a=$(cfgget m0 1); b=$(cfgget m1 0); c=$(cfgget m4 2); q=$(cfgget rs 0)
        case "$2" in follow) f=$3 ;; sport) s=$3 ;; m0) a=$3 ;; m1) b=$3 ;; m4) c=$3 ;; rs) q=$3 ;; esac
        putfile cfg "follow=$f
sport=$s
m0=$a
m1=$b
m4=$c
rs=$q" || finish WRITE_FAILED
        # the sport switch off while on the speedometer: move on to Center
        if [ "$2" = sport ] && [ "$3" = 0 ] && [ "$(curpos)" = 3 ]; then
            echo 4 > "$POS" 2>/dev/null; putfile pos 4
        fi
        apply "$(curpos)"
        finish OK ;;
    resync)
        r=$(cfgget rs 0)
        n=$(( (r+1) % 5 ))
        if [ "$n" -eq 3 ] && [ "$(cfgget sport 1)" = 0 ]; then n=4; fi
        echo "$n" > "$POS" 2>/dev/null
        putfile pos "$n" || finish WRITE_FAILED
        apply "$n"
        bump >/dev/null
        note "RESYNC rs=$r -> $n"
        finish OK ;;
    *) finish USAGE ;;
esac
