package de.mibr.hmi;

import de.vw.mib.cio.CioActionParameters;
import de.vw.mib.cio.CioDictionary;
import de.vw.mib.cio.CioDispatcher;
import de.vw.mib.cio.CioExecutor;
import de.vw.mib.cio.CioIntent;
import de.vw.mib.cio.CioRegistrationListener;
import de.vw.mib.cio.ContentInformationObject;
import de.vw.mib.cio.app.framework.AppFrameworkCioFactory;
import de.vw.mib.cio.app.framework.CioIntentDefinition;
import de.vw.mib.cio.framework.CioIdService;
import de.vw.mib.cio.framework.CioIntentVisualization;
import de.vw.mib.cio.framework.CioVisualizationService;
import de.vw.mib.graphics.image.Image;
import java.io.File;
import java.io.FileOutputStream;

/** Independent exact-MU1440 native HOME CIO. R4 QA pages only, no settings writes. */
public final class MibrHomeCio {
    private static final String STATUS = "/tmp/mibr-hmi-activation.status";
    private static final int MAX_STATUS_BYTES = 2048;
    private static final String[] STATUS_STAGES = {
        "CIO_ACTIVATOR_STARTED", "CIO_FACTORY_BOUND", "CIO_SERVICES_READY",
        "CIO_LISTENER_READY", "CIO_INTENT_SCAN_COMPLETE", "CIO_MENU_ACTION_CANDIDATE",
        "CIO_GRID_VIS_READY", "CIO_REGISTERED", "CIO_DETACHED",
        "HOME_TILE_VIS_REQUESTED", "HOME_TILE_VIS_RETURNED", "HOME_HOST_READY", "HOME_HOST_DETACHED",
        "HOME_HOST_DUPLICATE", "HOME_HOST_MATCHED", "HOME_HOST_NOT_READY",
        "HOME_CIO_EXECUTED", "PANEL_HOME_RENDERED", "PANEL_MENU_RENDERED",
        "PANEL_DETAIL_RENDERED", "BACK_ACTION", "FAIL_ACTIVATION_PREREQUISITE",
        "FAIL_ACTIVATION", "FAIL_CIO_DETACH", "FAIL_GRID_VISUAL", "FAIL_GRID_ICONS", "FAIL_CIO_REGISTER",
        "FAIL_TILE_VIS_FALLBACK", "FAIL_HOME_HOST"
    };
    private static final String[] WRITTEN_STAGES = new String[STATUS_STAGES.length];
    private static int writtenStageCount;
    public static final String APP = "MIBR";
    public static final String INSTANCE = "HmiQa";
    public static final String CIO = "VirtualCockpitHome";
    public static final String VIS = "VirtualCockpitHomeVisual";
    private static AppFrameworkCioFactory factory;
    private static CioDictionary dictionary;
    private static CioDispatcher dispatcher;
    private static CioIdService ids;
    private static MibrVisualizationService visualization;
    private static CioRegistrationListener registrationListener;
    private static Definition definition;
    private static boolean listening;
    private static boolean registered;

    private MibrHomeCio() {}

    /** Best-effort allow-listed diagnostic; never required for stock HMI startup. */
    public static synchronized void stage(String name) {
        boolean allowed = false;
        for (int i = 0; i < STATUS_STAGES.length; i++) {
            if (STATUS_STAGES[i].equals(name)) { allowed = true; break; }
        }
        if (!allowed) return;
        for (int i = 0; i < writtenStageCount; i++) {
            if (WRITTEN_STAGES[i].equals(name)) return;
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
            WRITTEN_STAGES[writtenStageCount++] = name;
        } catch (Throwable ignored) {
            try { System.err.println("MIBR_HMI_STATUS_WRITE_FAILED"); }
            catch (Throwable ignoredAgain) { }
        } finally {
            if (out != null) {
                try { out.close(); } catch (Throwable ignored) { }
            }
        }
    }

    public static void activatorStarted() {
        stage("CIO_ACTIVATOR_STARTED");
        // Vehicle-data speed source (default off; reads vdata.mode). Must never affect HMI startup.
        try { MibrVdataBridge.start(); } catch (Throwable ignored) { }
        try { MibrVstatusSource.start(); } catch (Throwable ignored) { }
    }

    public static synchronized void bind(AppFrameworkCioFactory f, CioDictionary d,
                                          CioDispatcher p, CioIdService i) {
        factory = f;
        dictionary = d;
        dispatcher = p;
        ids = i;
        stage("CIO_FACTORY_BOUND");
        System.out.println("MIBR_HOME_BIND");
    }

    public static synchronized void activate(CioVisualizationService service) {
        // The native WidgetList adapter supplies exactly one owned tile. The
        // earlier CIO registration would create a duplicate main-menu entry.
        if (service instanceof MibrVisualizationService) {
            visualization = (MibrVisualizationService)service;
            stage("CIO_SERVICES_READY");
            MibrSsmNativePage.enable();
        } else stage("FAIL_ACTIVATION_PREREQUISITE");
    }

    private static synchronized void maybeRegister(CioIntent candidate) {
        if (registered || candidate == null ||
            !"MenuAction".equals(candidate.getCioIntentClass()) ||
            !"GridMenuAction".equals(candidate.getUsage()) ||
            candidate.getVisualizationId() == 0L) return;
        try {
            stage("CIO_MENU_ACTION_CANDIDATE");
            CioIntentVisualization stock = visualization.getStockVisualization(candidate.getVisualizationId());
            if (stock == null) { stage("FAIL_GRID_VISUAL"); return; }
            Image[] icons = stock.getIcons();
            if (icons == null || icons.length == 0) { stage("FAIL_GRID_ICONS"); return; }
            stage("CIO_GRID_VIS_READY");
            visualization.setFallback(candidate.getVisualizationId());
            // Set before register: Dictionary listeners may be invoked synchronously.
            registered = true;
            if (definition == null) definition = new Definition();
            factory.createAndRegisterCio(definition, new Executor());
            stage("CIO_REGISTERED");
            System.out.println("MIBR_HOME_CIO_REGISTERED");
        } catch (Throwable t) {
            try {
                if (factory != null && definition != null) factory.unregisterCio(definition);
            } catch (Throwable ignored) { stage("FAIL_CIO_DETACH"); }
            registered = false;
            stage("FAIL_CIO_REGISTER");
            stage("FAIL_ACTIVATION");
            try { System.err.println("MIBR_HOME_CIO_REGISTER_FAILED " + t); }
            catch (Throwable ignored) { }
        }
    }

    public static long visualizationId() {
        return ids == null ? -1L :
            ids.getCioVisualizationId(APP, INSTANCE, CIO, VIS);
    }

    /** Detach only MIBR-owned listener, CIO and owned view widgets on bundle stop. */
    public static synchronized void deactivate() {
        boolean detachFailed = false;
        try { MibrSsmNativePage.disable(); }
        catch(Throwable t){detachFailed=true;stage("FAIL_CIO_DETACH");}
        if (listening && dictionary != null && registrationListener != null) {
            try {
                dictionary.removeCioRegistrationListener("MenuAction", registrationListener);
                registrationListener = null;
                listening = false;
            }
            catch (Throwable t) { detachFailed = true; stage("FAIL_CIO_DETACH"); }
        }
        if (registered && factory != null && definition != null) {
            try { factory.unregisterCio(definition); }
            catch (Throwable t) { detachFailed = true; stage("FAIL_CIO_DETACH"); }
        }
        try { MibrHomeList.detachOwnedList(); }
        catch (Throwable t) { detachFailed = true; stage("FAIL_CIO_DETACH"); }
        try { MibrOemPageEntry.detach(); }
        catch (Throwable t) { detachFailed = true; stage("FAIL_CIO_DETACH"); }
        visualization = null;
        if (!detachFailed) {
            registrationListener = null;
            listening = false;
            registered = false;
            definition = null;
            factory = null;
            dictionary = null;
            dispatcher = null;
            ids = null;
            stage("CIO_DETACHED");
        }
    }

    private static final class Definition implements CioIntentDefinition {
        public int getActionId() { return 1; }
        public String getAppName() { return APP; }
        public String getAppInstanceName() { return INSTANCE; }
        public String getCioName() { return CIO; }
        public String getIntentName() { return "OpenMibrHomeQa"; }
        public String getCioIntentClassName() { return "MenuAction"; }
        public String getUsage() { return "GridMenuAction"; }
        public int getRank() { return 2147483647; }
        public String[] getCioVisualizationNames() { return new String[] { VIS }; }
        public int getFeatureFlagId() { return -1; }
        public String getForwardedCioIntentClassName() { return null; }
        public String getForwardedUsageName() { return null; }
        public boolean isForwardingCioIntent() { return false; }
    }

    private static final class Executor implements CioExecutor {
        public boolean onCioIntentRegistration(ContentInformationObject cio) {
            return false; // OEM Factory convention: false = permit.
        }
        public void execute(ContentInformationObject cio, CioActionParameters parameters) {
            stage("HOME_CIO_EXECUTED");
            System.out.println("MIBR_R4_HOME_CIO_EXECUTED");
            if (!MibrOemPageEntry.requestOpen()) {
                stage("FAIL_HOME_HOST");
                System.err.println("MIBR_R4_CLICK_NO_HOST");
            }
        }
    }
}