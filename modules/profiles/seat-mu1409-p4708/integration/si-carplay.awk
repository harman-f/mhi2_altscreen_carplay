# si-carplay.awk - smartphone_integrator.json CarPlay environment transform.
#
# Rewrites the first "envs":[ array of the "carplay" child (inside "children")
# to the exact eleven-entry U2 environment list (ten U2 entries plus the SEAT
# steering-wheel zoom flag). Extracted from the logic of
# patch_carplay.sh; the stock file is never shipped, only this transform.
#
# Usage: awk -f si-carplay.awk [-v hook=... -v altport=... -v teeport=...
#        -v width=... -v height=... -v fps=... -v autoshow=... -v url=...]
#        stock-smartphone_integrator.json > patched
# Defaults are the shipped altscreen111.conf values.
#
# Exit codes: 3 = carplay envs array not found, 6 = input already carries a
# CarPlay preload hook (not stock; refuse to patch twice).
BEGIN {
    if (hook == "") hook = "/mnt/app/eso/lib/libmibr_carplay111.so"
    if (altport == "") altport = "6031"
    if (teeport == "") teeport = "19820"
    if (width == "") width = "1010"
    if (height == "") height = "376"
    if (fps == "") fps = "30"
    if (autoshow == "") autoshow = "0"
    if (url == "") url = "maps:/car/instrumentcluster"
    # SEAT/CUPRA: correlated steering-wheel zoom bridge (GEN2, env-gated; Skoda never sets it).
    if (seatzoom == "") seatzoom = "1"
    in_children = 0; in_carplay = 0; patched = 0; foreign = 0
}
{
    if ($0 ~ /libaltscreen111\.so/ || $0 ~ /libmibr_carplay111\.so/) foreign = 1
    if ($0 ~ /"children"[ \t]*:/) in_children = 1
    if (in_children && !in_carplay && $0 ~ /^[ \t]*"carplay"[ \t]*:/) in_carplay = 1
    if (in_carplay && !patched && $0 ~ /^[ \t]*"envs"[ \t]*:\[/) {
        indent = $0; sub(/"envs".*/, "", indent)
        print indent "\"envs\":[\"LD_PRELOAD=" hook "\", \"ALTSCREEN111_PORT=" altport "\", \"ALTSCREEN111_TEE_PORT=" teeport "\", \"ALTSCREEN111_WIDTH=" width "\", \"ALTSCREEN111_HEIGHT=" height "\", \"ALTSCREEN111_FPS=" fps "\", \"ALTSCREEN111_AUTO_SHOW=" autoshow "\", \"ALTSCREEN111_URL=" url "\", \"ALTSCREEN111_SEAT_WHEEL_ZOOM=" seatzoom "\", \"LD_LIBRARY_PATH=/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib\", \"IPL_CONFIG_DIR_DIO_MANAGER=/etc/eso/production\"],"
        patched = 1
        next
    }
    print
}
END {
    if (foreign) exit 6
    if (!patched) exit 3
}
