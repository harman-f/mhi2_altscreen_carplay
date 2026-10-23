package de.mibr.hmi;

import de.vw.mib.asl.framework.api.dsiproxy.DSIProxy;
import de.vw.mib.asl.framework.api.dsiproxy.DSIProxyFactory;
import de.vw.mib.asl.internal.system.SystemAccessor;
import de.vw.mib.genericevents.Target;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import org.dsi.ifc.base.DSIListener;
import org.dsi.ifc.carkombi.DSICarKombi;
import org.dsi.ifc.generalvehiclestates.DSIGeneralVehicleStates;
import org.dsi.ifc.generalvehiclestates.TankInfo;
import org.dsi.ifc.global.CarBCCurrentRange;
import org.dsi.ifc.global.CarBCDistance;
import org.dsi.ifc.global.CarBCTemperature;
import org.dsi.ifc.global.CarConstants;

/**
 * HMI-side source for the classic iAP2 VehicleStatus (range km, outside temperature, range warning) of the
 * CarPlay vehicle-data module. Default OFF: nothing is attached unless
 * /mnt/app/root/altscreen-u2/config/vstatus.mode says shadow or send. It only READS the stock DSI values
 * (DSICarKombi range/outside temperature, DSIGeneralVehicleStates TankInfo.fuelWarning) and publishes the
 * latest genuine values as a tiny key=value file for the native module inside dio_manager. A field that is
 * not valid is left out (never invented); all failures are swallowed.
 */
public final class MibrVstatusSource {
    private static final String MODE = "/mnt/app/root/altscreen-u2/config/vstatus.mode";
    private static final String OUT = "/tmp/mibr-vdata-status.vss";
    private static final String STATUS = "/tmp/mibr-vstatus-source.status";
    private static final long HEARTBEAT_MS = 30000L;
    private static boolean started;

    private int range = -1, temp = Integer.MIN_VALUE, warn = -1;
    private int seq;
    private int events, totalEvents, rangeEvents, tempEvents, tankEvents;
    private int totalResult = -99, rangeResult = -99, tempResult = -99, tankResult = -99;
    private long lastWrite;
    private boolean dirty;
    private int currentKm = -1, totalKm = -1;

    private MibrVstatusSource() { }

    public static synchronized void start() {
        if (started) return;
        started = true;
        final MibrVstatusSource source = new MibrVstatusSource();
        Thread worker = new Thread(new Runnable() { public void run() { source.loop(); } }, "MibrVstatus");
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

    /* ---- callbacks (any thread); keep them tiny and never throw ---- */
    synchronized void totalRange(CarBCDistance v, int result) {
        try {
            events++; totalEvents++; totalResult = result;
            int km = -1;
            if (v != null && result == 1 && v.distanceValueState == CarConstants.BCVALUESTATE_VALID) {
                double d = v.distanceValue;
                if (v.distanceUnit == CarConstants.DISTANCEUNIT_MI) d *= 1.609344;
                km = (int) Math.floor(d + 0.5);
            }
            totalKm = km;
            applyRange();
        } catch (Throwable ignored) { }
    }

    /** Primary range source: DSICarKombi ATTR_BCCURRENTRANGE1 (attr 8). */
    synchronized void currentRange1(CarBCCurrentRange v, int result) {
        try {
            events++; rangeEvents++; rangeResult = result;
            int km = -1;
            if (v != null && result == 1 && v.state == CarConstants.BCVALUESTATE_VALID) {
                double d = v.currentRangeValue;
                if (v.currentRangeUnit == CarConstants.DISTANCEUNIT_MI) d *= 1.609344;
                km = (int) Math.floor(d + 0.5);
            }
            currentKm = km;
            applyRange();
        } catch (Throwable ignored) { }
    }

    private void applyRange() {
        int km = currentKm >= 0 ? currentKm : totalKm;     /* total range is only a fallback */
        if (km > 2000) km = -1;
        if (km != range) { range = km; dirty = true; }
    }

    synchronized void outsideTemperature(CarBCTemperature v, int result) {
        try {
            events++; tempEvents++; tempResult = result;
            if (v == null || result != 1 || v.state != CarConstants.BCVALUESTATE_VALID) { if (temp != Integer.MIN_VALUE) { temp = Integer.MIN_VALUE; dirty = true; } return; }
            double c = v.temperatureValue;
            if (v.temperatureUnit == CarConstants.TEMPERATUREUNIT_F) c = (c - 32.0) * 5.0 / 9.0;
            int t = (int) Math.floor(c + 0.5);
            if (t < -60 || t > 80) return;
            if (t != temp) { temp = t; dirty = true; }
        } catch (Throwable ignored) { }
    }

    synchronized void tankInfo(TankInfo v, int result) {
        try {
            events++; tankEvents++; tankResult = result;
            int w = (v == null || result != 1) ? -1 : ((v.fuelWarning || v.fuelWarningSecondary) ? 1 : 0);
            if (w != warn) { warn = w; dirty = true; }
        } catch (Throwable ignored) { }
    }

    private synchronized void publishIfDue(boolean force) {
        long now = System.currentTimeMillis();
        if (!(dirty || force || now - lastWrite >= HEARTBEAT_MS)) return;
        if (range < 0 && temp == Integer.MIN_VALUE && warn < 0) { dirty = false; return; }
        StringBuffer b = new StringBuffer();
        if (range >= 0) b.append("range=").append(range).append('\n');
        if (temp != Integer.MIN_VALUE) b.append("outsidetemp=").append(temp).append('\n');
        if (warn >= 0) b.append("rangewarn=").append(warn).append('\n');
        b.append("seq=").append(++seq).append('\n');
        FileOutputStream out = null;
        try {
            /* File.renameTo fails on this QNX/J9: write the small final file directly in one write. */
            out = new FileOutputStream(OUT);
            out.write(b.toString().getBytes("US-ASCII"));
            out.close();
            out = null;
            dirty = false; lastWrite = now;
        } catch (Throwable t) {
        } finally {
            if (out != null) try { out.close(); } catch (Throwable ignored) { }
        }
    }

    private void status(String state, int attempts) {
        FileOutputStream out = null;
        try {
            String text = "state=" + state + "\nattempts=" + attempts + "\nevents=" + events + "\nrange=" + range +
                "\noutsidetemp=" + (temp == Integer.MIN_VALUE ? "none" : Integer.toString(temp)) + "\nrangewarn=" + warn +
                "\nev_total=" + totalEvents + "/" + totalResult + "\nev_range=" + rangeEvents + "/" + rangeResult +
                "\nev_temp=" + tempEvents + "/" + tempResult + "\nev_tank=" + tankEvents + "/" + tankResult + "\n";
            out = new FileOutputStream(STATUS);
            out.write(text.getBytes("US-ASCII"));
        } catch (Throwable ignored) {
        } finally {
            if (out != null) try { out.close(); } catch (Throwable ignored) { }
        }
    }

    /* ---- read-only taps on the stock caches (no DSI subscription of our own for the cluster values:
       the stock code holds the single listener for DSICarKombi; a second registration never delivered anything
       and could displace the OEM one) ---- */
    private static Object fieldOf(Object o, String name) {
        for (Class c = o == null ? null : o.getClass(); c != null; c = c.getSuperclass()) {
            try {
                java.lang.reflect.Field f = c.getDeclaredField(name);
                f.setAccessible(true);
                return f.get(o);
            } catch (NoSuchFieldException e) {
            } catch (Throwable t) { return null; }
        }
        return null;
    }

    private int oemErrors;
    private String oemState = "init";

    private void pollOem() {
        try {
            Object general = SystemAccessor.getGeneralTarget();
            Object temp0 = fieldOf(general, "outsideTemperature");
            Object valid = fieldOf(general, "outsideTemperatureValid");
            boolean ok = valid instanceof Boolean && ((Boolean) valid).booleanValue();
            outsideTemperature(temp0 instanceof CarBCTemperature && ok ? (CarBCTemperature) temp0 : null, ok ? 1 : 0);
            Object svc = de.vw.mib.asl.api.car.ASLCarFactory.getBordComputerAPI().getService();
            Object cur = fieldOf(svc, "primaryEngine");
            currentRange1(cur instanceof CarBCCurrentRange ? (CarBCCurrentRange) cur : null, cur == null ? 0 : 1);
            oemState = "polling";
        } catch (Throwable t) {
            oemErrors++;
            oemState = "error_" + t.getClass().getName();
        }
    }

    private void loop() {
        MibrVstatusAdapter listener = new MibrVstatusAdapter(this);
        DSIGeneralVehicleStates general = null;
        int attempts = 0;
        while (true) {
            try {
                String state;
                if (!enabled()) {
                    if (general != null) {
                        try { general.clearNotification(new int[] { DSIGeneralVehicleStates.ATTR_TANKINFO }, (DSIListener) listener); } catch (Throwable ignored) { }
                        general = null;
                    }
                    state = "off";
                } else {
                    if (general == null) {
                        attempts++;
                        DSIProxy proxy = DSIProxyFactory.getDSIProxyAPI().getDSIProxy();
                        Target owner = SystemAccessor.getVehicleStatesTarget();
                        if (proxy != null && owner != null) {
                            DSIGeneralVehicleStates g = (DSIGeneralVehicleStates) proxy.getService(owner, DSIGeneralVehicleStates.class);
                            if (g != null) {
                                g.setNotification(new int[] { DSIGeneralVehicleStates.ATTR_TANKINFO }, (DSIListener) listener);
                                general = g;
                            }
                        }
                    }
                    pollOem();
                    state = (general != null ? "attached" : "waiting") + "/" + oemState;
                    publishIfDue(false);
                }
                status(state, attempts);
                Thread.sleep(enabled() ? 1000L : 5000L);
            } catch (InterruptedException e) {
                return;
            } catch (Throwable t) {
                status("error_" + t.getClass().getName(), attempts);
                try { Thread.sleep(10000L); } catch (InterruptedException e) { return; }
            }
        }
    }
}