package de.mibr.extender;

import java.io.File;
import java.io.FileOutputStream;

/** P1 bootstrap plus bounded, best-effort activation diagnostics. No module loader. */
public final class MibrExtenderCore {
    private static final String STATUS = "/tmp/mibr-hmi-activation.status";
    private static final int MAX_STATUS_BYTES = 2048;
    private static final String[] ALLOWED = {
        "P1_SESSION_START", "SPI_ENTERED", "MODULES_DISABLED",
        "BEFORE_AUTOSTART", "FAIL_P1_CONSTRUCTOR", "FAIL_PREAUTOSTART"
    };
    private static final String[] WRITTEN = new String[ALLOWED.length];
    private static int writtenCount;
    private static boolean constructed;
    private static boolean preautostart;

    private MibrExtenderCore() { }

    static synchronized void constructed() {
        if (constructed) return;
        constructed = true;
        resetStatus();
        stage("P1_SESSION_START");
        stage("SPI_ENTERED");
        stage("MODULES_DISABLED");
        marker("MIBR_EXT_P1_CONSTRUCTED");
        marker("MIBR_EXT_P1_MODULES_DISABLED");
    }

    /** Start a fresh volatile record so markers from an earlier IOC run cannot look current. */
    private static void resetStatus() {
        FileOutputStream out = null;
        try {
            out = new FileOutputStream(STATUS, false);
            out.write("FORMAT=1\n".getBytes());
            out.flush();
        } catch (Throwable ignored) {
            marker("MIBR_HMI_STATUS_RESET_FAILED");
        } finally {
            if (out != null) {
                try { out.close(); } catch (Throwable ignored) { }
            }
        }
    }

    static synchronized void beforeAutostart() {
        if (preautostart) return;
        preautostart = true;
        stage("BEFORE_AUTOSTART");
        marker("MIBR_EXT_P1_BEFORE_AUTOSTART");
    }

    /**
     * Append one allow-listed lifecycle stage to a flat volatile status file.
     * File access is diagnostic only and every error is swallowed so OEM startup
     * and menu behavior never depend on /tmp being writable.
     */
    public static synchronized void stage(String name) {
        int index = -1;
        for (int i = 0; i < ALLOWED.length; i++) {
            if (ALLOWED[i].equals(name)) { index = i; break; }
        }
        if (index < 0) return;
        for (int i = 0; i < writtenCount; i++) {
            if (WRITTEN[i].equals(name)) return;
        }

        FileOutputStream out = null;
        try {
            File file = new File(STATUS);
            boolean header = file.length() == 0;
            if (file.length() + name.length() + 12 > MAX_STATUS_BYTES) return;
            out = new FileOutputStream(STATUS, true);
            if (header) out.write("FORMAT=1\n".getBytes());
            out.write(name.getBytes());
            out.write('\n');
            out.flush();
            WRITTEN[writtenCount++] = name;
        } catch (Throwable ignored) {
            marker("MIBR_HMI_STATUS_WRITE_FAILED");
        } finally {
            if (out != null) {
                try { out.close(); } catch (Throwable ignored) { }
            }
        }
    }

    static void error(String phase, Throwable failure) {
        if ("construct".equals(phase)) stage("FAIL_P1_CONSTRUCTOR");
        if ("preautostart".equals(phase)) stage("FAIL_PREAUTOSTART");
        try { System.err.println("MIBR_EXT_P1_FAILURE phase=" + phase + " type=" + failure.getClass().getName()); }
        catch (Throwable ignored) { }
    }

    private static void marker(String message) {
        try { System.err.println(message); }
        catch (Throwable ignored) { }
    }
}
