# lua-rgi.awk - usblauncher_otg.lua mm-ipod RGI hook transform.
#
# Adds exactly ONE line directly before the stock mm-ipod return line:
#   if posix.stat("<RGI_ON>") then return "<RGI_WRAPPER> ... config=<RGI_CFG>... end -- MIBR-RGI
# Every original line is kept byte-for-byte; the added line is the only one
# carrying the marker, so   grep -v -- '-- MIBR-RGI' patched   restores stock
# byte-exactly. Port of the sed edit of the MIBR kit (lua_build) to awk.
#
# Usage: awk -f lua-rgi.awk stock-usblauncher_otg.lua > patched
# Exit codes: 3 = stock mm-ipod line not found exactly once,
#             4 = input already carries a MIBR-RGI marker (refuse; foreign or
#                 already patched, never patch twice).
BEGIN {
    marker = "-- MIBR-RGI"
    stock = "return \"mm-ipod -d iap2,config=/etc/mm/iap2.cfg,"
    wrapped = "if posix.stat(\"/mnt/app/root/mibr/config/features/rgi.on\") then return \"/mnt/app/root/mibr/bin/mm-ipod-rgi "
    cfgold = "config=/etc/mm/iap2.cfg"
    cfgnew = "config=/dev/shmem/mibr-rgi-iap2.cfg"
    nl = 0; hits = 0; seen = 0
}
{
    line[++nl] = $0
    if (index($0, marker) > 0) seen++
    if (index($0, stock) > 0) hits++
}
END {
    if (seen > 0) exit 4
    if (hits != 1) exit 3
    for (i = 1; i <= nl; i++) {
        s = line[i]
        p = index(s, stock)
        if (p > 0) {
            # the stock line starts at "return \"mm-ipod " (first occurrence)
            q = index(s, "return \"mm-ipod ")
            m = substr(s, 1, q - 1) wrapped substr(s, q + length("return \"mm-ipod "))
            c = index(m, cfgold)
            m = substr(m, 1, c - 1) cfgnew substr(m, c + length(cfgold))
            print m " end " marker
        }
        print s
    }
}
