package de.mibr.hmi;

import java.util.Vector;

/**
 * Host end-to-end: the r8 Java session against the REAL native MIBR/3 service
 * (PR102 C source + pinned original settings core), started by
 * test_v3_native_e2e.py. Args: port secretFile mode(readonly|durable).
 */
public final class MibrV3NativeE2E {
    private static final Vector queue = new Vector();
    private static void check(boolean b, String m) { if (!b) throw new AssertionError(m); }
    private static int index(String key) {
        for (int i = 0; i < MibrSettingsCatalog.KEYS.length; i++)
            if (key.equals(MibrSettingsCatalog.KEYS[i])) return i;
        throw new AssertionError(key);
    }
    /** Drains the simulated OEM dispatcher until the status matches or times out. */
    private static String await(MibrV3Session s, String[] wanted, long ms) throws Exception {
        long end = System.currentTimeMillis() + ms;
        while (System.currentTimeMillis() < end) {
            Runnable r = null;
            synchronized (queue) { if (!queue.isEmpty()) { r = (Runnable) queue.elementAt(0); queue.removeElementAt(0); } }
            if (r != null) { r.run(); continue; }
            for (int i = 0; i < wanted.length; i++) if (s.status().indexOf(wanted[i]) >= 0) return s.status();
            Thread.sleep(10);
        }
        throw new AssertionError("timeout; status=" + s.status());
    }
    public static void main(String[] a) throws Exception {
        int port = Integer.parseInt(a[0]);
        boolean deferred = "deferred".equals(a[2]);
        boolean durable = "durable".equals(a[2]) || deferred;
        MibrPopupEditorModel model = new MibrPopupEditorModel();
        model.setAvailable(true);
        final int[] repaints = {0};
        MibrV3Session s = new MibrV3Session(new MibrV3Client(port, a[1]), model,
            new MibrV3Session.Dispatcher() { public void post(Runnable r) { synchronized (queue) { queue.addElement(r); } } },
            new Runnable() { public void run() { repaints[0]++; } });
        s.open();
        String ready = await(s, new String[] {"Bereit", "Nur Lesen", "nicht", "fehlt", "unbestätigt"}, 8000);
        check(durable ? ready.indexOf("Bereit") >= 0 : ready.indexOf("Nur Lesen") >= 0, "open: " + ready);
        int fps = index("navigation.maneuver"), url = index("navigation.url"), view = index("viewarea.selected");
        check(model.current(fps) != null, "maneuver read back from the native core");
        check(model.current(url) != null && !MibrPopupEditorModel.visible(url),
              "hidden navigation.url still parsed from the native 11-row snapshot");
        check(model.current(view) != null && model.open(view), "view value read, dropdown open");model.cancel();
        String[] fpsOptions = model.options(fps);
        String before = model.current(fps), wanted = null;
        for (int i = 0; i < fpsOptions.length; i++) if (!fpsOptions[i].equals(before)) { wanted = fpsOptions[i]; break; }
        check(wanted != null, "a different maneuver choice exists");
        int option = -1;
        for (int i = 0; i < fpsOptions.length; i++) if (fpsOptions[i].equals(wanted)) option = i;
        check(model.open(fps) && model.choose(option), "local maneuver draft");
        s.commit(fps);
        String after = await(s, new String[] {"Dauerhaft gespeichert", "Angezeigt; wird in Kürze", "nicht verfügbar", "nicht freigeschaltet",
                                              "unklar", "Speichern"}, 8000);
        if (deferred) {
            check(after.indexOf("Angezeigt; wird in Kürze") >= 0, "deferred SET answers at once: " + after);
            check(wanted.equals(model.current(fps)) && model.draft(fps) == null,
                  "live value confirmed from the TEMP snapshot, draft cleared");
        } else if (durable) {
            check(after.indexOf("Dauerhaft gespeichert") >= 0, "durable SET: " + after);
            check(wanted.equals(model.current(fps)) && model.draft(fps) == null,
                  "post-commit snapshot confirmed the value and cleared the draft");
        } else {
            check(after.indexOf("Dauerhaft gespeichert") < 0 && wanted.equals(model.draft(fps)) &&
                  before.equals(model.current(fps)), "read-only: no SET, draft kept: " + after);
        }
        int enabled = index("carplay.enabled");
        model.toggle(enabled);
        s.commit(enabled);
        String gated = await(s, new String[] {"Laufzeitaktion", "nicht verfügbar", "nicht freigegeben"}, 3000);
        check(gated.indexOf("Dauerhaft gespeichert") < 0, "carplay.enabled is never a durable SET");
        s.detach();
        System.out.println("MIBR_V3_NATIVE_E2E_PASS mode=" + a[2] + " maneuver " + before + "->" +
                           (durable ? wanted : before) + " repaints=" + repaints[0]);
    }
}
