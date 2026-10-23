package de.mibr.hmi;

/** A cockpit-confirmation poll that briefly holds the one-request client must not lock the menu:
 *  a tap during the poll is retried and saved (owner report 2026-10-21, menu dead after Center). */
public final class MibrV3BusyTest {
    static void check(boolean b, String m) { if (!b) throw new AssertionError(m); }

    static final class SlowShow extends MibrV3Client {
        String revision = "40";
        volatile boolean pending;
        volatile int refused, showCalls;
        SlowShow() { super(28744, "/unread/host/fixture"); }
        public synchronized boolean send(final String rid, String verb, String[] names, String[] values, final Listener cb) {
            if (pending) { refused++; return false; }
            final String response;
            if ("HELLO".equals(verb)) response = MibrV3BindingTest.reply(rid, new String[]{"version", "schema", "registry_keys", "phase"},
                new String[]{"MIBR/3", "2", "48", "NATIVE_PROFILE_GUARDED"});
            else if ("CAPABILITIES".equals(verb)) response = MibrV3BindingTest.caps(rid, true);
            else if ("SNAPSHOT".equals(verb)) response = MibrV3BindingTest.snapshot(rid, revision, "20");
            else if ("SET".equals(verb)) {
                MibrV3BindingTest.OVERRIDE.put(values[0], values[1]);
                revision = Integer.toString(Integer.parseInt(revision) + 1);
                response = MibrV3BindingTest.reply(rid,
                    new String[]{"stored", "apply", "active", "activation", "revision", "materialized"},
                    new String[]{"PENDING_PERSIST", "PENDING", "UNKNOWN", "PRESENTATION", revision, "1"});
            } else if ("SHOW_STATUS".equals(verb)) {
                // Holds the client for 600 ms like a slow socket round trip.
                showCalls++;
                pending = true;
                new Thread(new Runnable() { public void run() {
                    try { Thread.sleep(600); } catch (InterruptedException e) { }
                    synchronized (SlowShow.this) { pending = false; }
                    cb.onReply(MibrV3Protocol.parse(MibrV3BindingTest.reply(rid, new String[]{"state"},
                        new String[]{"PENDING"}), rid), null);
                }}).start();
                return true;
            } else if ("ENGINE_GET".equals(verb) || "ENGINE_SET".equals(verb)) response = MibrV3BindingTest.reply(rid, new String[]{"engine", "announced", "pending"}, new String[]{"gas", "gas", "0"}); else if ("VIEW_GET".equals(verb) || "VIEW_SET".equals(verb)) response = MibrV3BindingTest.reply(rid, new String[]{"follow", "sport", "m0", "m1", "m4", "rs", "pos"}, new String[]{"0", "1", "1", "0", "2", "0", "0"}); else throw new AssertionError(verb);
            cb.onReply(MibrV3Protocol.parse(response, rid), null);
            return true;
        }
    }

    public static void main(String[] a) throws Exception {
        MibrV3BindingTest.OVERRIDE.clear();
        SlowShow fake = new SlowShow();
        MibrPopupEditorModel model = new MibrPopupEditorModel();
        model.setAvailable(true);
        MibrV3Session s = new MibrV3Session(fake, model, new MibrV3Session.Dispatcher() {
            public void post(Runnable action) { synchronized (MibrV3BusyTest.class) { action.run(); } }
        }, new Runnable() { public void run() { } });
        s.open();
        int compass = MibrV3BindingTest.idx("navigation.compass");
        int eta = MibrV3BindingTest.idx("navigation.ETA");
        check(s.canWrite() && model.toggle(compass), "ready and toggled compass");
        s.commit(compass);
        // Wait until the confirmation poll holds the client, then tap the next row.
        long end = System.currentTimeMillis() + 5000;
        while (!fake.pending && System.currentTimeMillis() < end) Thread.sleep(10);
        check(fake.pending, "poll holds the client");
        synchronized (MibrV3BusyTest.class) {
            check(model.toggle(eta), "toggled ETA");
            s.commit(eta);
        }
        end = System.currentTimeMillis() + 5000;
        while (!MibrV3BindingTest.OVERRIDE.containsKey("navigation.ETA") && System.currentTimeMillis() < end) Thread.sleep(20);
        check(MibrV3BindingTest.OVERRIDE.containsKey("navigation.ETA"), "ETA saved after the poll, status=" + s.status());
        check(fake.refused >= 1, "the busy client was hit at least once");
        check(s.status().indexOf("beschäftigt") < 0, "menu not locked: " + s.status());
        Thread.sleep(300);
        check(s.canWrite(), "menu writable again, status=" + s.status());
        s.detach();
        System.out.println("MIBR_V3_BUSY_RETRY_TEST_PASS refused=" + fake.refused + " polls=" + fake.showCalls);
    }
}
