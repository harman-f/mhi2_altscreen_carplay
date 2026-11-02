package de.mibr.hmi;

import de.vw.mib.asl.api.system.ASLSystemAPI;
import de.vw.mib.asl.api.system.ASLSystemFactory;
import de.vw.mib.asl.api.system.KeyAdapter;
import de.vw.mib.asl.api.system.KeyListener;

/**
 * Hardware MENU key while the owned CarPlay page is open. The page is entered
 * beside the HMI state machine, which still believes the main menu is shown
 * and ignores MENU. Same registration as the stock CarPlay speech KeyHandler
 * (ASLSystemAPI.addKeyListener); listeners are additive, stock handling stays.
 */
final class MibrMenuKeyBack extends KeyAdapter {
    private static MibrMenuKeyBack armed;
    private MibrMenuKeyBack() {}

    static synchronized void arm() {
        if (armed != null) return;
        try {
            ASLSystemAPI api = ASLSystemFactory.getSystemApi();
            if (api == null) { System.err.println("MIBR_MENU_KEY_API_MISSING"); return; }
            MibrMenuKeyBack listener = new MibrMenuKeyBack();
            api.addKeyListener(KeyListener.KEY_MENU, listener);
            armed = listener;
        } catch (Throwable failure) {
            System.err.println("MIBR_MENU_KEY_ARM_FAILED " + failure);
        }
    }

    static synchronized void disarm() {
        MibrMenuKeyBack listener = armed;
        armed = null;
        if (listener == null) return;
        try {
            ASLSystemAPI api = ASLSystemFactory.getSystemApi();
            if (api != null) api.removeKeyListener(KeyListener.KEY_MENU, listener);
        } catch (Throwable failure) {
            System.err.println("MIBR_MENU_KEY_DISARM_FAILED " + failure);
        }
    }

    public void onReleased(int key) {
        if (key != KeyListener.KEY_MENU) return;
        // Key callbacks arrive on the ASL side; leave on the HMI dispatcher.
        de.vw.mib.widgets.internal.ServiceManager.eventDispatcher.invoke(new Runnable() {
            public void run() {
                synchronized (MibrMenuKeyBack.class) { if (armed == null) return; }
                if (!MibrOemPageEntry.isOpen()) return;
                System.out.println("MIBR_MENU_KEY_LEAVE");
                MibrOemPageEntry.back(); // no child page is registered: closes to HOME
            }
        });
    }
}
