package de.mibr.hmi;

/**
 * r46: engine type announced to the iPhone in the CarPlay Identify (iap2.cfg [vehicle] engine=). One value for the
 * whole HMI. It is read from and written to the unit ONLY through the broker (ENGINE_GET / ENGINE_SET); this class
 * holds the last confirmed answer and builds the menu text (German / English). Source 1.2 style (J9), no I/O.
 */
final class MibrEngineState {
    private MibrEngineState() { }

    /** Cycle order of the menu row. */
    static final String[] VALUES = { "gas", "diesel", "cng", "electric" };

    private static String engine, announced;
    private static boolean pending, busy, failed;

    static synchronized void reset() { engine = null; announced = null; pending = false; busy = false; failed = false; }

    static synchronized boolean known() { return engine != null; }
    static synchronized String engine() { return engine; }
    static synchronized boolean busy() { return busy; }
    static synchronized void busy(boolean b) { busy = b; }
    static synchronized void failed(boolean f) { failed = f; busy = false; }

    /** Confirmed answer of the broker; null/unknown values are ignored (never invented). */
    static synchronized void confirmed(String e, String a, String p) {
        if (index(e) < 0) { failed = true; busy = false; return; }
        engine = e;
        announced = index(a) < 0 ? e : a;
        pending = "1".equals(p);
        failed = false;
        busy = false;
    }

    static int index(String value) {
        for (int i = 0; i < VALUES.length; i++) if (VALUES[i].equals(value)) return i;
        return -1;
    }

    /** The value a tap on the row asks for: the one after the current one (petrol when still unknown). */
    static synchronized String next() {
        int i = index(engine);
        return VALUES[(i + 1) % VALUES.length];
    }

    static String name(String value) {
        if ("gas".equals(value)) return MibrI18n.pick("Benzin", "Petrol");
        if ("diesel".equals(value)) return "Diesel";
        if ("cng".equals(value)) return MibrI18n.pick("Erdgas (CNG)", "CNG");
        if ("electric".equals(value)) return MibrI18n.pick("Elektro", "Electric");
        return "?";
    }

    /** Text of one dropdown value; the value currently set but not yet announced carries the restart note. */
    static synchronized String valueLabel(String value) {
        if (value == null) return "";
        if (pending && value.equals(engine))
            return name(value) + MibrI18n.pick(" (nach Neustart; aktuell ", " (after restart; now ") + name(announced) + ")";
        return name(value);
    }

    /** Menu row text. */
    static synchronized String label() {
        String head = MibrI18n.pick("Motorart: ", "Engine type: ");
        if (failed) return head + MibrI18n.pick("nicht lesbar", "unavailable");
        if (engine == null) return head + (busy ? "..." : MibrI18n.pick("wird gelesen", "reading"));
        String tail = pending ? MibrI18n.pick(" (nach Neustart; aktuell ", " (after restart; now ") + name(announced) + ")" : "";
        return head + name(engine) + tail;
    }
}
