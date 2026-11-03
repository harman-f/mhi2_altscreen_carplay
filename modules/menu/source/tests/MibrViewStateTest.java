package de.mibr.hmi;

public final class MibrViewStateTest {
    static void check(boolean b, String m) { if (!b) throw new AssertionError(m); }
    public static void main(String[] a) {
        MibrI18n.forced = "de_DE";
        MibrViewState.reset();
        check(!MibrViewState.known() && MibrViewState.value(0) == null, "nothing known before the first answer");
        check("0".equals(MibrViewState.options(0)[0]) && MibrViewState.options(0).length == 2, "follow: off/on");
        check(MibrViewState.options(1).length == 5, "five views while the sport option is unknown");
        // protocol order: follow, sport, m0, m1, m4, pos
        MibrViewState.confirmed(new String[] {"1", "1", "1", "0", "2", "4", "3"});
        check(MibrViewState.known() && "1".equals(MibrViewState.value(0)) && "3".equals(MibrViewState.value(1))
              && "4".equals(MibrViewState.value(2)) && "1".equals(MibrViewState.value(3)) && "0".equals(MibrViewState.value(4))
              && "2".equals(MibrViewState.value(5)) && "1".equals(MibrViewState.value(6)), "row mapping");
        check(MibrViewState.options(1).length == 5 && "3".equals(MibrViewState.options(1)[3]), "speedometer offered with the sport option");
        MibrViewState.confirmed(new String[] {"0", "0", "1", "0", "2", "0", "4"});
        String[] p = MibrViewState.options(1);
        check(MibrViewState.options(2).length == 4 && !"3".equals(MibrViewState.options(2)[3]), "resync view: no speedometer without the option");
        check(p.length == 4 && "0".equals(p[0]) && "1".equals(p[1]) && "2".equals(p[2]) && "4".equals(p[3]), "speedometer hidden without it");
        String[] m = MibrViewState.options(3);
        check(m.length == 3 && "2".equals(m[0]) && "1".equals(m[1]) && "0".equals(m[2]), "area dropdown order Center, Voll, Wide");
        check("Voll".equals(MibrViewState.valueLabel(1, "0")) && "Wide".equals(MibrViewState.valueLabel(1, "1"))
              && "Reichweite".equals(MibrViewState.valueLabel(1, "2")) && "Sporttacho".equals(MibrViewState.valueLabel(1, "3"))
              && "Center".equals(MibrViewState.valueLabel(1, "4")), "view labels de");
        check("Center".equals(MibrViewState.valueLabel(3, "2")) && "Voll".equals(MibrViewState.valueLabel(4, "1"))
              && "Wide".equals(MibrViewState.valueLabel(5, "0")) && "Voll".equals(MibrViewState.valueLabel(2, "0")), "area labels");
        check("Aus".equals(MibrViewState.valueLabel(0, "0")) && "Ein".equals(MibrViewState.valueLabel(0, "1"))
              && "Ja".equals(MibrViewState.valueLabel(6, "1")) && "Nein".equals(MibrViewState.valueLabel(6, "0")), "switch labels de");
        check("Bildbereich folgt Cockpit-Ansicht".equals(MibrViewState.rowLabel(0)) && "Cockpit-Ansicht jetzt".equals(MibrViewState.rowLabel(1))
              && "Sporttacho vorhanden".equals(MibrViewState.rowLabel(6)) && "Resync-Ansicht (Langdruck rechts)".equals(MibrViewState.rowLabel(2)), "row labels de");
        MibrI18n.forced = "en_GB";
        check("Safe area follows cockpit view".equals(MibrViewState.rowLabel(0)) && "Full".equals(MibrViewState.valueLabel(1, "0"))
              && "On".equals(MibrViewState.valueLabel(0, "1")) && "Yes".equals(MibrViewState.valueLabel(6, "1")), "labels en");
        check(MibrViewState.rowOf("pos") == 1 && MibrViewState.rowOf("sport") == 6 && MibrViewState.rowOf("rs") == 2 && MibrViewState.rowOf("engine") < 0, "wire names");
        MibrViewState.confirmed(null);
        check(MibrViewState.failed() && !MibrViewState.busy(), "malformed answer is a failure, never invented");
        // the broker reply parser
        String[] none = new String[0];
        String[] v = MibrV3Protocol.view(MibrV3Protocol.parse("MIBR/3 r1 OK follow=1;sport=1;m0=1;m1=0;m4=2;rs=3;pos=4\n", "r1"));
        check(v != null && "1".equals(v[0]) && "1".equals(v[1]) && "1".equals(v[2]) && "0".equals(v[3]) && "2".equals(v[4])
              && "3".equals(v[5]) && "4".equals(v[6]), "reply parsed");
        String[] bad = {
            "MIBR/3 r2 OK follow=2;sport=1;m0=1;m1=0;m4=2;rs=0;pos=4\n", "MIBR/3 r3 OK follow=1;sport=1;m0=3;m1=0;m4=2;rs=0;pos=4\n",
            "MIBR/3 r4 OK follow=1;sport=1;m0=1;m1=0;m4=2;rs=0;pos=5\n", "MIBR/3 r5 OK follow=1;sport=1;m0=1;m1=0;m4=2;rs=0\n",
            "MIBR/3 r6 OK follow=1;sport=1;m0=1;m1=0;m4=2;rs=0;pos=44\n", "MIBR/3 r7 ERR VIEW_FAILED\n",
            "MIBR/3 r8 OK follow=1;sport=1;m0=1;m1=0;m4=2;rs=7;pos=1\n"
        };
        for (int i = 0; i < bad.length; i++) {
            String rid = "r" + (i + 2);
            check(MibrV3Protocol.view(MibrV3Protocol.parse(bad[i], rid)) == null, "bad reply " + i);
        }
        String secret = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
        check(MibrV3Protocol.request("r8", "VIEW_GET", none, none, secret).startsWith("MIBR/3 r8 VIEW_GET auth="), "VIEW_GET verb");
        check(MibrV3Protocol.request("r9", "VIEW_SET", new String[] {"name", "value"}, new String[] {"pos", "4"}, secret)
              .startsWith("MIBR/3 r9 VIEW_SET name=pos;value=4;auth="), "VIEW_SET verb");
        System.out.println("MIBR_VIEW_STATE_HOST_PASS");
    }
}
