#!/bin/sh
# Thin wrapper: delegates to the canonical installer entrypoint (no duplicated logic).
case $0 in */*) D=${0%/*} ;; *) D=. ;; esac
if [ -x /bin/ksh ]; then S=/bin/ksh; else S=sh; fi
exec "$S" "$D/mibr-install.ksh" --uninstall "$@"
