package de.mibr.hmi;

import de.vw.mib.asl.framework.api.dsiproxy.DSIProxy;
import de.vw.mib.asl.framework.api.dsiproxy.DSIProxyFactory;
import de.vw.mib.asl.internal.system.SystemAccessor;
import de.vw.mib.genericevents.Target;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.util.Vector;
import mib.mu1440.vehiclespeed.DsiVehicleSpeedAdapter;
import mib.mu1440.vehiclespeed.Mu1440CarBCSpeedDecoder;
import org.dsi.ifc.global.CarBCSpeed;

/**
 * HMI-side vehicle speed source for the CarPlay vehicle-data module.
 * Default OFF: nothing is attached unless /mnt/app/root/altscreen-u2/config/vdata.mode says shadow or send.
 * It only READS the stock DSI speed through the vendored R1 adapter and writes the last genuine events as
 * MVS1 records into a small ring file that the native module (inside dio_manager) reads. It never
 * touches OEM state, never blocks an OEM thread and swallows every failure.
 */
public final class MibrVdataBridge {
    private static final String MODE = "/mnt/app/root/altscreen-u2/config/vdata.mode";
    private static final String RING = "/tmp/mibr-vdata-speed.ring";
    private static final String STATUS = "/tmp/mibr-vdata-source.status";
    private static final int RING_RECORDS = 8;
    private static boolean started;

    private MibrVdataBridge() { }

    /** Called once from the activator; returns at once, all work runs in one daemon thread. */
    public static synchronized void start() {
        if (started) return;
        started = true;
        Thread worker = new Thread(new Runnable() { public void run() { loop(); } }, "MibrVdata");
        worker.setDaemon(true);
        worker.start();
    }

    private static boolean enabled() {
        FileInputStream in = null;
        try {
            byte[] b = new byte[16];
            in = new FileInputStream(MODE);
            int n = in.read(b);
            if (n < 4) return false;
            String s = new String(b, 0, n, "US-ASCII");
            return s.startsWith("shadow") || s.startsWith("send");
        } catch (Throwable t) {
            return false;
        } finally {
            if (in != null) try { in.close(); } catch (Throwable ignored) { }
        }
    }

    private static final class Ring implements DsiVehicleSpeedAdapter.Policy {
        private final Vector records = new Vector();
        long offers, failures, lastMmps = -1L;

        public boolean ready() { return true; }
        public int toMillimetresPerSecond(CarBCSpeed speed) {
            return Mu1440CarBCSpeedDecoder.toMillimetresPerSecond(speed);
        }
        /** Relative time only: the native side re-bases the newest record to the file age. */
        public long monotonicMillis() { return System.currentTimeMillis(); }
        public synchronized boolean offer(byte[] mvs1) {
            if (mvs1 == null || mvs1.length != 24) return false;
            offers++;
            lastMmps = (mvs1[16] & 0xffL) | ((mvs1[17] & 0xffL) << 8) | ((mvs1[18] & 0xffL) << 16) | ((mvs1[19] & 0xffL) << 24);
            records.addElement(mvs1);
            while (records.size() > RING_RECORDS) records.removeElementAt(0);
            return flush();
        }
        private boolean flush() {
            FileOutputStream out = null;
            try {
                /* File.renameTo fails on this QNX/J9 (127 of 127 in the first run): write the final file directly,
                   as one buffer in one write; the native reader validates every record. */
                byte[] all = new byte[records.size() * 24];
                for (int i = 0; i < records.size(); i++) System.arraycopy((byte[]) records.elementAt(i), 0, all, i * 24, 24);
                out = new FileOutputStream(RING);
                out.write(all);
                out.close();
                out = null;
                return true;
            } catch (Throwable t) {
                failures++;
                return false;
            } finally {
                if (out != null) try { out.close(); } catch (Throwable ignored) { }
            }
        }
        synchronized void clearFile() { records.removeAllElements(); try { new File(RING).delete(); } catch (Throwable ignored) { } }
    }

    private static void status(String state, Ring ring, int attempts) {
        FileOutputStream out = null;
        try {
            String text = "state=" + state + "\nattempts=" + attempts +
                "\noffers=" + (ring == null ? 0L : ring.offers) +
                "\nwrite_failures=" + (ring == null ? 0L : ring.failures) +
                "\nlast_speed_mmps=" + (ring == null ? -1L : ring.lastMmps) + "\n";
            out = new FileOutputStream(STATUS);
            out.write(text.getBytes("US-ASCII"));
        } catch (Throwable ignored) {
        } finally {
            if (out != null) try { out.close(); } catch (Throwable ignored) { }
        }
    }

    /** Read-only tap: the stock vehicle-states target keeps the last valid speed as integer km/h in oldVelocity. */
    private static int stockKmh(Object target) {
        for (Class c = target == null ? null : target.getClass(); c != null; c = c.getSuperclass()) {
            try {
                java.lang.reflect.Field f = c.getDeclaredField("oldVelocity");
                f.setAccessible(true);
                return f.getInt(target);
            } catch (NoSuchFieldException e) {
            } catch (Throwable t) { return -1; }
        }
        return -1;
    }

    private static void loop() {
        Ring ring = new Ring();
        DsiVehicleSpeedAdapter adapter = null;
        int attempts = 0, lastKmh = -2;
        long lastFeed = 0L;
        String last = "";
        while (true) {
            try {
                boolean on = enabled();
                String state;
                if (!on) {
                    if (adapter != null) { adapter.close(); adapter = null; ring.clearFile(); lastKmh = -2; }
                    state = "off";
                } else {
                    Object owner = SystemAccessor.getVehicleStatesTarget();
                    if (owner == null) state = "waiting_for_asl";
                    else {
                        if (adapter == null) {
                            attempts++;
                            adapter = DsiVehicleSpeedAdapter.offline(ring);
                            adapter.beginCarPlaySession(1L);
                        }
                        int kmh = stockKmh(owner);
                        long now = System.currentTimeMillis();
                        if (kmh >= 0 && (kmh != lastKmh || now - lastFeed >= 500L)) {
                            org.dsi.ifc.carvehiclestates.DynamicVehicleInfoHighFrequent hf =
                                new org.dsi.ifc.carvehiclestates.DynamicVehicleInfoHighFrequent();
                            hf.vehicleSpeed = new CarBCSpeed(org.dsi.ifc.global.CarConstants.BCVALUESTATE_VALID,
                                (float) kmh, org.dsi.ifc.global.CarConstants.SPEEDUNIT_KMPH);
                            adapter.updateDynamicVehicleInfoHighFrequent(hf, 1);
                            lastKmh = kmh;
                            lastFeed = now;
                        }
                        state = "tap_kmh=" + kmh;
                    }
                }
                if (!state.equals(last) || adapter != null) status(state, ring, attempts);
                last = state;
                Thread.sleep(adapter != null ? 200L : 5000L);
            } catch (InterruptedException e) {
                return;
            } catch (Throwable t) {
                status("error_" + t.getClass().getName(), ring, attempts);
                try { Thread.sleep(10000L); } catch (InterruptedException e) { return; }
            }
        }
    }
}