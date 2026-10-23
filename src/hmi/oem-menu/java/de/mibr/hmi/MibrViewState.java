package de.mibr.hmi;

/**
 * r55: "Bildbereich folgt Cockpit-Ansicht". The virtual cockpit steps through five views with the right roller push
 * (0 Voll, 1 Wide, 2 Reichweite, 3 Sporttacho, 4 Center); the unit keeps that position and, when the owner switched
 * "follow" on, sets the live safe area (0 Wide, 1 Voll, 2 Center) for the three map views. This class holds the last
 * confirmed answer of the broker (VIEW_GET / VIEW_SET) and builds the menu texts. Source 1.2 style (J9), no I/O.
 * Row numbers: 0 follow, 1 pos ("Cockpit-Ansicht jetzt"), 2 rs ("Resync-Ansicht", r57), 3 m0 (area at Voll),
 * 4 m1 (at Wide), 5 m4 (at Center), 6 sport ("Sporttacho vorhanden").
 */
final class MibrViewState {
    private MibrViewState() { }

    static final int ROWS = 7;
    /** Wire names of the rows, in row order (VIEW_SET name=). */
    static final String[] NAMES = { "follow", "pos", "rs", "m0", "m1", "m4", "sport" };

    private static final String[] value = new String[ROWS];
    private static boolean busy, failed;

    static synchronized void reset() {
        for (int i = 0; i < ROWS; i++) value[i] = null;
        busy = false; failed = false;
    }
    static synchronized boolean known() { return value[0] != null; }
    static synchronized boolean busy() { return busy; }
    static synchronized void busy(boolean b) { busy = b; }
    static synchronized void failed(boolean f) { failed = f; busy = false; }
    static synchronized boolean failed() { return failed; }

    /** Confirmed answer, in the protocol order follow, sport, m0, m1, m4, rs, pos (see MibrV3Protocol.view). */
    static synchronized void confirmed(String[] v) {
        if (v == null || v.length != ROWS) { failed = true; busy = false; return; }
        value[0] = v[0]; value[6] = v[1]; value[3] = v[2]; value[4] = v[3]; value[5] = v[4]; value[2] = v[5]; value[1] = v[6];
        failed = false; busy = false;
    }
    static synchronized String value(int row) {
        return row >= 0 && row < ROWS ? value[row] : null;
    }
    static int rowOf(String name) {
        for (int i = 0; i < ROWS; i++) if (NAMES[i].equals(name)) return i;
        return -1;
    }

    /** Dropdown values of a row. The speedometer position is not offered while the car has none. */
    static synchronized String[] options(int row) {
        switch (row) {
            case 0: return new String[] { "0", "1" };
            case 1: case 2:
                if ("0".equals(value[6])) return new String[] { "0", "1", "2", "4" };
                return new String[] { "0", "1", "2", "3", "4" };
            case 3: case 4: case 5: return new String[] { "2", "1", "0" };
            case 6: return new String[] { "1", "0" };
            default: return new String[0];
        }
    }

    static String rowLabel(int row) {
        switch (row) {
            case 0: return MibrI18n.pick("Bildbereich folgt Cockpit-Ansicht", "Safe area follows cockpit view");
            case 1: return MibrI18n.pick("Cockpit-Ansicht jetzt", "Cockpit view now");
            case 2: return MibrI18n.pick("Resync-Ansicht (Langdruck rechts)", "Resync view (long press right)");
            case 3: return MibrI18n.pick("Bildbereich bei Voll", "Safe area at Full");
            case 4: return MibrI18n.pick("Bildbereich bei Wide", "Safe area at Wide");
            case 5: return MibrI18n.pick("Bildbereich bei Center", "Safe area at Center");
            case 6: return MibrI18n.pick("Sporttacho vorhanden", "Sport speedometer present");
            default: return "?";
        }
    }

    static String valueLabel(int row, String v) {
        if (v == null) return "";
        switch (row) {
            case 0: return "1".equals(v) ? MibrI18n.pick("Ein", "On") : MibrI18n.pick("Aus", "Off");
            case 1: case 2:
                if ("0".equals(v)) return MibrI18n.pick("Voll", "Full");
                if ("1".equals(v)) return "Wide";
                if ("2".equals(v)) return MibrI18n.pick("Reichweite", "Range");
                if ("3".equals(v)) return MibrI18n.pick("Sporttacho", "Sport speedo");
                if ("4".equals(v)) return "Center";
                return "?";
            case 3: case 4: case 5:
                if ("0".equals(v)) return "Wide";
                if ("1".equals(v)) return MibrI18n.pick("Voll", "Full");
                if ("2".equals(v)) return "Center";
                return "?";
            case 6: return "1".equals(v) ? MibrI18n.pick("Ja", "Yes") : MibrI18n.pick("Nein", "No");
            default: return "?";
        }
    }
}
