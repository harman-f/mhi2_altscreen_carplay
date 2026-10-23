package de.mibr.hmi;

import java.io.FileInputStream;

/**
 * Read-only lines for the menu page "Diagnose": what the vehicle-data module
 * of the CarPlay link currently knows. It only reads the small status files the module already writes
 * (HMI source, native counters), the Identify configuration and, if present, the PPS object "vehicle" that
 * shows which fields the iPhone requested. Nothing is written, nothing is sent. Source 1.2 style (J9).
 */
final class MibrVdataDiag {
    private MibrVdataDiag() { }

    static final String SRC_STATUS = "/tmp/mibr-vstatus-source.status";
    static final String NAT_STATUS = "/tmp/mibr-vstatus.status";
    static final String SPEED_STATUS = "/tmp/mibr-vdata.status";
    /** HMI-side speed source: state=tap_kmh=<km/h> (the stock value read once per 200 ms). */
    static final String SPEED_SOURCE = "/tmp/mibr-vdata-source.status";
    static final String IAP2_CFG = "/mnt/system/etc/mm/iap2.cfg";
    static final String[] PPS_CANDIDATES = {
        "/pps/iap2/vehicle", "/ramdisk/pps/iap2/vehicle", "/pps/mm-ipod/vehicle", "/tmp/pps/iap2/vehicle", "/pps/vehicle"
    };

    /** Test seam: replaces the file reader. */
    interface Reader { String read(String path); }
    static Reader reader = new Reader() {
        public String read(String path) {
            FileInputStream in = null;
            try {
                in = new FileInputStream(path);
                byte[] b = new byte[4096];
                int n = in.read(b);
                return n <= 0 ? "" : new String(b, 0, n, "US-ASCII");
            } catch (Throwable t) {
                return null;
            } finally {
                if (in != null) try { in.close(); } catch (Throwable ignored) { }
            }
        }
    };

    /** Value of key= in a key=value text, or null. */
    static String get(String text, String key) {
        if (text == null) return null;
        String k = key + "=";
        int at = 0;
        while (at < text.length()) {
            int end = text.indexOf('\n', at);
            if (end < 0) end = text.length();
            if (text.startsWith(k, at)) return text.substring(at + k.length(), end).trim();
            at = end + 1;
        }
        return null;
    }

    static String onoff(boolean b) { return b ? MibrI18n.pick("ja", "yes") : MibrI18n.pick("nein", "no"); }

    /** true when [vehicle] with enable=yes is present in iap2.cfg (the capability announced in Identify). */
    static boolean announced(String cfg) {
        if (cfg == null) return false;
        boolean in = false;
        int at = 0;
        while (at < cfg.length()) {
            int end = cfg.indexOf('\n', at);
            if (end < 0) end = cfg.length();
            String line = cfg.substring(at, end).trim();
            at = end + 1;
            if (line.startsWith("[")) in = line.equals("[vehicle]");
            else if (in && line.equals("enable=yes")) return true;
        }
        return false;
    }

    /** engine= value of the [vehicle] block, or null. */
    static String engineOf(String cfg) {
        if (cfg == null) return null;
        boolean in = false;
        int at = 0;
        while (at < cfg.length()) {
            int end = cfg.indexOf('\n', at);
            if (end < 0) end = cfg.length();
            String line = cfg.substring(at, end).trim();
            at = end + 1;
            if (line.startsWith("[")) in = line.equals("[vehicle]");
            else if (in && line.startsWith("engine=")) return line.substring(7);
        }
        return null;
    }

    static String requested(String pps) {
        if (pps == null) return MibrI18n.pick("unbekannt", "unknown");
        StringBuffer b = new StringBuffer();
        if (flag(pps, "Range")) b.append(MibrI18n.pick("Reichweite ", "range "));
        if (flag(pps, "OutsideTemperature")) b.append(MibrI18n.pick("Temp. ", "temp. "));
        if (flag(pps, "RangeWarning")) b.append(MibrI18n.pick("Warnung", "warning"));
        return b.length() == 0 ? MibrI18n.pick("nichts", "nothing") : b.toString().trim();
    }

    private static boolean flag(String pps, String name) {
        int at = pps.indexOf(name);
        if (at < 0) return false;
        int end = pps.indexOf('\n', at);
        String line = pps.substring(at, end < 0 ? pps.length() : end);
        return line.indexOf("true") >= 0 || line.indexOf(":1") >= 0 || line.endsWith("=1");
    }

    static String modeName(String m) {
        if (m == null) return MibrI18n.pick("aus", "off");
        if (m.startsWith("send")) return MibrI18n.pick("senden", "send");
        if (m.startsWith("shadow")) return MibrI18n.pick("Beobachten", "shadow");
        return MibrI18n.pick("aus", "off");
    }

    static String[] lines(String src, String nat, String speed, String cfg, String pps) {
        return lines(src, nat, speed, cfg, pps, null);
    }

    /** km/h from the speed source status ("state=tap_kmh=68"), or null when not available. */
    static String kmh(String tap) {
        String st = get(tap, "state");
        if (st == null || !st.startsWith("tap_kmh=")) return null;
        String v = st.substring(8);
        return v.length() == 0 || v.startsWith("-") ? null : v;
    }

    static String[] lines(String src, String nat, String speed, String cfg, String pps, String tap) {
        String range = get(src, "range"), temp = get(src, "outsidetemp"), warn = get(src, "rangewarn");
        String state = get(src, "state");
        String mode = get(nat, "vstatus_mode");
        String sent = get(nat, "vstatus_sent"), would = get(nat, "vstatus_would_send"), last = get(nat, "vstatus_last");
        String sMode = get(speed, "mode"), sSent = get(speed, "sent"), sWould = get(speed, "would_send");
        String[] out = new String[7];
        out[0] = MibrI18n.pick("Fahrzeugdaten: ", "Vehicle data: ") + modeName(mode)
            + (state == null ? "" : " (" + state + ")");
        out[1] = MibrI18n.pick("Reichweite: ", "Range: ") + (range == null || range.equals("-1") ? "-" : range + " km")
            + "  " + MibrI18n.pick("Außentemp.: ", "Outside: ") + (temp == null || temp.equals("none") ? "-" : temp + " °C");
        out[2] = MibrI18n.pick("Tankwarnung: ", "Fuel warning: ")
            + (warn == null || warn.equals("-1") ? "-" : (warn.equals("1") ? MibrI18n.pick("an", "on") : MibrI18n.pick("aus", "off")));
        String engine = engineOf(cfg);
        out[3] = MibrI18n.pick("Im Identify angekündigt: ", "Announced in Identify: ") + onoff(announced(cfg))
            + (announced(cfg) && engine != null && MibrEngineState.index(engine) >= 0 ? " (" + MibrEngineState.name(engine) + ")" : "");
        out[4] = MibrI18n.pick("Vom iPhone angefordert: ", "Requested by iPhone: ") + requested(pps);
        out[5] = MibrI18n.pick("Gesendet: ", "Sent: ") + (sent == null ? "0" : sent)
            + MibrI18n.pick(" (wäre gesendet: ", " (would send: ") + (would == null ? "0" : would) + ")"
            + (last == null || last.length() == 0 ? "" : "  " + last);
        String v = kmh(tap);
        out[6] = MibrI18n.pick("Tempo: ", "Speed: ") + (v == null ? "-" : v + " km/h") + "  "
            + MibrI18n.pick("Modul: ", "Module: ") + modeName(sMode)
            + MibrI18n.pick(", gesendet ", ", sent ") + (sSent == null ? "0" : sSent)
            + MibrI18n.pick(" (wäre ", " (would ") + (sWould == null ? "0" : sWould) + ")";
        return out;
    }

    static String[] read() {
        String pps = null;
        for (int i = 0; i < PPS_CANDIDATES.length && pps == null; i++) pps = reader.read(PPS_CANDIDATES[i]);
        return lines(reader.read(SRC_STATUS), reader.read(NAT_STATUS), reader.read(SPEED_STATUS), reader.read(IAP2_CFG), pps, reader.read(SPEED_SOURCE));
    }
}