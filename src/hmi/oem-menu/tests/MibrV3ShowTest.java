package de.mibr.hmi;

/** r23: the status text claims "Im Cockpit" only after SHOW_STATUS reports SHOWN. */
public final class MibrV3ShowTest {
    static void check(boolean b, String m) { if (!b) throw new AssertionError(m); }

    static final class Fake extends MibrV3Client {
        String revision = "40";
        volatile int showCalls;
        volatile String[] states = {"PENDING", "PENDING", "SHOWN"};
        Fake() { super(28743, "/unread/host/fixture"); }
        public synchronized boolean send(String rid, String verb, String[] names, String[] values, Listener cb) {
            String response;
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
                int i = Math.min(showCalls++, states.length - 1);
                response = MibrV3BindingTest.reply(rid, new String[]{"state"}, new String[]{states[i]});
            } else if ("ENGINE_GET".equals(verb) || "ENGINE_SET".equals(verb)) response = MibrV3BindingTest.reply(rid, new String[]{"engine", "announced", "pending"}, new String[]{"gas", "gas", "0"}); else if ("VIEW_GET".equals(verb) || "VIEW_SET".equals(verb)) response = MibrV3BindingTest.reply(rid, new String[]{"follow", "sport", "m0", "m1", "m4", "rs", "pos"}, new String[]{"0", "1", "1", "0", "2", "0", "0"}); else throw new AssertionError(verb);
            cb.onReply(MibrV3Protocol.parse(response, rid), null);
            return true;
        }
    }

    static String waitFor(MibrV3Session s, String part, long ms) throws Exception {
        long end = System.currentTimeMillis() + ms;
        while (System.currentTimeMillis() < end) {
            if (s.status().indexOf(part) >= 0) return s.status();
            Thread.sleep(50);
        }
        throw new AssertionError("timeout waiting for '" + part + "', status=" + s.status());
    }

    static void run(String[] states, String expected, boolean mustNotClaimBefore) throws Exception {
        MibrV3BindingTest.OVERRIDE.clear();
        Fake fake = new Fake();
        fake.states = states;
        MibrPopupEditorModel model = new MibrPopupEditorModel();
        model.setAvailable(true);
        MibrV3Session s = new MibrV3Session(fake, model, new MibrV3Session.Dispatcher() {
            public void post(Runnable action) { action.run(); }
        }, new Runnable() { public void run() { } });
        s.open();
        int compass = MibrV3BindingTest.idx("navigation.compass");
        check(s.canWrite() && model.toggle(compass), "ready and toggled");
        s.commit(compass);
        check(s.status().indexOf("Im Cockpit") < 0, "no claim right after the reply: " + s.status());
        if (mustNotClaimBefore) check(s.status().indexOf("Bestätigung vom Cockpit") >= 0, "waiting text: " + s.status());
        waitFor(s, expected, 15000);
        check(fake.showCalls >= 1, "SHOW_STATUS was polled");
        s.detach();
    }

    public static void main(String[] args) throws Exception {
        run(new String[]{"PENDING", "PENDING", "SHOWN"}, "Im Cockpit bestätigt", true);
        run(new String[]{"PENDING", "NO_SESSION"}, "nächsten CarPlay-Verbindung", true);
        run(new String[]{"PENDING", "FAILED"}, "nicht bestätigt", true);
        System.out.println("MIBR_V3_SHOW_CONFIRM_HOST_PASS");
    }
}
