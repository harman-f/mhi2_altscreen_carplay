package de.mibr.hmi;

public final class MibrVdataDiagTest {
    static void check(boolean b, String m) { if (!b) throw new AssertionError(m); }
    public static void main(String[] a) {
        MibrI18n.forced = "en_GB";
        String src = "state=attached\nrange=412\noutsidetemp=-3\nrangewarn=1\n";
        String nat = "vstatus_mode=shadow\nvstatus_sent=0\nvstatus_would_send=5\nvstatus_last=range=412 outsidetemp=-3 rangewarn=1\n";
        String sp = "mode=shadow\nsent=0\nwould_send=9\n";
        String cfg = "[location]\nenable=yes\n[vehicle]\nengine=gas\nenable=yes\n";
        String[] l = MibrVdataDiag.lines(src, nat, sp, cfg, "Range::true\nOutsideTemperature::false\nRangeWarning::true\n", "state=tap_kmh=68\noffers=5\n");
        check(l.length == 7, "rows");
        check(l[0].equals("Vehicle data: shadow (attached)"), l[0]);
        check(l[1].equals("Range: 412 km  Outside: -3 \u00b0C"), l[1]);
        check(l[2].equals("Fuel warning: on"), l[2]);
        check(l[3].equals("Announced in Identify: yes (Petrol)"), l[3]);
        check(l[4].equals("Requested by iPhone: range warning"), l[4]);
        check(l[5].startsWith("Sent: 0 (would send: 5)"), l[5]);
        check(l[6].equals("Speed: 68 km/h  Module: shadow, sent 0 (would 9)"), l[6]);
        check(MibrVdataDiag.lines(src, nat, sp, cfg, null, "state=waiting_for_asl\n")[6].startsWith("Speed: -  Module:"), "no tap value");
        String[] n = MibrVdataDiag.lines(null, null, null, "[location]\nenable=yes\n", null);
        check(n[0].equals("Vehicle data: off"), n[0]);
        check(n[1].equals("Range: -  Outside: -"), n[1]);
        check(n[3].endsWith("no") && n[4].endsWith("unknown"), "unannounced/unknown");
        MibrI18n.forced = "de_DE";
        check(MibrVdataDiag.lines(src, nat, sp, cfg, null)[2].equals("Tankwarnung: an"), "de");
        System.out.println("MIBR_VDATA_DIAG_HOST_PASS");
    }
}
