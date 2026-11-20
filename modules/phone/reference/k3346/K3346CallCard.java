package de.audi.app.combi.bap.app.phone;

import de.audi.app.terminalmode.k3346.K3346Diag;
import de.audi.app.terminalmode.k3346.K3346HmiLanguage;
import java.io.FileOutputStream;
import java.io.IOException;

/*
 * Tells vc_overlay what the call card shows, format in overlay/call_card.h:
 *   <state>\n<name>\n<label>\nEND\n
 * /tmp on QNX has no rename(), so the text goes out in one write and ends with a
 * marker. The caller's name stays out of the logs: it is personal data.
 */
final class K3346CallCard {
    private static final int NAME_MAX_BYTES = 127;
    private static final String NO_CALL = "\n\n\nEND\n";

    static String path = "/tmp/vc-call-card";

    private static String last = null;

    private K3346CallCard() {
    }

    static void update(K3346PpsCall c) {
        try {
            write(text(K3346GatedPhoneService.bapState(c), c.name, c.number, K3346HmiLanguage.isPolish()));
        } catch (Throwable t) {
            K3346Diag.log("K3346_CALL_CARD update_failed " + t.getClass().getName());
        }
    }

    static void clear() {
        try {
            write(NO_CALL);
        } catch (Throwable t) {
            K3346Diag.log("K3346_CALL_CARD clear_failed " + t.getClass().getName());
        }
    }

    /* A forgotten text forces the next write, for the host test. */
    static void forget() {
        last = null;
    }

    static String text(int bapState, String name, String number, boolean polish) {
        String state;
        String label;
        switch (bapState) {
            case K3346GatedPhoneService.BAP_RINGING:
                state = "R";
                label = polish ? "Dzwoni" : "Incoming call";
                break;
            case K3346GatedPhoneService.BAP_DIALING:
                state = "D";
                label = polish ? "Łączenie" : "Calling";
                break;
            case K3346GatedPhoneService.BAP_ACTIVE:
                state = "A";
                label = polish ? "Trwa rozmowa" : "In call";
                break;
            case K3346GatedPhoneService.BAP_HELD:
                state = "H";
                label = polish ? "Wstrzymana" : "On hold";
                break;
            default:
                return NO_CALL;
        }
        return state + "\n" + limit(shownName(name, number, polish)) + "\n" + label + "\nEND\n";
    }

    static String shownName(String name, String number, boolean polish) {
        String n = oneLine(name);
        if (n.length() > 0) {
            return n;
        }
        String d = oneLine(number);
        if (d.length() > 0) {
            return d;
        }
        return polish ? "Nieznany numer" : "Unknown number";
    }

    private static String oneLine(String s) {
        return s == null ? "" : s.replace('\n', ' ').replace('\r', ' ').trim();
    }

    /* The overlay refuses a longer line. Whole characters only. */
    static String limit(String s) {
        int bytes = 0;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            int size;
            if (c < 0x80) {
                size = 1;
            } else if (c < 0x800) {
                size = 2;
            } else if (c >= 0xD800 && c <= 0xDBFF) {
                size = 4;
            } else {
                size = 3;
            }
            if (bytes + size > NAME_MAX_BYTES) {
                return s.substring(0, i);
            }
            bytes += size;
            if (size == 4) {
                i++;
            }
        }
        return s;
    }

    private static void write(String text) throws IOException {
        if (text.equals(last)) {
            return;
        }
        FileOutputStream out = new FileOutputStream(path);
        try {
            out.write(text.getBytes("UTF-8"));
        } finally {
            out.close();
        }
        last = text;
        K3346Diag.log("K3346_CALL_CARD state=" + (text.charAt(0) == '\n' ? "none" : text.substring(0, 1)));
    }
}
