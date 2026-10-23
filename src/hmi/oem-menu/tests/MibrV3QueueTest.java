package de.mibr.hmi;

import java.util.Vector;

/** r12: rapid checkbox taps during a running SET are queued and saved, never lost or desynchronised. */
public final class MibrV3QueueTest {
    static void check(boolean b, String m) { if (!b) throw new AssertionError(m); }

    static final class Fake extends MibrV3Client {
        int sets, rev = 30;
        final Vector held = new Vector();
        Fake() { super(28743, "/unread/host/fixture"); }
        public synchronized boolean send(String rid, String verb, String[] names, String[] values, Listener cb) {
            String response;
            if ("HELLO".equals(verb)) response = MibrV3BindingTest.reply(rid, new String[]{"version", "schema", "registry_keys", "phase"},
                new String[]{"MIBR/3", "2", "48", "NATIVE_PROFILE_GUARDED"});
            else if ("CAPABILITIES".equals(verb)) response = MibrV3BindingTest.caps(rid, true);
            else if ("SNAPSHOT".equals(verb)) response = MibrV3BindingTest.snapshot(rid, Integer.toString(rev), "20");
            else if ("SET".equals(verb)) {
                sets++;
                held.addElement(new Object[]{rid, values[0], values[1], cb});
                return true;
            } else if ("ENGINE_GET".equals(verb) || "ENGINE_SET".equals(verb)) response = MibrV3BindingTest.reply(rid, new String[]{"engine", "announced", "pending"}, new String[]{"gas", "gas", "0"}); else if ("VIEW_GET".equals(verb) || "VIEW_SET".equals(verb)) response = MibrV3BindingTest.reply(rid, new String[]{"follow", "sport", "m0", "m1", "m4", "rs", "pos"}, new String[]{"0", "1", "1", "0", "2", "0", "0"}); else throw new AssertionError(verb);
            cb.onReply(MibrV3Protocol.parse(response, rid), null);
            return true;
        }
        /** Completes the oldest held SET like the native service (stores, bumps revision, replies). */
        void release() {
            Object[] h = (Object[]) held.elementAt(0);
            held.removeElementAt(0);
            MibrV3BindingTest.OVERRIDE.put(h[1], h[2]);
            rev++;
            String rid = (String) h[0];
            String response = MibrV3BindingTest.reply(rid,
                new String[]{"stored", "apply", "active", "activation", "revision", "materialized"},
                new String[]{"VERIFIED", "PENDING", "UNKNOWN", "PRESENTATION", Integer.toString(rev), "1"});
            ((Listener) h[3]).onReply(MibrV3Protocol.parse(response, rid), null);
        }
    }

    static MibrPopupEditorModel open(Fake fake, MibrV3Session[] out) {
        MibrV3BindingTest.OVERRIDE.clear();
        MibrPopupEditorModel model = new MibrPopupEditorModel();
        model.setAvailable(true);
        MibrV3Session s = new MibrV3Session(fake, model, new MibrV3Session.Dispatcher() {
            public void post(Runnable action) { action.run(); }
        }, new Runnable() { public void run() { } });
        s.open();
        out[0] = s;
        check(s.canWrite(), "ready");
        return model;
    }

    public static void main(String[] args) {
        final int ETA = MibrV3BindingTest.idx("navigation.ETA");
        final int COMP = MibrV3BindingTest.idx("navigation.compass");
        // A: two different checkboxes tapped while the first SET is in flight.
        Fake fake = new Fake();
        MibrV3Session[] box = new MibrV3Session[1];
        MibrPopupEditorModel m = open(fake, box);
        MibrV3Session s = box[0];
        check(m.toggle(ETA), "toggle ETA");
        s.commit(ETA);
        check(fake.sets == 1 && !s.canWrite(), "SET #1 in flight");
        check(m.toggle(COMP), "toggle compass during SET");
        s.commit(COMP);
        check(fake.sets == 1, "no second parallel SET");
        fake.release();
        check("yes".equals(m.current(ETA)) && m.draft(ETA) == null, "ETA saved and confirmed");
        check(fake.sets == 2 && "yes".equals(m.draft(COMP)), "queued compass SET sent after #1");
        fake.release();
        check("yes".equals(m.current(COMP)) && m.draft(COMP) == null && s.canWrite(), "compass saved, editor writable");
        check(s.status().indexOf("Dauerhaft gespeichert") >= 0, "status " + s.status());
        // B: same checkbox tapped twice while its SET runs -> final value is the last tap.
        fake = new Fake();
        m = open(fake, box);
        s = box[0];
        m.toggle(ETA);
        s.commit(ETA);
        m.toggle(ETA);
        s.commit(ETA);
        check(fake.sets == 1, "second tap queued");
        fake.release();
        check("yes".equals(m.current(ETA)) && "no".equals(m.draft(ETA)), "newer draft kept after SET #1");
        check(fake.sets == 2, "SET #2 for the newer tap");
        fake.release();
        check("no".equals(m.current(ETA)) && m.draft(ETA) == null && s.canWrite(), "final value no, writable");
        // C: tapped on and straight back off -> nothing left to save, no stuck state.
        fake = new Fake();
        m = open(fake, box);
        s = box[0];
        m.toggle(ETA);
        s.commit(ETA);
        m.toggle(COMP);
        s.commit(COMP);
        m.toggle(COMP);
        s.commit(COMP);
        fake.release();
        check(fake.sets == 1 || fake.sets == 2, "bounded SETs");
        while (fake.held.size() > 0) fake.release();
        check(s.canWrite(), "writable after drain");
        System.out.println("MIBR_V3_QUEUE_HOST_PASS sets=" + fake.sets);
    }
}
