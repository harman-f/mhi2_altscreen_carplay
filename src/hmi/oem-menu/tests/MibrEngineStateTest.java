package de.mibr.hmi;

public final class MibrEngineStateTest {
    static void check(boolean b, String m) { if (!b) throw new AssertionError(m); }
    public static void main(String[] a) {
        MibrI18n.forced = "de_DE";
        MibrEngineState.reset();
        check("Motorart: wird gelesen".equals(MibrEngineState.label()), MibrEngineState.label());
        check("gas".equals(MibrEngineState.next()), "first tap asks for petrol");
        MibrEngineState.busy(true);
        check("Motorart: ...".equals(MibrEngineState.label()), "busy before the first answer");
        MibrEngineState.confirmed("gas", "gas", "0");
        check("Motorart: Benzin".equals(MibrEngineState.label()) && !MibrEngineState.busy(), "confirmed petrol");
        String[] order = {"diesel", "cng", "electric", "gas"};
        for (int i = 0; i < order.length; i++) {
            check(order[i].equals(MibrEngineState.next()), "cycle step " + i);
            MibrEngineState.confirmed(order[i], "gas", "1");
        }
        MibrEngineState.confirmed("diesel", "gas", "1");
        check("Motorart: Diesel (nach Neustart; aktuell Benzin)".equals(MibrEngineState.label()), MibrEngineState.label());
        MibrI18n.forced = "en_GB";
        check("Engine type: Diesel (after restart; now Petrol)".equals(MibrEngineState.label()), MibrEngineState.label());
        MibrEngineState.confirmed("cng", "cng", "0");
        check("Engine type: CNG".equals(MibrEngineState.label()), MibrEngineState.label());
        MibrEngineState.confirmed("electric", "electric", "0");
        check("Engine type: Electric".equals(MibrEngineState.label()), MibrEngineState.label());
        check("Diesel".equals(MibrEngineState.valueLabel("diesel")) && "".equals(MibrEngineState.valueLabel(null)), "value labels");
        MibrEngineState.confirmed("diesel", "gas", "1");
        check("Diesel (after restart; now Petrol)".equals(MibrEngineState.valueLabel("diesel")) && "Petrol".equals(MibrEngineState.valueLabel("gas")), "pending note only on the set value");
        MibrEngineState.confirmed("rubbish", "gas", "0");   // malformed answer: never invented, shows unavailable
        check("Engine type: unavailable".equals(MibrEngineState.label()), MibrEngineState.label());
        // the broker reply parser
        String[] none = new String[0];
        MibrV3Protocol.Frame ok = MibrV3Protocol.parse("MIBR/3 r1 OK engine=diesel;announced=gas;pending=1\n", "r1");
        String[] e = MibrV3Protocol.engine(ok);
        check(e != null && "diesel".equals(e[0]) && "gas".equals(e[1]) && "1".equals(e[2]), "reply parsed");
        check(MibrV3Protocol.engine(MibrV3Protocol.parse("MIBR/3 r2 OK engine=petrol;announced=gas;pending=1\n", "r2")) == null, "bad type");
        check(MibrV3Protocol.engine(MibrV3Protocol.parse("MIBR/3 r3 OK engine=gas;announced=gas;pending=2\n", "r3")) == null, "bad pending");
        check(MibrV3Protocol.engine(MibrV3Protocol.parse("MIBR/3 r4 ERR ENGINE_FAILED\n", "r4")) == null, "error reply");
        String secret = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
        check(MibrV3Protocol.request("r5", "ENGINE_GET", none, none, secret).startsWith("MIBR/3 r5 ENGINE_GET auth="), "ENGINE_GET verb");
        check(MibrV3Protocol.request("r6", "ENGINE_SET", new String[]{"value"}, new String[]{"diesel"}, secret)
              .startsWith("MIBR/3 r6 ENGINE_SET value=diesel;auth="), "ENGINE_SET verb");
        System.out.println("MIBR_ENGINE_STATE_HOST_PASS");
    }
}
